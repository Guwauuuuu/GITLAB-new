import math

from flask import Flask, redirect, render_template, request, url_for

from bjt import BiasInput, validate, solve_base_loop
from independent import solve_nodal, compare

FIELD_NAMES = ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v")
RESISTOR_FIELDS = ("r1_ohm", "r2_ohm", "rc_ohm", "re_ohm")

LABELS = {
    "vcc_v": "VCC",
    "r1_ohm": "R1",
    "r2_ohm": "R2",
    "rc_ohm": "RC",
    "re_ohm": "RE",
    "beta": "beta",
    "vbe_v": "VBE",
}

DEFAULTS = {name: "" for name in FIELD_NAMES}
DEFAULT_UNITS = {name: "ohm" for name in RESISTOR_FIELDS}

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", raw=DEFAULTS, units=DEFAULT_UNITS)


@app.get("/calculate")
def calculate_form():
    # Opening or refreshing the results URL directly would otherwise be a 405.
    return redirect(url_for("index"))


@app.post("/calculate")
def calculate():
    raw = {name: request.form.get(name, "") for name in FIELD_NAMES}
    units = {name: request.form.get(f"{name}_unit", "ohm") for name in RESISTOR_FIELDS}
    units = {name: (unit if unit in ("ohm", "kohm") else "ohm") for name, unit in units.items()}

    parsed = {}
    errors = []
    for name in FIELD_NAMES:
        try:
            parsed[name] = float(raw[name])
        except (ValueError, TypeError):
            errors.append(f"{LABELS[name]} must be a number")

    if not errors:
        for name in RESISTOR_FIELDS:
            if units[name] == "kohm":
                parsed[name] *= 1000.0
        bias = BiasInput(**parsed)
        errors = validate(bias)

    if errors:
        return render_template("index.html", errors=errors, raw=raw, units=units), 400

    base = solve_base_loop(bias)
    nodal = solve_nodal(bias)
    report = compare(base, nodal)

    rendered_values = (
        base.vbb_v, base.rb_ohm, base.ib_a, base.ic_a, base.ie_a,
        base.ve_v, base.vc_v, base.vb_v, base.vce_v,
        nodal.ib_a, nodal.ic_a, nodal.ie_a,
        nodal.ve_v, nodal.vc_v, nodal.vb_v, nodal.vce_v,
    )
    if not all(math.isfinite(value) for value in rendered_values):
        return render_template(
            "index.html",
            errors=["values exceed the representable numeric range"],
            raw=raw,
            units=units,
        ), 400

    return render_template(
        "index.html",
        base=base,
        nodal=nodal,
        report=report,
        raw=raw,
        units=units,
    )


if __name__ == "__main__":
    import os
    import socket
    import threading
    import urllib.request
    import webbrowser

    host = os.environ.get("HOST", "127.0.0.1")
    start_port = int(os.environ.get("PORT", "5000"))
    open_browser = os.environ.get("OPEN_BROWSER") == "1"

    def is_healthy(port):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_free(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return True
            except OSError:
                return False

    if open_browser and is_healthy(start_port):
        print(f"App already running at http://127.0.0.1:{start_port}/")
        webbrowser.open(f"http://127.0.0.1:{start_port}/")
        raise SystemExit(0)

    port = next((p for p in range(start_port, start_port + 20) if is_free(p)), None)
    if port is None:
        print(f"No free port between {start_port} and {start_port + 19}.")
        raise SystemExit(1)

    url = f"http://127.0.0.1:{port}/"
    print(f"Local:   {url}")
    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        lan_ip = None
    if lan_ip and not lan_ip.startswith("127."):
        print(f"Network: http://{lan_ip}:{port}/")
    print("Press CTRL+C to stop.")

    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
