import os
import pygrib
import numpy as np
import pandas as pd
from datetime import datetime, time
from functools import reduce
from pyspark.sql import DataFrame
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType,
    TimestampType,
)

# detect if local or cloud
if "DATABRICKS_RUNTIME_VERSION" in os.environ:
    print("Running in cluster")
else:
    print("Running locally")
    import pyspark
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    dbutils = w.dbutils
    spark = pyspark.sql.SparkSession.builder.getOrCreate()

# Accept input_path parameter from ADF
dbutils.widgets.text("input_path", "", "Input file path from Extract")
input_path = dbutils.widgets.get("input_path")

# Fallback to latest file if no parameter provided (manual testing)
if not input_path:
    input_path = dbutils.fs.ls("dbfs:/mnt/pollen/bronze/")[-1].path
    print(f"No input_path provided, using latest file: {input_path}")

# pygrib cannot read directly from DBFS, hence the copy operation
local_path = "/tmp/temp_grib_file.grib"
dbutils.fs.cp(input_path, "file:" + local_path)

# (pyspark) Define the schema
schema = StructType(
    [
        StructField("constituent_type", StringType(), nullable=False),
        StructField("lat", DoubleType(), nullable=False),
        StructField("lon", DoubleType(), nullable=False),
        StructField("constituent_value", DoubleType(), nullable=True),
        StructField("forecast_time", IntegerType(), nullable=False),
        StructField("start_date", TimestampType(), nullable=False),
    ]
)

# Create directory for temp files
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
temp_parquet_dir = f"dbfs:/tmp/grib_temp_{timestamp}/"

grbs = pygrib.open(local_path)
for grb in grbs:
    # print(grb)
    # print(grb.values)
    # print(grb.keys())

    # return two 2D arrays
    lats, lons = grb.latlons()

    # returns one 2D array
    values = grb.values

    lats_flat = lats.flatten()
    lons_flat = lons.flatten()
    values_flat = values.flatten()

    # construct datetime that represents the start of the forecast
    start_date = datetime.fromisoformat(str(grb.date))
    start_time = time(grb.hour, 0, 0)
    start_date = datetime.combine(start_date, start_time)

    # pandas dataframe (of a single grib message)
    pdf = pd.DataFrame(
        {
            "constituent_type": grb.constituentTypeName,
            "lat": lats_flat,
            "lon": lons_flat,
            "constituent_value": values_flat,
            "forecast_time": grb.forecastTime,
            "start_date": start_date,
        }
    )
    # pandas to spark
    tmp_df = spark.createDataFrame(pdf, schema=schema)

    # write to disk: we just use a directory and spark will handle the filenames inside automatically
    tmp_df.write.mode("append").parquet(temp_parquet_dir)

files = dbutils.fs.ls(temp_parquet_dir)
parquet_files = [f for f in files if f.name.endswith(".parquet")]
total_size = sum(f.size for f in parquet_files)
print(
    f"Wrote {len(parquet_files)} parquet files, total: {total_size / (1024**2):.2f} MB, avg: {total_size / len(parquet_files) / 1024:.2f} KB per file"
)

grbs.close()

# read all files from temp dir (spark read all files in dir)
# doesnt actually load all data into memory
df = spark.read.parquet(temp_parquet_dir)
print(f"Created final dataframe")

# Write DataFrame to DBFS silver folder as parquet
dbfs_silver_path = f"dbfs:/mnt/pollen/silver/grib_data_{timestamp}.parquet"
df.write.mode("overwrite").parquet(dbfs_silver_path)

print(f"Written to {dbfs_silver_path}")

# cleanup
if os.path.exists(local_path):
    os.remove(local_path)
dbutils.fs.rm(temp_parquet_dir, recurse=True)

# think of as a return value
result = dbfs_silver_path

# Only exit if running in ADF (widget has value from previous activity)
# During manual testing, widget is empty so we skip exit and show all output
if dbutils.widgets.get("input_path"):
    dbutils.notebook.exit(result)
else:
    print(f"\nManual execution complete. Output path: {result}")
