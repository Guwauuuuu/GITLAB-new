import math

from flask import Flask, render_template, request

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

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))

    print(f"Local:   http://127.0.0.1:{port}/")
    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        lan_ip = None
    if lan_ip and not lan_ip.startswith("127."):
        print(f"Network: http://{lan_ip}:{port}/")
    print("Press CTRL+C to stop.")

    app.run(host=host, port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
