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
    "reWriteBatchedInserts": "true",  # PostgreSQL JDBC optimization: combines multiple INSERTs
}

# Blue-Green Deployment Pattern:
# 1. Load new data into staging table
# 2. Build indexes on staging table
# 3. Validate staging data
# 4. Atomically swap staging → production
# 5. Drop old table
# This ensures zero downtime and consistent data for API users

# Schema for production table
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

# Index definitions (template used for both production and staging)
create_indexes_template = """
CREATE INDEX IF NOT EXISTS idx_forecast_time{suffix} 
    ON public.pollen_forecast{suffix}(forecast_time DESC);
CREATE INDEX IF NOT EXISTS idx_constituent{suffix} 
    ON public.pollen_forecast{suffix}(constituent_type);
CREATE INDEX IF NOT EXISTS idx_location{suffix} 
    ON public.pollen_forecast{suffix}(latitude, longitude);
"""

# Staging table creation
create_staging_sql = """
DROP TABLE IF EXISTS public.pollen_forecast_staging CASCADE;
CREATE TABLE public.pollen_forecast_staging (
    LIKE public.pollen_forecast INCLUDING DEFAULTS EXCLUDING INDEXES
);
"""

# Table swap SQL (atomic operation in transaction)
swap_tables_sql = """
BEGIN;
    -- Rename current production table to _old
    ALTER TABLE IF EXISTS public.pollen_forecast 
        RENAME TO pollen_forecast_old;
    
    -- Promote staging to production (atomic!)
    ALTER TABLE public.pollen_forecast_staging 
        RENAME TO pollen_forecast;
COMMIT;

-- Clean up old table after successful swap
DROP TABLE IF EXISTS public.pollen_forecast_old;
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

# Create fresh staging table for this load
# If previous load failed, this drops any leftover staging table
print("Creating staging table for new data...")
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    statement.execute(create_staging_sql)
    connection.close()
    print("✓ Staging table created (pollen_forecast_staging)")
except Exception as e:
    print(f"ERROR creating staging table: {str(e)}")
    raise

# Write to staging table (production table remains live and responsive)
# Dataframe keys must match SQL table column names
# Calculate optimal partition count based on data size
# Use 2-6 partitions for better IOPS utilization on B1ms SKU
current_partitions = df.rdd.getNumPartitions()
partition_count = min(6, max(2, current_partitions))
df = df.coalesce(partition_count)
print(f"Using {partition_count} partitions for parallel loading")

try:
    print(f"Loading data into staging table...")
    df.write.option("batchsize", 50000).option(
        "isolationLevel", "READ_UNCOMMITTED"  # OK for staging table
    ).jdbc(
        url=jdbc_url,
        table="public.pollen_forecast_staging",
        mode="append",
        properties=connection_properties,
    )

    # Verify row count in staging table
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    result = statement.executeQuery(
        "SELECT COUNT(*) FROM public.pollen_forecast_staging"
    )
    # quirk: JDBC resultSet cursor starts on line before first line
    result.next()
    # index starts at 1
    row_count = result.getLong(1)
    connection.close()

    print(f"✓ Successfully loaded {row_count:,} rows into staging table")
except Exception as e:
    print(f"ERROR loading data to staging table: {str(e)}")
    raise

# Build indexes on staging table (production table stays indexed and fast!)
print("Building indexes on staging table (this may take 5-15 minutes)...")

try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    
    # Use _staging suffix for staging table indexes
    staging_indexes = create_indexes_template.format(suffix="_staging")
    statement.execute(staging_indexes)
    
    connection.close()
    print("✓ Indexes successfully created on staging table")

except Exception as e:
    print(f"ERROR creating indexes on staging table: {str(e)}")
    raise

# Validate staging data before swapping to production
print("Validating staging data...")
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    
    # Check 1: Verify we have data for all expected pollen constituents
    result = statement.executeQuery(
        "SELECT COUNT(DISTINCT constituent_type) FROM public.pollen_forecast_staging"
    )
    result.next()
    constituent_count = result.getInt(1)
    
    # Check 2: Verify we have reasonable data volume (not empty)
    result = statement.executeQuery(
        "SELECT COUNT(*) FROM public.pollen_forecast_staging"
    )
    result.next()
    staging_row_count = result.getLong(1)
    
    connection.close()
    
    # Validation thresholds
    EXPECTED_CONSTITUENTS = 6  # Alnus, Betula, Poaceae, Ambrosia, Artemisia, Olive
    MIN_ROWS = 1000  # Sanity check for minimum data
    
    if constituent_count < EXPECTED_CONSTITUENTS:
        raise ValueError(
            f"Expected {EXPECTED_CONSTITUENTS} pollen constituents, found {constituent_count}"
        )
    if staging_row_count < MIN_ROWS:
        raise ValueError(
            f"Staging table has suspiciously few rows: {staging_row_count}"
        )
    
    print(f"✓ Validation passed: {constituent_count} constituents, {staging_row_count:,} rows")
    
except Exception as e:
    print(f"ERROR: Validation failed: {str(e)}")
    print("ABORTING: Staging table will NOT be swapped to production")
    print("Production table remains unchanged")
    raise

# Perform atomic table swap (blue-green deployment)
print("Swapping staging table to production (atomic operation)...")
try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    
    # Execute the swap in a transaction (atomic!)
    statement.execute(swap_tables_sql)
    
    connection.close()
    
    print("=" * 60)
    print("✓ SUCCESS! Table swap complete - new data is now live")
    print("=" * 60)
    print("✓ Production table (pollen_forecast) now contains fresh forecast data")
    print("✓ Old production table has been dropped")
    print("✓ API queries will now see the updated forecast")
    print(f"✓ Total rows in production: {staging_row_count:,}")

except Exception as e:
    print(f"ERROR during table swap: {str(e)}")
    print("Production table remains unchanged (rollback successful)")
    raise
