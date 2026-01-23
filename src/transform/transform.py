import os
from azure.storage.blob import BlobServiceClient
import pygrib
import numpy as np
from datetime import datetime

def transform(storage_conn_str):
    # Now configure Blob storage and upload ############

    blob_service = BlobServiceClient.from_connection_string(storage_conn_str)

    # Download the blob to a local file
    # Add 'DOWNLOAD' before the .txt extension so you can see both files in the data directory

    local_path = ""
    local_file_name = "result.grib"
    download_file_path = os.path.join(
        local_path, str.replace(local_file_name ,'.grib', 'DOWNLOAD.grib'))
    container_client = blob_service.get_container_client(
        container= 'bronze') 
    print("\nDownloading blob to \n\t" + download_file_path)

    with open(file=download_file_path, mode="wb") as download_file:
        download_file.write(container_client.download_blob(
            'result.grib').readall())

    print("\nDone downloading blob")

    grbs = pygrib.open("resultDOWNLOAD.grib")
    for grb in grbs:
        print(grb)
        print(grb.values)
        # print(grb.keys())

    grbs.close()
    print("\n Done gribbing")
    # if os.path.exists(filename):
    #     os.remove(filename)
    # else:
    #     print("No file to remove")


storage_conn_str=os.environ.get("AzureWebJobsStorage")
transform("UseDevelopmentStorage=true")
