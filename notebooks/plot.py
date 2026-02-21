import os
import plotly.express as px
from pyspark.sql import SparkSession
from pyspark.sql.functions import expr
from azure.storage.blob import BlobServiceClient, ContentSettings

# NOTE: we could have skipped the whole SQL step and use just dataframes and
# possibly parquet. But there will be other users of the data in the future
# and so using SQL makes sense


def plot(latitude, longitude, name, sqlconn):
    # using f-strings to create SQL queries opens the door to SQL injection
    # here we enforce the types to prevent that
    lat = float(latitude)
    lon = float(longitude)

    # the 'AS' alias is needed because spark needs a subquery that it can then
    # further wrap with another query
    query = f"""
        (SELECT start_date, forecast_time, constituent_type, constituent_value
        FROM dbo.pollen_forecast
        WHERE latitude = {lat} AND longitude = {lon}) AS filtered_data
        """
    try:
        df = spark.read.jdbc(jdbc_url, query, properties=sqlconn)
    except Exception as e:
        print(f"WARNING: Could not read from database: {str(e)}")
        raise

    # expr means you can do SQL
    # this is to get a nice x-axis with actual datetimes instead of just hours since
    # start of forecast
    df = df.withColumn(
        "forecast_datetime", expr("DATEADD(hour, forecast_time, start_date)")
    )

    # pyspark specific way to visualize interactively
    df.display()

    # need to sort because plotly will connect points in the order that they are in the data
    df = df.orderBy("forecast_datetime")

    fig = px.line(
        df,
        x="forecast_datetime",
        y="constituent_value",
        color="constituent_type",
        title=name,
        markers=True,
        labels=dict(
            forecast_datetime="Time",
            constituent_value="Pollen grains in m3 of air",
            constituent_type="Pollen type",
        ),
    )
    fig.show()

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


# get secrets for SQL access
sql_server = dbutils.secrets.get(scope="secrets", key="sql-server-fqdn")
sql_username = dbutils.secrets.get(scope="secrets", key="sql-admin-username")
sql_password = dbutils.secrets.get(scope="secrets", key="sql-admin-password")
sql_database = "sqldb-pollen"  # name is configured in the Terraform resource

# connect to SQL
jdbc_url = f"jdbc:sqlserver://{sql_server}:1433;database={sql_database};encrypt=true;trustServerCertificate=false;loginTimeout=30"
connection_properties = {
    "user": sql_username,
    "password": sql_password,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
}

# locations we want to plot
# available grid points are like x.05, x.15, x.25 ... x.95
locations = [
    {"lat": 60.15, "lon": 24.95, "name": "Helsinki"},
    {"lat": 48.85, "lon": 2.35, "name": "Paris"},
    {"lat": 41.85, "lon": 12.55, "name": "Rome"},
]

# create plots and save into an list
plots = []
for l in locations:
    plots.append(plot(l["lat"], l["lon"], l["name"], connection_properties))

# create the HTML, join loops through the array and adds a separator
combined_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Pollen Forecasts</title>
</head>
<body>
    <h1>Pollen Forecasts</h1>
    {'<hr>'.join(plots)}
</body>
</html>
"""

tmp_name = "/tmp/index.html"
with open(tmp_name, "w") as f:
    f.write(combined_html)

# Get storage credentials from Databricks secrets
storage_account_name = dbutils.secrets.get(
    scope="secrets", key="web-storage-account-name"
)
storage_account_key = dbutils.secrets.get(
    scope="secrets", key="web-storage-account-key"
)

# Create blob service client
blob_service_client = BlobServiceClient(
    account_url=f"https://{storage_account_name}.blob.core.windows.net",
    credential=storage_account_key,
)

# Upload to $web container (static website hosting container)
container_name = "$web"

blob_name = "index.html"
try:
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=blob_name
    )

    with open(tmp_name, "rb") as data:
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type="text/html"),
        )

except Exception as e:
    print(f"ERROR uploading chart to blob storage: {str(e)}")
    raise

# Clean up local temporary file
if os.path.exists(tmp_name):
    os.remove(tmp_name)
