# pyspark available by default in Databricks
from pyspark.sql import SparkSession
import plotly.express as px

# NOTE: we could have skipped the whole SQL step and use just dataframes and
# possibly parquet. But there will be other users of the data in the future
# and so using SQL makes sense

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

# query
query = """
    SELECT * from dbo.pollen_forecast WHERE latitude = 60.95 AND longitude = 23.05;
"""

try:
    df = spark.read.jdbc(
        jdbc_url, "dbo.pollen_forecast", properties=connection_properties
    )
except Exception as e:
    print(f"WARNING: Could not read from database: {str(e)}")
    raise

df = df.filter((df.latitude == 60.95) & (df.longitude == 23.05))
df = df.select(df.forecast_time, df.constituent_value, df.constituent_type)
# pyspark specific way to visualize interactively
df.display()

# plotly will connect points in the order that they are in the data
df = df.orderBy("forecast_time")

fig = px.line(
    df,
    x="forecast_time",
    y="constituent_value",
    color="constituent_type",
    title="Pollen grains in m3 of air",
    markers=True,
)
fig.show()
