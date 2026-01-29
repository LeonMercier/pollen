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

    grbs.close()
    print("\n Done gribbing")
    
    if os.path.exists(local_path):
        os.remove(local_path)
    else:
        print("No file to remove")

input_path = dbutils.fs.ls("dbfs:/mnt/pollen/bronze/")[-1].path
transform(input_path)

