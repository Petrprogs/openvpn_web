from flask import Flask, render_template, request, send_file, redirect, make_response
from managment_api import ManagementAPI
from functools import wraps
import os

STATUS_LOG_PATH = "/var/log/openvpn/status.log"  # Path to status.log
CONFIGS_STORE = "/root"

app = Flask(__name__)

api = ManagementAPI(STATUS_LOG_PATH) # Initialize API class


def basic_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for the Authorization header
        auth = request.authorization
        if not auth or auth.username != "openvpn" or auth.password != "vpn":
            # If authorization fails, prompt for login
            return make_response(
                "Could not verify!",
                401,
                {"WWW-Authenticate": 'Basic realm="Login required"'},
            )

        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
@basic_auth_required
def home_page():
    tun_traff = api.get_tun_traffic()
    cpu_ld = api.get_cpu_load()
    mem = api.get_mem_free()
    status = api.get_status()
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
@basic_auth_required
def clients_page():
    status = api.get_status()

    return render_template(
        "clients.html",
        clients=status["clients"],
        convert_bytes=convert_bytes
    )


@app.route("/add_client", methods=["GET", "POST"])
@basic_auth_required
def add_client_page():
    if request.method.lower() == 'get':
        return render_template(
            "add_client.html"
        )
    else:
        config = api.new_client(request.form.get("name"))
        return render_template("download.html", config=config)


@app.route("/download/<config>")
@basic_auth_required
def download(config):
    if os.path.exists(f"{CONFIGS_STORE}/{config}"):
        return send_file(f"{CONFIGS_STORE}/{config}")
    else:
        return "Not found"

@app.route("/revoke_client")
def revoke_clients_page():
    clients = api.get_clients()
    return render_template("revoke_client.html", clients=clients)


@app.route("/revoke_client/<config>")
@basic_auth_required
def revoke_client_page(config):
    clients = api.revoke_client(config)
    return redirect("/revoke_client", 302)


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
