import telnetlib
import os
import json
import psutil
import time


class ManagementAPI:
    def __init__(self, host="localhost", port=7505):
        self.host = host
        self.port = port
        self.telnet_client = None

    def connect(self):
        self.telnet_client = telnetlib.Telnet(self.host, self.port)

    def disconnect(self):
        self.telnet_client.close()

    def get_status(self):
        raw_status = b""

        if not self.telnet_client:
            raise Exception("Telnet session not initialized")
        self.telnet_client.write(b"status\n")
        while (
            not raw_status.decode().startswith(">INFO")
            and not raw_status.decode().startswith("TITLE")
            and not raw_status.decode().startswith("\n")
            and not raw_status.decode().startswith("\r\nTITLE")
        ):
            self.telnet_client.write(b"status\n")
            raw_status = self.telnet_client.read_until(b"END")
            time.sleep(2)

        processed_status = self.__parse_status__(raw_status.decode())
        return processed_status

    def __parse_status__(self, raw_string):
        line_split = raw_string.split("\n")
        if raw_string.startswith(">") or raw_string.startswith("\r"):
            line_split.pop(0)
        server_datetime = line_split[1].split(",")[1]
        clients = []
        for client in line_split[3:]:
            if client.startswith("HEADER"):
                break
            split_string = client.split(",")
            clients.append(
                {
                    "type": split_string[0],
                    "name": split_string[1],
                    "ip": split_string[2],
                    "virt_ip": split_string[3],
                    "virt_ip6": split_string[4],
                    "received": int(split_string[5]),
                    "sent": int(split_string[6]),
                    "connected_since": split_string[7],
                }
            )
        return {"datetime": server_datetime, "clients": clients}

    def get_status_json(self):
        with open("status.json", "r") as fl:
            return json.load(fl)

    def get_tun_traffic(self, dev="tun0"):
        cmd_result = os.popen(f"ip --json stats show dev {dev} group link").read()
        cdm_dict = json.loads(cmd_result)
        return {
            "received": cdm_dict[0]["stats64"]["rx"]["bytes"],
            "sent": cdm_dict[0]["stats64"]["tx"]["bytes"],
        }

    def get_cpu_load(self):
        avg_load = [
            str(round(x / psutil.cpu_count() * 100)) for x in psutil.getloadavg()
        ]
        return [round(psutil.cpu_percent())] + avg_load

    def get_mem_free(self):
        mem = psutil.virtual_memory()
        return [mem.available, mem.total]
