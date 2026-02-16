# pyspark available by default in Databricks
from pyspark.sql import SparkSession

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
        jdbc_url, "dbo.pollen.forecast", properties=connection_properties
    )
except Exception as e:
    print(f"WARNING: Could not read from database: {str(e)}")
    raise

subset = df.filter((df.latitude == 60.95) & (df.longitude == 23.05))
print("Dataframe: ")
print(subset)
