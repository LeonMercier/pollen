import os
import gc
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
dbfs_silver_path = f"dbfs:/mnt/pollen/silver/grib_data_{timestamp}/"

# Accumulate BATCH_SIZE GRIB messages into one pandas dataframe,
# then turn into pySpark dataframe and write to disk.
# The goal is to prevent loading the whole dataset into memory as one giant
# pandas dataframe. Simultaneously we want to avoid the overhead from too many
# Spark jobs, hence the batching.

# Counterintuitively, OOM is more likely in multi-node configs than single-node.
BATCH_SIZE = 50
df_batch = []
grb_count = 0
batch_number = 0

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

    df_batch.append(pdf)
    grb_count += 1

    if len(df_batch) >= BATCH_SIZE:
        batch_number += 1
        print(f"Processing batch {batch_number}: {len(df_batch)} messages")
        concat_df = pd.concat(df_batch, ignore_index=True)
        # pandas to spark
        tmp_df = spark.createDataFrame(concat_df, schema=schema)
        # Spark by default creates 200 partitions, which would be fine, except
        # that here we are already creating many small dataframes in a loop.
        # Therefore we reduce partitioning.
        tmp_df = tmp_df.repartition(8)
        # Write to disk: we just use a directory and spark will handle the
        # filenames inside automatically.
        tmp_df.write.mode("append").parquet(dbfs_silver_path)

        # clear
        df_batch = []
        # We are dealing with large in-memory data, so give the garbage collector
        # a little kick between each batch. Alternatively could also use `del`.
        gc.collect()
        print(f"Batch {batch_number} written ({grb_count} messages processed so far)")

# final partial batch (same as above)
batch_number += 1
print(f"Processing batch {batch_number}: {len(df_batch)} messages")
concat_df = pd.concat(df_batch, ignore_index=True)
tmp_df = spark.createDataFrame(concat_df, schema=schema)
tmp_df = tmp_df.repartition(8)
tmp_df.write.mode("append").parquet(dbfs_silver_path)
print(f"Batch {batch_number} written ({grb_count} messages processed so far)")

# Print summary
files = dbutils.fs.ls(dbfs_silver_path)
parquet_files = [f for f in files if f.name.endswith(".parquet")]
total_size = sum(f.size for f in parquet_files)
print(
    f"Wrote {len(parquet_files)} parquet files, total: {total_size / (1024**2):.2f} MB, avg: {total_size / len(parquet_files) / 1024:.2f} KB per file"
)

grbs.close()


# cleanup
if os.path.exists(local_path):
    os.remove(local_path)

# think of as a return value
result = dbfs_silver_path

# Only exit if running in ADF (widget has value from previous activity)
# During manual testing, widget is empty so we skip exit and show all output
if dbutils.widgets.get("input_path"):
    dbutils.notebook.exit(result)
else:
    print(f"\nManual execution complete. Output path: {result}")
