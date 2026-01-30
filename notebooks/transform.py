%pip install pygrib

import os
import pygrib
import numpy as np
from datetime import datetime

def transform(input_path):
    # pygrib cannot read directly from DBFS, hence the copy operation
    local_path = "/tmp/temp_grib_file.grib"
    dbutils.fs.cp(input_path, "file:" + local_path)
    
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
        print(data)


    # TODO: flatten data
    # TODO: write parquet file into silver storage
    grbs.close()
    print("\n Done gribbing")
    
    if os.path.exists(local_path):
        os.remove(local_path)
    else:
        print("No file to remove")

input_path = dbutils.fs.ls("dbfs:/mnt/pollen/bronze/")[-1].path
transform(input_path)

