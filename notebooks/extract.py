import os
import cdsapi

# TODO: return something?
def download(api_url, api_key):

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

    client = cdsapi.Client()

    filename = 'result.grib'

    # when filename is passed as argument, returns a string, NOT a Result 
    # object with a .download() method
    client.retrieve(dataset, request, filename)


# TODO: load env vars
api_url = 
api_key = 

download(api_url, api_key)

