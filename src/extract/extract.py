import cdsapi
from azure.storage.blob import BlobServiceClient

# TODO: return something?
# TODO: import azure.storage.blob, take path to that as arg
def download(api_url, api_key, storage_conn_str)

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
    filename = 'result.grib'
    client.retrieve(dataset, request, filename).download()

    blob_service = BlobServiceClient.from_connection_string(storage_conn_str)
    container_client = blob_service.get_container_client('bronze')

    with open(file=filename, mode="rb") as data:
        blob_client = container_client.upload_blob(name="sample-blob.txt", data=data, overwrite=True)
