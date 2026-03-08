import plotly.express as px
import pandas as pd
import psycopg


def plot(latitude, longitude):
    query = f"""
        (SELECT start_date, forecast_time, constituent_type, constituent_value
        FROM dbo.pollen_forecast
        WHERE latitude = {latitude} AND longitude = {longitude})
        """
    try:
        df = {}  # TODO: execute SQL query
    except Exception as e:
        print(f"WARNING: Could not read from database: {str(e)}")
        raise

    # create new column forecast_datetime that is a sum of start_date and forecast_time
    df["forecast_datetime"] = df["start_date"] + df["forecast_time"]

    # order df by forecast_datetime
    df = df.sort_values("foreacast_datetime")

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
