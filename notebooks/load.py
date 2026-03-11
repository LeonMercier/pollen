# pyspark available by default in Databricks
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp
from datetime import datetime

# Accept input_path parameter from ADF
dbutils.widgets.text("input_path", "", "Input file path from Transform")
input_path = dbutils.widgets.get("input_path")

# Fallback to latest file if no parameter provided (manual testing)
if not input_path:
    input_path = dbutils.fs.ls("dbfs:/mnt/pollen/silver/")[-1].path
    print(f"No input_path provided, using latest file: {input_path}")

# get secrets for PostgreSQL access
postgres_server = dbutils.secrets.get(scope="secrets", key="postgres-server-fqdn")
postgres_username = dbutils.secrets.get(scope="secrets", key="postgres-admin-username")
postgres_password = dbutils.secrets.get(scope="secrets", key="postgres-admin-password")
postgres_database = "pollen"  # name is configured in the Terraform resource

# connect to PostgreSQL
jdbc_url = (
    f"jdbc:postgresql://{postgres_server}:5432/{postgres_database}?sslmode=require"
)
connection_properties = {
    "user": postgres_username,
    "password": postgres_password,
    "driver": "org.postgresql.Driver",
}

# create the table if it doesnt already exist (without indexes initially)
# Indexes are created AFTER data load for optimal performance
# TODO: review DECIMAL and DOUBLE needed precision
create_table_sql = """
CREATE TABLE IF NOT EXISTS public.pollen_forecast (
    id SERIAL PRIMARY KEY,
    start_date TIMESTAMP NOT NULL,
    load_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    constituent_type VARCHAR(50) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    constituent_value DOUBLE PRECISION NOT NULL,
    forecast_time INT NOT NULL
);
"""

# Separate index creation (executed AFTER data load)
create_indexes_sql = """
CREATE INDEX IF NOT EXISTS idx_forecast_time 
    ON public.pollen_forecast(forecast_time DESC);
CREATE INDEX IF NOT EXISTS idx_constituent 
    ON public.pollen_forecast(constituent_type);
CREATE INDEX IF NOT EXISTS idx_location 
    ON public.pollen_forecast(latitude, longitude);
"""

# execute database creation
# The 'spark' object exists already because of the Databricks environment.
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    statement.execute(create_table_sql)
    connection.close()
    print("Table schema verified/created")
except Exception as e:
    print(f"ERROR creating table: {str(e)}")
    raise

# read all parquet files from transform step
# raise = exception becomes fatal
# creates spark dataframe, not exactly same as pandas dataframe
try:
    df = spark.read.parquet(input_path)
    print(f"Schema: {df.schema}")
except Exception as e:
    print(f"ERROR reading parquet file: {str(e)}")
    raise

# add column
df = df.withColumn("load_timestamp", current_timestamp())
# Rename columns to match SQL table schema
df = df.withColumnRenamed("lat", "latitude").withColumnRenamed("lon", "longitude")
print(f"Final schema before load:")
df.printSchema()

# truncate = remove all rows, but keep table structure
# never gets here if parquet loading fails
truncate_sql = "TRUNCATE TABLE public.pollen_forecast"
# Drop indexes before load for optimal bulk insert performance
drop_indexes_sql = """
DROP INDEX IF EXISTS idx_forecast_time;
DROP INDEX IF EXISTS idx_constituent;
DROP INDEX IF EXISTS idx_location;
"""

try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    statement.execute(truncate_sql)
    statement.execute(drop_indexes_sql)
    connection.close()
    print("Existing data truncated and indexes dropped for fast loading")
except Exception as e:
    print(f"ERROR truncating table and dropping indexes: {str(e)}")
    raise

# Write to database
# Dataframe keys have to match SQL table colum names
# Calculate optimal partition count based on data size
# Use 2-6 partitions for better IOPS utilization on B1ms SKU
current_partitions = df.rdd.getNumPartitions()
partition_count = min(6, max(2, current_partitions))
df = df.coalesce(partition_count)
print(f"Using {partition_count} partitions for parallel loading")

try:
    df.write.option("batchsize", 50000).option(
        "isolationLevel", "READ_UNCOMMITTED"
    ).jdbc(
        url=jdbc_url,
        table="public.pollen_forecast",
        mode="append",
        properties=connection_properties,
    )
    print(f"Successfully loaded data into PostgreSQL database")
except Exception as e:
    print(f"ERROR loading data to PostgreSQL: {str(e)}")
    raise

# Recreate indexes after data load for optimal query performance
# This is faster than updating indexes during each insert
print("Recreating indexes (this may take 5-15 minutes depending on data size)...")
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    statement.execute(create_indexes_sql)
    connection.close()
    print("Indexes successfully recreated")
except Exception as e:
    print(f"ERROR recreating indexes: {str(e)}")
    raise
