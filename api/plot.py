import plotly.express as px
import pandas as pd

# local
from database import *

CONSTITUENT_DISPLAY_NAMES = {
    "Alnus": "Alder (Alnus)",
    "Betula": "Birch (Betula)",
    "Poaceae": "Grass (Poaceae)",
    "Ambrosia": "Ragweed (Ambrosia)",
    "Artemisia": "Mugwort (Artemisia)",
    "64002": "Olive (Olea)",
}

# Per-species pollen severity thresholds in grains/m³.
# Each entry is [low, medium, high]; values above 'high' are Very High.
# These are approximate values — TODO: calibrate against EAN/SILAM guidelines.
SEVERITY_THRESHOLDS = {
    "Alnus": [10, 70, 200],
    "Betula": [10, 70, 200],
    "Poaceae": [10, 50, 200],
    "Ambrosia": [10, 50, 200],
    "Artemisia": [10, 50, 200],
    "64002": [10, 100, 300],
}

# Band colours (semi-transparent fills drawn behind the trace)
_BAND_COLORS = [
    "rgba(0,   180,  0,   0.10)",  # Low       — green
    "rgba(255, 210,  0,   0.15)",  # Medium    — yellow
    "rgba(255, 130,  0,   0.18)",  # High      — orange
    "rgba(220,  30,  30,  0.20)",  # Very High — red
]


def _add_severity_bands(fig, constituent_type: str) -> None:
    """
    Add coloured background bands to a log-scale Plotly figure representing
    pollen severity levels (Low / Medium / High / Very High).

    Args:
        fig: Plotly figure to modify in-place.
        constituent_type: Internal pollen key used to look up thresholds.
    """
    thresholds = SEVERITY_THRESHOLDS.get(constituent_type)
    if not thresholds:
        return

    low, medium, high = thresholds

    # Low / Medium / High bands use fixed data-space y coordinates
    fixed_bands = [
        (0.1, low, _BAND_COLORS[0]),  # Low    — green
        (low, medium, _BAND_COLORS[1]),  # Medium — yellow
        (medium, high, _BAND_COLORS[2]),  # High   — orange
    ]
    for y0, y1, color in fixed_bands:
        fig.add_shape(
            type="rect",
            xref="paper",
            x0=0,
            x1=1,
            yref="y",  # raw data coordinates; Plotly handles log scaling
            y0=y0,
            y1=y1,
            fillcolor=color,
            line_width=0,
            layer="below",
        )

    # Very High band: starts at the 'high' threshold and stretches to the top
    # of the plot area; y1=1e9 is clipped by Plotly to the visible axis range
    fig.add_shape(
        type="rect",
        xref="paper",
        x0=0,
        x1=1,
        yref="y",
        y0=high,
        y1=1e9,
        fillcolor=_BAND_COLORS[3],
        line_width=0,
        layer="below",
    )


def _fetch_forecast_df(lat: float, lon: float) -> pd.DataFrame:
    """Fetch and prepare the pollen forecast dataframe for a given location."""
    query = f"""
        (SELECT start_date, forecast_time, constituent_type, constituent_value
        FROM public.pollen_forecast
        WHERE latitude = {lat} AND longitude = {lon})
        """
    try:
        conn = get_sync_connection()
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"WARNING: Could not read from database: {str(e)}")
        raise

    if len(df) < 1:
        print("Error: got empty dataframe")
        raise ValueError("No pollen forecast data found for the specified location")

    print(f"Got DF with {len(df)} rows")

    # snap zeroes and low values to 1 because of the log scale
    df["constituent_value"] = df["constituent_value"].clip(lower=1)

    # forecast_time is stored as INT hours offset from start_date
    df["forecast_datetime"] = df["start_date"] + pd.to_timedelta(
        df["forecast_time"], unit="h"
    )
    df = df.sort_values("forecast_datetime")
    df["constituent_display"] = df["constituent_type"].map(
        lambda x: CONSTITUENT_DISPLAY_NAMES.get(x, x)
    )

    return df


def plot(latitude, longitude):
    """Return a single Plotly figure with all pollen types as separate traces."""
    # SQL injection guard
    lat = float(latitude)
    lon = float(longitude)

    df = _fetch_forecast_df(lat, lon)

    fig = px.line(
        df,
        x="forecast_datetime",
        y="constituent_value",
        color="constituent_display",
        title="Nice title",
        markers=True,
        labels=dict(
            forecast_datetime="Time (UTC)",
            constituent_value="Pollen grains in m3 of air",
            constituent_display="Pollen type",
        ),
    )

    return fig


def plot_by_type(latitude, longitude) -> dict:
    """Return a dict of Plotly figures, one per pollen type, keyed by display name."""
    # SQL injection guard
    lat = float(latitude)
    lon = float(longitude)

    df = _fetch_forecast_df(lat, lon)

    # y-axis upper bound (log10 units); must match update_layout range below
    LOG_Y_MAX = 3

    figures = {}
    for constituent_type, group_df in df.groupby("constituent_type"):
        display_name = CONSTITUENT_DISPLAY_NAMES.get(constituent_type, constituent_type)
        fig = px.line(
            group_df,
            x="forecast_datetime",
            y="constituent_value",
            title=display_name,
            markers=True,
            labels=dict(
                forecast_datetime="Time (UTC)",
                constituent_value="Pollen grains / m³",
            ),
        )
        fig.update_layout(yaxis=dict(type="log", range=[0, LOG_Y_MAX]))
        _add_severity_bands(fig, constituent_type)
        figures[display_name] = fig

    return figures
