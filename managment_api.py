import os
import json
import psutil
import time
import re
import subprocess


class ManagementAPI:
    def __init__(self, status_log="/var/log/openvpn/status.log"):
        self.status_log = status_log

    def get_status(self) -> dict:
        with open(self.status_log, "r") as fl:
            raw_data = fl.readlines()
            processed_status = self.__parse_status__(raw_data)
            return processed_status

    def __parse_status__(self, raw_string):
        server_datetime = raw_string[1].split(",")[1]
        clients = []
        for client in raw_string[3:]:
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

    def get_tun_traffic(self, dev="tun0"):
        cmd_result = os.popen(f"ip --json stats show dev {dev} group link").read()
        try:
            cdm_dict = json.loads(cmd_result)
            return {
                "received": cdm_dict[0]["stats64"]["rx"]["bytes"],
                "sent": cdm_dict[0]["stats64"]["tx"]["bytes"],
            }
        except:
            return "N/A"

    def get_cpu_load(self):
        avg_load = [
            str(round(x / psutil.cpu_count() * 100)) for x in psutil.getloadavg()
        ]
        return [round(psutil.cpu_percent())] + avg_load

    def get_mem_free(self):
        mem = psutil.virtual_memory()
        return [mem.available, mem.total]

    def new_client(self, client="", ovpn_store="/root"):
        with open("/etc/openvpn/easy-rsa/pki/index.txt", "r") as f:
            client_exists = sum(1 for line in f if f"/CN={client}" in line)
        if client_exists == 1:
            print(
                "\nThe specified client CN was already found in easy-rsa, please choose another name."
            )
            return f"{client}.ovpn"
        os.chdir("/etc/openvpn/easy-rsa/")
        my_env = os.environ.copy()
        my_env["EASYRSA_CERT_EXPIRE"] = "3650"
        print(
            subprocess.run(
                f"/etc/openvpn/easy-rsa/easyrsa --batch build-client-full {client} nopass",
                env=my_env,
                shell=True,
                stdout=subprocess.PIPE,
            ).stdout.decode()
        )
        print(f"Client {client} added.")
        # Determine if we use tls-auth or tls-crypt
        tls_sig = None
        with open("/etc/openvpn/server.conf", "r") as f:
            if any(line.startswith("tls-crypt") for line in f):
                tls_sig = "1"
            elif any(line.startswith("tls-auth") for line in f):
                tls_sig = "2"

        # Generates the custom client.ovpn
        with open(f"/etc/openvpn/client-template.txt", "r") as template_file, open(
            f"{ovpn_store}/{client}.ovpn", "w"
        ) as output_file:
            output_file.write(template_file.read())

            output_file.write("<ca>\n")
            with open("/etc/openvpn/easy-rsa/pki/ca.crt", "r") as ca_file:
                output_file.write(ca_file.read())
            output_file.write("</ca>\n")

            output_file.write("<cert>\n")
            with open(
                f"/etc/openvpn/easy-rsa/pki/issued/{client}.crt", "r"
            ) as cert_file:
                output_file.write(cert_file.read())
            output_file.write("</cert>\n")

            output_file.write("<key>\n")
            with open(
                f"/etc/openvpn/easy-rsa/pki/private/{client}.key", "r"
            ) as key_file:
                output_file.write(key_file.read())
            output_file.write("</key>\n")

            if tls_sig == "1":
                output_file.write("<tls-crypt>\n")
                with open("/etc/openvpn/tls-crypt.key", "r") as tls_file:
                    output_file.write(tls_file.read())
                output_file.write("</tls-crypt>\n")
            elif tls_sig == "2":
                output_file.write("key-direction 1\n")
                output_file.write("<tls-auth>\n")
                with open("/etc/openvpn/tls-auth.key", "r") as auth_file:
                    output_file.write(auth_file.read())
                output_file.write("</tls-auth>\n")
        return f"{client}.ovpn"

    def get_clients(self):
        with open("/etc/openvpn/easy-rsa/pki/index.txt", "r") as f:
            clients = [line for line in f.readlines()[1:] if line.startswith("V")]
            if len(clients) == 0:
                return "No clients"
            return_list = []
            for index, client_line in enumerate(clients, start=1):
                client_name = client_line.split("=")[1].strip()
                print(client_name)
                return_list.append(client_name)
            return return_list

    def revoke_client(self, config_name, ovpn_store="/root"):
        # Change directory to /etc/openvpn/easy-rsa
        os.chdir("/etc/openvpn/easy-rsa")

        # Revoke the client certificate
        print(subprocess.run(f"./easyrsa --batch revoke {config_name}", shell=True, stdout=subprocess.PIPE).stdout.decode())

        # Generate a new CRL
        os.environ["EASYRSA_CRL_DAYS"] = "3650"
        print(
            subprocess.run(
                "./easyrsa gen-crl", shell=True, stdout=subprocess.PIPE
            ).stdout.decode()
        )

        # Update the CRL file
        os.remove("/etc/openvpn/crl.pem")
        os.replace("/etc/openvpn/easy-rsa/pki/crl.pem", "/etc/openvpn/crl.pem")

        # Change permissions
        os.chmod("/etc/openvpn/crl.pem", 0o644)

        # Delete the client .ovpn file if it exists
        client_ovpn_path = f"{ovpn_store}/{config_name}.ovpn"
        if os.path.isfile(client_ovpn_path):
            os.remove(client_ovpn_path)

        # Remove the IP address from ipp.txt
        with open("/etc/openvpn/ipp.txt", "r") as f:
            lines = f.readlines()
        with open("/etc/openvpn/ipp.txt", "w") as f:
            for line in lines:
                if not line.startswith(config_name + ","):
                    f.write(line)

        # Backup the index file
        with open("/etc/openvpn/easy-rsa/pki/index.txt", "r") as f:
            index_content = f.read()
        with open("/etc/openvpn/easy-rsa/pki/index.txt.bk", "w") as backup_file:
            backup_file.write(index_content)

        print(f"\nCertificate for client {config_name} revoked.")
        return True
