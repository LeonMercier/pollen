import math
import plotly.express as px
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# local
from database import *

CONSTITUENT_DISPLAY_NAMES = {
    "Alnus": "Alder / Leppä",
    "Betula": "Birch / Koivu",
    "Poaceae": "Grasses / Heinät",
    "Ambrosia": "Ragweed / Tuoksukki",
    "Artemisia": "Mugwort / Pujo",
    "64002": "Olive / Oliivi",
}

# Per-species pollen severity thresholds in grains/m³.
# Each entry is [low, medium, high]; values above 'high' are Very High.
# These are approximate values — TODO: calibrate against more sources
# https://climate-adapt.eea.europa.eu/en/observatory/publications-data/analysis-data/cams-ground-level-pollen-forecast
# Olive, Betula, Alnus, Artemisia: start - high: 10 - 100
# Poaceae, Ambrosia: start - high: 3 - 50
# Plus we have high x 2 = very high
SEVERITY_THRESHOLDS = {
    "Alnus": [10, 100, 200],
    "Betula": [10, 100, 200],
    "Poaceae": [3, 50, 100],
    "Ambrosia": [3, 50, 100],
    "Artemisia": [10, 100, 200],
    "64002": [10, 100, 200],
}

# Band colours (semi-transparent fills drawn behind the trace)
_BAND_COLORS = [
    "rgba(0,   180,  0,   0.10)",  # Low       — green
    "rgba(255, 210,  0,   0.15)",  # Medium    — yellow
    "rgba(255, 130,  0,   0.18)",  # High      — orange
    "rgba(220,  30,  30,  0.20)",  # Very High — red
]


def _get_utc_offset_string(timezone_name: str) -> str:
    """
    Get UTC offset string for a timezone (e.g., "UTC+2", "UTC-5").

    Args:
        timezone_name: IANA timezone name (e.g., "Europe/Helsinki")

    Returns:
        String like "UTC+2" or "UTC-5"

    Note:
        This function returns integer hour offsets only. Timezones with
        half-hour or quarter-hour offsets (e.g., Asia/Kolkata UTC+5:30,
        Australia/Eucla UTC+8:45) will be rounded to the nearest hour.
        For more precision, modify to include minutes in the format.
    """
    # Get current time in the timezone to determine offset
    # (offset can change due to DST, so we use current time)
    now = datetime.now(ZoneInfo(timezone_name))
    offset = now.utcoffset()

    # Handle edge case where utcoffset() returns None
    if offset is None:
        return "unknown"

    offset_seconds = offset.total_seconds()
    offset_hours = int(offset_seconds / 3600)

    if offset_hours >= 0:
        return f"UTC+{offset_hours}"
    else:
        return f"UTC{offset_hours}"  # negative sign included


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


def _fetch_forecast_df(lat: float, lon: float, timezone_name: str) -> pd.DataFrame:
    """
    Fetch and prepare the pollen forecast dataframe for a given location.

    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        timezone_name: IANA timezone name (e.g., "America/New_York") for time conversion

    Returns:
        DataFrame with forecast_datetime converted to local timezone
    """
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

    # Convert from UTC to local timezone
    # First localize to UTC (make timezone-aware), then convert to target timezone
    try:
        df["forecast_datetime"] = (
            df["forecast_datetime"]
            .dt.tz_localize("UTC")
            .dt.tz_convert(ZoneInfo(timezone_name))
        )
        print(f"Converted times to timezone: {timezone_name}")
    except Exception as e:
        print(f"WARNING: Could not convert to timezone '{timezone_name}': {str(e)}")
        print("Falling back to UTC")
        # Keep as UTC if timezone conversion fails
        df["forecast_datetime"] = df["forecast_datetime"].dt.tz_localize("UTC")

    df = df.sort_values("forecast_datetime")
    df["constituent_display"] = df["constituent_type"].map(
        lambda x: CONSTITUENT_DISPLAY_NAMES.get(x, x)
    )

    return df


def plot(latitude, longitude, timezone_name: str):
    """
    Return a single Plotly figure with all pollen types as separate traces.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
        timezone_name: IANA timezone name for x-axis labels
    """
    # SQL injection guard
    lat = float(latitude)
    lon = float(longitude)

    df = _fetch_forecast_df(lat, lon, timezone_name)

    fig = px.line(
        df,
        x="forecast_datetime",
        y="constituent_value",
        color="constituent_display",
        title="Nice title",
        markers=True,
        labels=dict(
            forecast_datetime="Local Time",
            constituent_value="Pollen grains in m3 of air",
            constituent_display="Pollen type",
        ),
    )

    return fig


def plot_by_type(latitude, longitude, timezone_name: str, city_name: str) -> dict:
    """
    Return a dict of Plotly figures, one per pollen type, keyed by display name.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
        timezone_name: IANA timezone name for x-axis labels
        city_name: City name to display on x-axis label
    """
    # SQL injection guard
    lat = float(latitude)
    lon = float(longitude)

    df = _fetch_forecast_df(lat, lon, timezone_name)

    # Calculate UTC offset for the x-axis label
    utc_offset = _get_utc_offset_string(timezone_name)
    x_axis_label = f"{city_name} Local Time ({utc_offset})"

    figures = {}
    for constituent_type, group_df in df.groupby("constituent_type"):
        display_name = CONSTITUENT_DISPLAY_NAMES.get(constituent_type, constituent_type)

        # y-axis upper bound (log10 units)
        # get from variable with hardcoded fallback
        thresholds = SEVERITY_THRESHOLDS.get(constituent_type, [10, 100, 200])
        # arbitrarily the highest threshold times 5
        # NOTE: with math.ceil() to get a nice round value, all plots currently
        # end up with the same default upper value
        log_floor = math.ceil(math.log10(thresholds[-1] * 5))
        max_val = group_df["constituent_value"].max()
        LOG_Y_MAX = max(
            log_floor, math.ceil(math.log10(max_val)) if max_val > 0 else log_floor
        )

        fig = px.line(
            group_df,
            x="forecast_datetime",
            y="constituent_value",
            title=display_name,
            # markers=True,
            labels=dict(
                forecast_datetime=x_axis_label,
                constituent_value="Pollen grains / m³",
            ),
        )
        fig.update_layout(yaxis=dict(type="log", range=[0, LOG_Y_MAX]))
        fig.update_traces(line_shape="spline")
        _add_severity_bands(fig, constituent_type)
        figures[display_name] = fig

    # sort by activity, then name (by returning a tuple)
    def _plot_sort_key(item):
        display_name, fig = item
        values = fig.data[0].y
        # v > 1 because we replace 0's with 1's previously
        has_activity = sum(v > 1 for v in values if v is not None) >= 10
        return (0 if has_activity else 1, display_name)

    figures = dict(sorted(figures.items(), key=_plot_sort_key))

    return figures
