import os
import cdsapi
from azure.storage.blob import BlobServiceClient

# TODO: return something?
def download(api_url, api_key, storage_conn_str):

    # This part from CAMS query builder ################
    dataset = "cams-europe-air-quality-forecasts"
    request = {
    "variable": ["birch_pollen"],
    "model": ["ensemble"],
    "level": ["0"],
    "date": ["2025-03-20/2025-03-20"],
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


    # Now configure Blob storage and upload ############

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
        blob_client = container_client.upload_blob(
            name="result.grib", data=data, overwrite=True)

    if os.path.exists(filename):
        os.remove(filename)
    else:
        print("No file to remove")
