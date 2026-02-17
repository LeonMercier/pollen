import os
import pygrib
import numpy as np
import pandas as pd
from datetime import datetime, time

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

# Collect all data from all GRIB messages
all_data = []

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

    # python dict
    data = {
        "constituent_type": grb.constituentTypeName,
        "lat": lats_flat,
        "lon": lons_flat,
        "constituent_value": values_flat,
        "forecast_time": grb.forecastTime,
        "start_date": start_date,
    }

    # pandas data frame from dict
    # by default, keys become column names
    df_temp = pd.DataFrame(data)

    # array of data frames
    all_data.append(df_temp)

    print(df_temp)

grbs.close()

# remove downloaded temp file
if os.path.exists(local_path):
    os.remove(local_path)

# Combine all data into a single DataFrame
df = pd.concat(all_data, ignore_index=True)
print(f"\nCombined DataFrame with {len(df)} rows")

# Write DataFrame to DBFS silver folder as parquet
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = f"/tmp/grib_data_{timestamp}.parquet"  # python F-string
df.to_parquet(output_path)

dbfs_silver_path = f"dbfs:/mnt/pollen/silver/grib_data_{timestamp}.parquet"
dbutils.fs.cp("file:" + output_path, dbfs_silver_path)

# remove created temp file
if os.path.exists(output_path):
    os.remove(output_path)

print(f"Written to {dbfs_silver_path}")

# think of as a return value
result = dbfs_silver_path

# Only exit if running in ADF (widget has value from previous activity)
# During manual testing, widget is empty so we skip exit and show all output
if dbutils.widgets.get("input_path"):
    dbutils.notebook.exit(result)
else:
    print(f"\nManual execution complete. Output path: {result}")
