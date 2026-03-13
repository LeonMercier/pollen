import plotly.express as px
import pandas as pd

# local
from database import *


def plot(latitude, longitude):
    # SQL injection guard
    lat = float(latitude)
    lon = float(longitude)

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
    else:
        print(f"Got DF with {len(df)} rows")

    # create new column forecast_datetime that is a sum of start_date and forecast_time
    # forecast_time is stored as INT, so needs to be converted to timedelta
    df["forecast_datetime"] = df["start_date"] + pd.to_timedelta(
        df["forecast_time"], unit="h"
    )

    # order df by forecast_datetime
    df = df.sort_values("forecast_datetime")

    # Map constituent_type to user-facing display names
    constituent_display_names = {
        "Alnus": "Alder (Alnus)",
        "Betula": "Birch (Betula)",
        "Poaceae": "Grass (Poaceae)",
        "Ambrosia": "Ragweed (Ambrosia)",
        "Artemisia": "Mugwort (Artemisia)",
        "64002": "Olive (Olea)",
    }
    df["constituent_display"] = df["constituent_type"].map(
        lambda x: constituent_display_names.get(x, x)
    )

    fig = px.line(
        df,
        x="forecast_datetime",
        y="constituent_value",
        color="constituent_display",
        title="Nice title",
        markers=True,
        labels=dict(
            forecast_datetime="Time",
            constituent_value="Pollen grains in m3 of air",
            constituent_display="Pollen type",
        ),
    )

    return fig
