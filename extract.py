import cdsapi

dataset = "cams-europe-air-quality-forecasts"
request = {
    "variable": ["birch_pollen"],
    "model": ["ensemble"],
    "level": ["0"],
    "date": ["2025-03-19/2025-03-19"],
    "type": ["forecast"],
    "time": ["00:00"],
    "leadtime_hour": ["0"],
    "data_format": "grib"
}

client = cdsapi.Client()
client.retrieve(dataset, request).download()

