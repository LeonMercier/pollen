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
        return "<p>Error</p>"
    else:
        print(f"Got DF with {len(df)} rows")

    # create new column forecast_datetime that is a sum of start_date and forecast_time
    # forecast_time is stored as INT, so needs to be converted to timedelta
    df["forecast_datetime"] = df["start_date"] + pd.to_timedelta(
        df["forecast_time"], unit="h"
    )

    # order df by forecast_datetime
    df = df.sort_values("forecast_datetime")

    fig = px.line(
        df,
        x="forecast_datetime",
        y="constituent_value",
        color="constituent_type",
        title="Nice title",
        markers=True,
        labels=dict(
            forecast_datetime="Time",
            constituent_value="Pollen grains in m3 of air",
            constituent_type="Pollen type",
        ),
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")
