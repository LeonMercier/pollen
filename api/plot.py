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

    figures = {}
    for display_name, group_df in df.groupby("constituent_display"):
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
        fig.update_layout(yaxis=dict(type="log", range=[0, 3]))
        figures[display_name] = fig

    return figures
