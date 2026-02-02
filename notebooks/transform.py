%pip install pygrib

import os
import pygrib
import numpy as np
import pandas as pd
from datetime import datetime


def transform(input_path):
    # pygrib cannot read directly from DBFS, hence the copy operation
    local_path = "/tmp/temp_grib_file.grib"
    dbutils.fs.cp(input_path, "file:" + local_path)
    
    # Collect all data from all GRIB messages
    all_data = []
    
    grbs = pygrib.open(local_path)
    for grb in grbs:
        print(grb)
        print(grb.values)
        # print(grb.keys())

        lats, lons = grb.latlons()
        values = grb.values

        lats_flat = lats.flatten()
        lons_flat = lons.flatten()
        values_flat = values.flatten()

        data = {
                'variable': grb.shortName,
                'lat': lats_flat,
                'lon': lons_flat,
                'value': values_flat
        }
        df_temp = pd.DataFrame(data)
        all_data.append(df_temp)
        print(df_temp)

    grbs.close()
    
    # Combine all data into a single DataFrame
    df = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined DataFrame with {len(df)} rows")
    
    # Write DataFrame to DBFS silver folder as parquet
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/tmp/grib_data_{timestamp}.parquet"
    df.to_parquet(output_path)
    
    dbfs_silver_path = f"dbfs:/mnt/pollen/silver/grib_data_{timestamp}.parquet"
    dbutils.fs.cp("file:" + output_path, dbfs_silver_path)
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    print(f"Written to {dbfs_silver_path}")
    print("\n Done gribbing")
    
    if os.path.exists(local_path):
        os.remove(local_path)
    else:
        print("No file to remove")

    return dbfs_silver_path

input_path = dbutils.fs.ls("dbfs:/mnt/pollen/bronze/")[-1].path
transform(input_path)

