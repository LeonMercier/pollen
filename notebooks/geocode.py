# Databricks notebook source
# TITLE: GeoNames Cities Geocoding ETL
# DESCRIPTION: Downloads GeoNames cities500 dataset, filters to European cities,
#              computes nearest pollen grid points, and loads to PostgreSQL

# COMMAND ----------

# Accept parameters from ADF (or use defaults for manual execution)
dbutils.widgets.text(
    "geonames_url",
    "https://download.geonames.org/export/dump/cities500.zip",
    "GeoNames Download URL",
)
dbutils.widgets.text("output_mode", "replace", "Output mode: replace or append")

geonames_url = dbutils.widgets.get("geonames_url")
output_mode = dbutils.widgets.get("output_mode")

# COMMAND ----------

# Imports
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    IntegerType,
    StringType,
    DoubleType,
    LongType,
    DecimalType,
)
from pyspark.sql.functions import (
    col,
    broadcast,
    sin,
    cos,
    radians,
    asin,
    sqrt,
    row_number,
    current_timestamp,
    lit,
)
from pyspark.sql.window import Window
import urllib.request
import zipfile
import os

# COMMAND ----------

# European country codes (47 countries)
EUROPE_COUNTRIES = [
    "AD",
    "AL",
    "AT",
    "AX",
    "BA",
    "BE",
    "BG",
    "BY",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FO",
    "FR",
    "GB",
    "GG",
    "GI",
    "GR",
    "HR",
    "HU",
    "IE",
    "IM",
    "IS",
    "IT",
    "JE",
    "LI",
    "LT",
    "LU",
    "LV",
    "MC",
    "MD",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "SE",
    "SI",
    "SK",
    "SM",
    "UA",
    "VA",
    "XK",
]

GRID_WEST = -25.0
GRID_EAST = 45.0
GRID_SOUTH = 30.0
GRID_NORTH = 72.0

# COMMAND ----------

# STEP 1: Download GeoNames cities500.zip from web
print(f"Downloading GeoNames data from: {geonames_url}")

# Use /tmp for temporary file storage
os.makedirs("/dbfs/tmp", exist_ok=True)
local_zip_path = "/dbfs/tmp/cities500.zip"
local_txt_path = "/dbfs/tmp/cities500.txt"

try:
    urllib.request.urlretrieve(geonames_url, local_zip_path)
    print(f"Downloaded to: {local_zip_path}")

    # Extract the zip file
    with zipfile.ZipFile(local_zip_path, "r") as zip_ref:
        zip_ref.extractall("/dbfs/tmp/")
    print(f"Extracted to: {local_txt_path}")

    # Verify file exists and get size
    file_size_mb = os.path.getsize(local_txt_path) / (1024 * 1024)
    print(f"GeoNames file size: {file_size_mb:.2f} MB")

except Exception as e:
    print(f"ERROR downloading/extracting GeoNames data: {str(e)}")
    raise

# COMMAND ----------

# STEP 2: Define GeoNames schema and load into Spark DataFrame
# GeoNames cities500.txt format: tab-delimited, 19 columns, no header
# See: https://download.geonames.org/export/dump/readme.txt

geonames_schema = StructType(
    [
        StructField("geonameid", IntegerType(), False),
        StructField("name", StringType(), False),
        StructField("asciiname", StringType(), False),
        StructField("alternatenames", StringType(), True),
        StructField("latitude", DoubleType(), False),
        StructField("longitude", DoubleType(), False),
        StructField("feature_class", StringType(), True),
        StructField("feature_code", StringType(), True),
        StructField("country_code", StringType(), False),
        StructField("cc2", StringType(), True),
        StructField("admin1_code", StringType(), True),
        StructField("admin2_code", StringType(), True),
        StructField("admin3_code", StringType(), True),
        StructField("admin4_code", StringType(), True),
        StructField("population", LongType(), True),
        StructField("elevation", IntegerType(), True),
        StructField("dem", IntegerType(), True),
        StructField("timezone", StringType(), True),
        StructField("modification_date", StringType(), True),
    ]
)

print("Loading GeoNames data into Spark DataFrame...")

try:
    df_cities = (
        spark.read.option("delimiter", "\t")
        .option("header", "false")
        .schema(geonames_schema)
        .csv(local_txt_path.replace("/dbfs/", "dbfs:/", 1))
    )

    total_cities = df_cities.count()
    print(f"Loaded {total_cities:,} cities from GeoNames")

except Exception as e:
    print(f"ERROR loading GeoNames data: {str(e)}")
    raise

# COMMAND ----------

# STEP 3: Filter to European countries only
print("Filtering to European countries...")

df_europe = df_cities.filter(col("country_code").isin(EUROPE_COUNTRIES))

europe_count = df_europe.count()
print(f"Filtered to {europe_count:,} European cities")

print("Filtering to bounding box...")
df_europe = df_europe.filter(
    (col("latitude") >= GRID_SOUTH)
    & (col("latitude") <= GRID_NORTH)
    & (col("longitude") >= GRID_WEST)
    & (col("longitude") <= GRID_EAST)
)
europe_count = df_europe.count()
print(f"Filtered to {europe_count:,} European cities in bounding box")

# Show sample cities
print("\nSample European cities:")
df_europe.select("name", "country_code", "population", "latitude", "longitude").show(
    10, truncate=False
)

# COMMAND ----------

# STEP 4: Get distinct pollen grid points from PostgreSQL database
print("Fetching pollen grid points from database...")

# Get secrets for PostgreSQL access
postgres_server = dbutils.secrets.get(scope="secrets", key="postgres-server-fqdn")
postgres_username = dbutils.secrets.get(scope="secrets", key="postgres-admin-username")
postgres_password = dbutils.secrets.get(scope="secrets", key="postgres-admin-password")
postgres_database = "pollen"

# JDBC connection configuration
jdbc_url = (
    f"jdbc:postgresql://{postgres_server}:5432/{postgres_database}?sslmode=require"
)
connection_properties = {
    "user": postgres_username,
    "password": postgres_password,
    "driver": "org.postgresql.Driver",
}

try:
    # Query distinct pollen grid coordinates
    # This should be a small dataset (~few hundred unique locations)
    pollen_grid_query = """
        (SELECT DISTINCT latitude, longitude 
         FROM public.pollen_forecast) as pollen_grid
    """

    df_pollen_grid = spark.read.jdbc(
        url=jdbc_url, table=pollen_grid_query, properties=connection_properties
    )

    grid_count = df_pollen_grid.count()
    print(f"Found {grid_count:,} distinct pollen grid points")

    # Show sample grid points
    print("\nSample pollen grid points:")
    df_pollen_grid.show(5, truncate=False)

except Exception as e:
    print(f"ERROR fetching pollen grid points: {str(e)}")
    raise

# COMMAND ----------

# STEP 5: Compute nearest pollen grid point for each city using Haversine distance
print("Computing nearest pollen grid point for each city...")

# Broadcast the pollen grid to all workers (it's small, ~few hundred rows)
df_pollen_grid_broadcast = broadcast(
    df_pollen_grid.withColumnRenamed("latitude", "pollen_latitude").withColumnRenamed(
        "longitude", "pollen_longitude"
    )
)

# Cross join cities with pollen grid points
# For each city, we'll calculate distance to ALL grid points, then pick the nearest
df_cross = df_europe.crossJoin(df_pollen_grid_broadcast)

# Haversine distance formula for great-circle distance
# Distance in kilometers between two lat/lon points
# See: https://en.wikipedia.org/wiki/Haversine_formula
R = 6371  # Earth radius in kilometers

# NOTE: distance_km is dropped in a later stage, but could be kept in the future
# for debugging
df_with_distance = df_cross.withColumn(
    "distance_km",
    2
    * R
    * asin(
        sqrt(
            sin((radians(col("pollen_latitude")) - radians(col("latitude"))) / 2) ** 2
            + cos(radians(col("latitude")))
            * cos(radians(col("pollen_latitude")))
            * sin((radians(col("pollen_longitude")) - radians(col("longitude"))) / 2)
            ** 2
        )
    ),
)

# For each city (geonameid), find the pollen grid point with minimum distance
window = Window.partitionBy("geonameid").orderBy(col("distance_km"))

df_nearest = (
    df_with_distance.withColumn("rank", row_number().over(window))
    .filter(col("rank") == 1)
    .drop("rank")
)

print(f"Computed nearest pollen grid points for {df_nearest.count():,} cities")

# Show sample results with distances
print("\nSample cities with nearest pollen grid points:")
df_nearest.select(
    "name",
    "country_code",
    "latitude",
    "longitude",
    "pollen_latitude",
    "pollen_longitude",
    "distance_km",
).show(10, truncate=False)

# COMMAND ----------

# STEP 6: Prepare final schema for cities table
print("Preparing final dataset for database load...")

df_final = df_nearest.select(
    col("geonameid").alias("geoname_id"),
    col("name"),
    col("asciiname").alias("ascii_name"),
    col("country_code"),
    col("admin1_code"),
    col("population"),
    col("timezone"),
    # Cast to DECIMAL(9,6) to match database schema
    col("latitude").cast(DecimalType(9, 6)),
    col("longitude").cast(DecimalType(9, 6)),
    col("pollen_latitude").cast(DecimalType(9, 6)),
    col("pollen_longitude").cast(DecimalType(9, 6)),
    current_timestamp().alias("created_at"),
)

print("Final schema:")
df_final.printSchema()

# Show statistics
print(f"\nFinal dataset statistics:")
print(f"Total cities: {df_final.count():,}")
df_final.groupBy("country_code").count().orderBy("count", ascending=False).show(20)

# COMMAND ----------

# STEP 7: Create cities table if not exists
print("Creating cities table if not exists...")

create_table_sql = """
CREATE TABLE IF NOT EXISTS public.cities (
    id SERIAL PRIMARY KEY,
    geoname_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    ascii_name VARCHAR(200) NOT NULL,
    country_code CHAR(2) NOT NULL,
    admin1_code VARCHAR(20),
    population BIGINT,
    timezone VARCHAR(40),
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    pollen_latitude DECIMAL(9,6) NOT NULL,
    pollen_longitude DECIMAL(9,6) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# Indexes for search and lookups
create_indexes_sql = """
CREATE INDEX IF NOT EXISTS idx_cities_name ON public.cities (name);
CREATE INDEX IF NOT EXISTS idx_cities_ascii_name ON public.cities (ascii_name);
CREATE INDEX IF NOT EXISTS idx_cities_country ON public.cities (country_code);
CREATE INDEX IF NOT EXISTS idx_cities_pollen_location ON public.cities (pollen_latitude, pollen_longitude);
CREATE INDEX IF NOT EXISTS idx_cities_geoname ON public.cities (geoname_id);
"""

try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    statement.execute(create_table_sql)
    connection.close()
    print("Cities table schema verified/created")
except Exception as e:
    print(f"ERROR creating cities table: {str(e)}")
    raise

# COMMAND ----------

# STEP 8: Load data to PostgreSQL
print(f"Loading data to PostgreSQL (mode: {output_mode})...")

# If replace mode, truncate existing data and drop indexes
if output_mode == "replace":
    truncate_sql = "TRUNCATE TABLE public.cities"
    drop_indexes_sql = """
    DROP INDEX IF EXISTS idx_cities_name;
    DROP INDEX IF EXISTS idx_cities_ascii_name;
    DROP INDEX IF EXISTS idx_cities_country;
    DROP INDEX IF EXISTS idx_cities_pollen_location;
    DROP INDEX IF EXISTS idx_cities_geoname;
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
        print(f"ERROR truncating table: {str(e)}")
        raise

# Write to PostgreSQL
# Use fewer partitions since dataset is smaller than pollen_forecast
current_partitions = df_final.rdd.getNumPartitions()
partition_count = min(4, max(2, current_partitions))
df_final = df_final.coalesce(partition_count)
print(f"Using {partition_count} partitions for parallel loading")

try:
    df_final.write.option("batchsize", 10000).option(
        "isolationLevel", "READ_UNCOMMITTED"
    ).jdbc(
        url=jdbc_url,
        table="public.cities",
        mode="append",
        properties=connection_properties,
    )

    # Get row count from PostgreSQL
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    result = statement.executeQuery("SELECT COUNT(*) FROM public.cities")
    result.next()
    row_count = result.getLong(1)
    connection.close()

    print(f"Successfully loaded {row_count:,} cities into PostgreSQL database")

except Exception as e:
    print(f"ERROR loading data to PostgreSQL: {str(e)}")
    raise

# COMMAND ----------

# STEP 9: Recreate indexes for optimal query performance
print("Creating indexes (this may take a few minutes)...")

try:
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        jdbc_url, postgres_username, postgres_password
    )
    statement = connection.createStatement()
    statement.execute(create_indexes_sql)
    connection.close()
    print("Indexes successfully created")

except Exception as e:
    print(f"ERROR creating indexes: {str(e)}")
    raise

# COMMAND ----------

# STEP 10: Cleanup temporary files
print("Cleaning up temporary files...")

try:
    if os.path.exists(local_zip_path):
        os.remove(local_zip_path)
    if os.path.exists(local_txt_path):
        os.remove(local_txt_path)
    print("Temporary files removed")
except Exception as e:
    print(f"WARNING: Could not remove temporary files: {str(e)}")

# COMMAND ----------

print("=" * 60)
print("GeoNames cities geocoding ETL completed successfully!")
print("=" * 60)
