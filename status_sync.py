import time
import json
from managment_api import ManagementAPI
from threading import Thread

mng_api = ManagementAPI()

def sync():
    print("sync started")
    mng_api.connect()
    while True:
        with open("status.json", "w") as fl:
            print("file open")
            json.dump(mng_api.get_status(), fl)
        print("file close")
        time.sleep(30)