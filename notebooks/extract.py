import cdsapi
import os
import shutil
from datetime import datetime, timezone

# NOTE: the full forecast is guaranteed to be available daily at 10:00 UTC (but "time" in request should always be 00:00)

# Retrieve secrets from Databricks-managed secret scope
# Secrets are stored securely in Databricks (encrypted at rest)
api_url = dbutils.secrets.get(scope="secrets", key="cdsapi-url")
api_key = dbutils.secrets.get(scope="secrets", key="cdsapi-key")

# calculate date to request most recent forecast
req_datetime = datetime.now(timezone.utc)
req_date = req_datetime.strftime("%Y-%m-%d")

# This part can be generated from CAMS query builder ################
dataset = "cams-europe-air-quality-forecasts"
request = {
    "variable": ["alder_pollen", "birch_pollen"],
    "model": ["ensemble"],
    "level": ["0"],
    "date": [f"{req_date}/{req_date}"],
    "type": ["forecast"],
    "time": ["00:00"],
    "leadtime_hour": [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "59",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "67",
        "68",
        "69",
        "70",
        "71",
        "72",
        "73",
        "74",
        "75",
        "76",
        "77",
        "78",
        "79",
        "80",
        "81",
        "82",
        "83",
        "84",
        "85",
        "86",
        "87",
        "88",
        "89",
        "90",
        "91",
        "92",
        "93",
        "94",
        "95",
        "96",
    ],
    "data_format": "grib",
    "area": [61, 23, 60, 25],
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
