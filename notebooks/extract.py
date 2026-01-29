# TODO: move this to an init script
%pip install cdsapi

import cdsapi
import os
import shutil

def download(api_url, api_key):
    """
    Downloads pollen forecast data from Copernicus CAMS.
    Returns the filename of the downloaded GRIB file.
    """

    # This part from CAMS query builder ################
    dataset = "cams-europe-air-quality-forecasts"
    request = {
    "variable": ["birch_pollen"],
    "model": ["ensemble"],
    "level": ["0"],
    "date": ["2025-04-20/2025-04-20"],
    "type": ["forecast"],
    "time": ["00:00"],
    "leadtime_hour": ["0"],
    "data_format": "grib",
    "area": [61, 23, 60, 24]
    }
    ####################################################

    # Initialize CDSAPI client with explicit credentials
    client = cdsapi.Client(url=api_url, key=api_key)

    local_filename = 'result.grib'

    # when filename is passed as argument, returns a string, NOT a Result 
    # object with a .download() method
    client.retrieve(dataset, request, local_filename)

    # move local file to DBFS for next steps
    dbfs_path = f"/dbfs/mnt/pollen/bronze/result.grib"
    os.makedirs("/dbfs/mnt/pollen/bronze", exist_ok=True)
    shutil.copy(local_filename, dbfs_path)

    return local_filename  # Return for downstream processing


# Retrieve secrets from Databricks-managed secret scope
# Secrets are stored securely in Databricks (encrypted at rest)
api_url = dbutils.secrets.get(scope="secrets", key="cdsapi-url")
api_key = dbutils.secrets.get(scope="secrets", key="cdsapi-key")

# Execute download
download(api_url, api_key)

