import os
import cdsapi
from azure.storage.blob import BlobServiceClient

# TODO: return something?
# TODO: import azure.storage.blob, take path to that as arg
def download(api_url, api_key, storage_conn_str):

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

    # when filename is passed as argument, returns a string, not a Result 
    # object with a .download() method
    client.retrieve(dataset, request, filename)

    # Now configure Blob storage and upload 

    blob_service = BlobServiceClient.from_connection_string(storage_conn_str)

    # doesnt actually create anything on the remote, just creates the object 
    # that represents the resource
    container_client = blob_service.get_container_client('bronze')

    # Create container if it doesn't exist
    from azure.core.exceptions import ResourceExistsError
    try:
        container_client.create_container()
    except ResourceExistsError:
        # Container already exists, that's fine
        pass

    with open(file=filename, mode="rb") as data:
        blob_client = container_client.upload_blob(name="sample-blob.txt", data=data, overwrite=True)

    if os.path.exists(filename):
        os.remove(filename)
    else:
        print("No file to remove")
