import cdsapi

# TODO: take api keys as parameter here?
# TODO: return something?
# TODO: import azure.storage.blob, take path to that as arg
def download()

    # This part from query builder ################
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
    #################

    client = cdsapi.Client()
    client.retrieve(dataset, request).download()

