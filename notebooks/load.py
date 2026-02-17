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

# create the table if it doesnt already exist
# triple quote = multiline string (+ no need to escape single quotes)
# IDENTITY() = auto increment (start, increment)
# TODO: review decimal scale/precision to match data
create_table_sql = """
IF OBJECT_ID('dbo.pollen_forecast', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.pollen_forecast (
        id INT IDENTITY(1,1) PRIMARY KEY,
        start_date DATETIME2 NOT NULL,
        load_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
        constituent_type NVARCHAR(50) NOT NULL,
        latitude DECIMAL(9,6) NOT NULL,
        longitude DECIMAL(9,6) NOT NULL,
        constituent_value FLOAT NOT NULL,
        forecast_time INT NOT NULL
    );
    
    CREATE INDEX idx_forecast_time ON dbo.pollen_forecast(forecast_timestamp DESC);
    CREATE INDEX idx_constituent ON dbo.pollen_forecast(constituent_type);
    CREATE INDEX idx_location ON dbo.pollen_forecast(latitude, longitude);
    
    PRINT 'Table created successfully';
END
ELSE
BEGIN
    PRINT 'Table already exists';
END
"""

# execute database creation
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, sql_username, sql_password
    )
    statement = connection.createStatement()
    statement.execute(create_table_sql)
    connection.close()
    print("Table schema verified/created")
except Exception as e:
    print(f"ERROR creating table: {str(e)}")
    raise

# read parquet file from transform step
# raise = exception becomes fatal
# creates spark dataframe, not exactly same as pandas dataframe
try:
    df = spark.read.parquet(input_path)
    print(f"Read {df.count()} rows from parquet file")
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
truncate_sql = "TRUNCATE TABLE dbo.pollen_forecast"
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, sql_username, sql_password
    )
    statement = connection.createStatement()
    statement.execute(truncate_sql)
    connection.close()
    print("Existing data truncated")
except Exception as e:
    print(f"ERROR truncating table: {str(e)}")
    raise

# write to database
# dataframe keys have to match SQL table colum names
try:
    df.write.jdbc(
        url=jdbc_url,
        table="dbo.pollen_forecast",
        mode="append",  # Append after truncate = replace
        properties=connection_properties,
    )

    row_count = df.count()
    print(f"Successfully loaded {row_count} rows into SQL database")
except Exception as e:
    print(f"ERROR loading data to SQL: {str(e)}")
    raise

# verification (read back and compare)
try:
    sql_df = spark.read.jdbc(
        jdbc_url, "dbo.pollen_forecast", properties=connection_properties
    )
    sql_row_count = sql_df.count()

    print(f"Verification: {sql_row_count} rows in SQL table")

    if sql_row_count != row_count:
        print(
            f"WARNING: Row count mismatch! Expected {row_count}, found {sql_row_count}"
        )
    else:
        print("Row count verification passed")

except Exception as e:
    print(f"WARNING: Could not verify load: {str(e)}")
    # Don't raise - data might still be loaded successfully

# Note: load.py doesn't need to return a value since it's the final step
