import time
import json
from managment_api import ManagementAPI
from threading import Thread

mng_api = ManagementAPI()

def sync():
    mng_api.connect()
    while True:
        with open("status.json", "w") as fl:
            json.dump(mng_api.get_status(), fl, indent=4)
        time.sleep(30)