import azure.functions as func
import datetime
import json
import logging
import os
import sys
from pathlib import Path

# add the repo root to our path
# the parent of dirA/dirB/file.py is dirA/diB, hence we need .parent.parent
# to get to the actual parent directory
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.extract.extract import download

app = func.FunctionApp()

# Crontab expression: at minute 5 of every hour of every day...
@app.timer_trigger(schedule="0 5 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def extract(myTimer: func.TimerRequest) -> None:
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    download(
        api_url=os.environ['CDSAPI_URL'],
        api_key=os.environ['CDSAPI_KEY'],
        storage_conn_str=os.environ.get("AzureWebJobsStorage")
    )

    logging.info('Python timer trigger function executed.')
