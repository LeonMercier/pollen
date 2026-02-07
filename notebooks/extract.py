import cdsapi
import os
import shutil

# Retrieve secrets from Databricks-managed secret scope
# Secrets are stored securely in Databricks (encrypted at rest)
api_url = dbutils.secrets.get(scope="secrets", key="cdsapi-url")
api_key = dbutils.secrets.get(scope="secrets", key="cdsapi-key")

"""
Downloads pollen forecast data from Copernicus CAMS.
Returns the DBFS path of the downloaded GRIB file.
"""
from datetime import datetime

# This part from CAMS query builder ################
dataset = "cams-europe-air-quality-forecasts"
request = {
    "variable": ["alder_pollen", "birch_pollen"],
    "model": ["ensemble"],
    "level": ["0"],
    "date": ["2025-04-20/2025-04-20"],
    "type": ["forecast"],
    "time": ["00:00"],
    "leadtime_hour": ["0"],
    "data_format": "grib",
    "area": [61, 23, 60, 24],
}
####################################################

# Initialize CDSAPI client with explicit credentials
client = cdsapi.Client(url=api_url, key=api_key)

local_filename = "result.grib"

# when filename is passed as argument, returns a string, NOT a Result
# object with a .download() method
client.retrieve(dataset, request, local_filename)

# Generate timestamped filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dbfs_filename = f"pollen_data_{timestamp}.grib"
dbfs_path = f"/dbfs/mnt/pollen/bronze/{dbfs_filename}"

# move local file to DBFS for next steps
os.makedirs("/dbfs/mnt/pollen/bronze", exist_ok=True)
shutil.copy(local_filename, dbfs_path)

if os.path.exists(local_filename):
    os.remove(local_filename)
else:
    print("No file to remove")

# Return DBFS path in the format expected by Databricks
result = f"dbfs:/mnt/pollen/bronze/{dbfs_filename}"
print(f"\nExtract complete. Output path: {result}")
dbutils.notebook.exit(result)
