import math

from flask import Flask, redirect, render_template, request, url_for

from bias_modes import (
    EmitterBiasInput,
    FixedBiasInput,
    solve_emitter_bias,
    solve_fixed_bias,
    validate_emitter,
    validate_fixed,
)
from bjt import BiasInput, validate, solve_base_loop
from independent import solve_nodal, compare

FIELD_NAMES = ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v")
ALL_FIELDS = ("vcc_v", "r1_ohm", "r2_ohm", "rb_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v")
RESISTOR_FIELDS = ("r1_ohm", "r2_ohm", "rb_ohm", "rc_ohm", "re_ohm")

UNIT_SCALE = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}
UNIT_SYMBOLS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}


def _display(raw_value, unit=None, suffix=""):
    value = (raw_value or "").strip()
    if not value:
        return "= —"
    if unit:
        return f"= {value} {UNIT_SYMBOLS.get(unit, UNIT_SYMBOLS['ohm'])}"
    return f"= {value}{(' ' + suffix) if suffix else ''}"


def circuit_labels(raw, units):
    """Format circuit-diagram text from user input. Display only, no bias math."""
    return {
        "vcc": _display(raw.get("vcc_v", ""), None, "V"),
        "r1": _display(raw.get("r1_ohm", ""), units.get("r1_ohm", "ohm")),
        "r2": _display(raw.get("r2_ohm", ""), units.get("r2_ohm", "ohm")),
        "rb": _display(raw.get("rb_ohm", ""), units.get("rb_ohm", "ohm")),
        "rc": _display(raw.get("rc_ohm", ""), units.get("rc_ohm", "ohm")),
        "re": _display(raw.get("re_ohm", ""), units.get("re_ohm", "ohm")),
        "beta": _display(raw.get("beta", "")),
        "vbe": _display(raw.get("vbe_v", ""), None, "V"),
    }

MODE_FIELDS = {
    "divider": FIELD_NAMES,
    "fixed": ("vcc_v", "rb_ohm", "rc_ohm", "beta", "vbe_v"),
    "emitter": ("vcc_v", "rb_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v"),
}

LABELS = {
    "vcc_v": "VCC",
    "r1_ohm": "R1",
    "r2_ohm": "R2",
    "rb_ohm": "RB",
    "rc_ohm": "RC",
    "re_ohm": "RE",
    "beta": "beta",
    "vbe_v": "VBE",
}

DEFAULTS = {name: "" for name in ALL_FIELDS}
DEFAULT_UNITS = {name: "ohm" for name in RESISTOR_FIELDS}

app = Flask(__name__)
app.jinja_env.globals["circuit_labels"] = circuit_labels


@app.get("/")
def index():
    return render_template(
        "index.html",
        raw=DEFAULTS,
        units=DEFAULT_UNITS,
        mode="divider",
    )


@app.get("/calculate")
def calculate_form():
    # Opening or refreshing the results URL directly would otherwise be a 405.
    return redirect(url_for("index"))


@app.post("/calculate")
def calculate():
    mode = request.form.get("mode", "divider") or "divider"
    raw = {name: request.form.get(name, "") for name in ALL_FIELDS}
    units = {name: request.form.get(f"{name}_unit", "ohm") for name in RESISTOR_FIELDS}
    units = {name: (unit if unit in UNIT_SCALE else "ohm") for name, unit in units.items()}

    if mode not in MODE_FIELDS:
        return render_template(
            "index.html",
            errors=["mode must be divider, fixed, or emitter"],
            raw=raw,
            units=units,
            mode="divider",
        ), 400

    field_names = MODE_FIELDS[mode]
    parsed = {}
    errors = []
    for name in field_names:
        try:
            parsed[name] = float(raw[name])
        except (ValueError, TypeError):
            errors.append(f"{LABELS[name]} must be a number")

    if not errors:
        for name in field_names:
            if name in RESISTOR_FIELDS:
                parsed[name] *= UNIT_SCALE[units[name]]
        if mode == "divider":
            bias = BiasInput(**parsed)
            errors = validate(bias)
        elif mode == "fixed":
            bias = FixedBiasInput(**parsed)
            errors = validate_fixed(bias)
        else:
            bias = EmitterBiasInput(**parsed)
            errors = validate_emitter(bias)

    if errors:
        return render_template(
            "index.html",
            errors=errors,
            raw=raw,
            units=units,
            mode=mode,
        ), 400

    if mode != "divider":
        result = solve_fixed_bias(bias) if mode == "fixed" else solve_emitter_bias(bias)
        rendered_values = (
            result["ib_a"], result["ic_a"], result["ie_a"],
            result["vb_v"], result["vc_v"], result["ve_v"], result["vce_v"],
        )
        if not all(math.isfinite(value) for value in rendered_values):
            return render_template(
                "index.html",
                errors=["values exceed the representable numeric range"],
                raw=raw,
                units=units,
                mode=mode,
            ), 400
        return render_template(
            "index.html",
            result=result,
            raw=raw,
            units=units,
            mode=mode,
        )

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
            mode=mode,
        ), 400

    return render_template(
        "index.html",
        base=base,
        nodal=nodal,
        report=report,
        raw=raw,
        units=units,
        mode=mode,
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
