from flask import Flask, render_template
from managment_api import ManagementAPI
import status_sync
from threading import Thread

TELNET_HOST = "localhost"  # Openvpn management host
TELNET_PORT = 7505  # Openvpn management port

app = Flask(__name__)

api = ManagementAPI(TELNET_HOST, TELNET_PORT) # Initialize API class
Thread(target=status_sync.sync).start() # Start openvpn status sync thread


@app.route("/")
def home_page():
    tun_traff = api.get_tun_traffic()
    cpu_ld = api.get_cpu_load()
    mem = api.get_mem_free()
    status = api.get_status_json()
    return render_template(
        "index.html",
        rx=convert_bytes(tun_traff["received"]),
        tx=convert_bytes(tun_traff["sent"]),
        cpu_ld=cpu_ld,
        mem=[convert_bytes(mem[0]).split(" ")[0], convert_bytes(mem[1])],
        clients_count=len(status["clients"]),
        datetime=status["datetime"]
    )

@app.route("/clients")
def clients_page():
    status = api.get_status_json()
    
    return render_template(
        "clients.html",
        clients=status["clients"],
        convert_bytes=convert_bytes
    )

def convert_bytes(size):
    """
    Convert bytes to a more suitable unit (KB, MB, GB).
    :param size: Size in bytes
    :return: Size as a string with appropriate unit
    """
    if size < 0:
        return "Invalid size"

    # Conversion factors
    units = ["B", "KB", "MB", "GB"]
    factor = 1024
    unit_index = 0

    # Convert bytes to higher units
    while size >= factor and unit_index < len(units) - 1:
        size /= factor
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"

if __name__ == "__main__":
    app.run("0.0.0.0", debug=False)
