import math

from flask import Flask, jsonify, redirect, render_template, request, url_for

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
from spice_engine import (
    AC_VIN_REFERENCE,
    CECircuitParams,
    simulate_ce,
    validate_ce_params,
)

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


# ---------------------------------------------------------------------------
# Common-Emitter Amplifier Simulator v1 (real ngspice runs)
# ---------------------------------------------------------------------------

CE_ANALYSES = ("op", "ac", "tran")

CE_FORM_DEFAULTS = {
    "analysis": "op",
    "vcc_v": "12",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1", "re_unit": "kohm",
    "rl": "10", "rl_unit": "kohm",
    "cin": "10", "cin_unit": "uf",
    "cout": "10", "cout_unit": "uf",
    "source_amp": "10", "source_amp_unit": "mv",
    "source_freq": "1", "source_freq_unit": "khz",
    "beta": "100",
    "vbe_v": "0.7",
}

CE_RESISTOR_UNITS = (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ"))
CE_CAP_UNITS = (("uf", "µF"), ("nf", "nF"), ("pf", "pF"), ("f", "F"))
CE_AMP_UNITS = (("mv", "mV"), ("v", "V"))
CE_FREQ_UNITS = (("hz", "Hz"), ("khz", "kHz"), ("mhz", "MHz"))

CE_RESISTOR_SCALE = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}
CE_CAP_SCALE = {"uf": 1e-6, "nf": 1e-9, "pf": 1e-12, "f": 1.0}
CE_AMP_SCALE = {"mv": 1e-3, "v": 1.0}
CE_FREQ_SCALE = {"hz": 1.0, "khz": 1e3, "mhz": 1e6}

CE_QUANTITIES = (
    ("r1", "R1", "r1_unit", CE_RESISTOR_SCALE, "ohm"),
    ("r2", "R2", "r2_unit", CE_RESISTOR_SCALE, "ohm"),
    ("rc", "RC", "rc_unit", CE_RESISTOR_SCALE, "ohm"),
    ("re", "RE", "re_unit", CE_RESISTOR_SCALE, "ohm"),
    ("rl", "RL", "rl_unit", CE_RESISTOR_SCALE, "ohm"),
    ("cin", "Cin", "cin_unit", CE_CAP_SCALE, "f"),
    ("cout", "Cout", "cout_unit", CE_CAP_SCALE, "f"),
    ("source_amp", "Source amplitude", "source_amp_unit", CE_AMP_SCALE, "v"),
    ("source_freq", "Source frequency", "source_freq_unit", CE_FREQ_SCALE, "hz"),
)

CE_UNITS_METADATA = {
    "voltage": "V",
    "current": "A",
    "resistance": "Ω",
    "capacitance": "F",
    "frequency": "Hz",
    "time": "s",
    "gain": "V/V",
    "gain_db": "dB",
    "phase": "deg",
}


def _ce_payload():
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return request.form


def _ce_number(payload, key, label, errors):
    raw = payload.get(key, CE_FORM_DEFAULTS.get(key, ""))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        errors.append(f"{label} must be a number")
        return None
    if not math.isfinite(value):
        errors.append(f"{label} must be a finite number")
        return None
    return value


def _ce_quantity(payload, field, label, unit_field, scale, default_unit, errors):
    value = _ce_number(payload, field, label, errors)
    if value is None:
        return None
    unit = payload.get(unit_field, default_unit)
    if unit not in scale:
        unit = default_unit
    scaled = value * scale[unit]
    if not math.isfinite(scaled):
        errors.append(f"{label} exceeds the representable numeric range")
        return None
    return scaled


@app.get("/ce-simulator")
def ce_simulator():
    return render_template(
        "ce_simulator.html",
        defaults=CE_FORM_DEFAULTS,
        resistor_units=CE_RESISTOR_UNITS,
        cap_units=CE_CAP_UNITS,
        amp_units=CE_AMP_UNITS,
        freq_units=CE_FREQ_UNITS,
        vin_reference=AC_VIN_REFERENCE,
    )


@app.post("/api/ce-simulate")
def ce_simulate():
    payload = _ce_payload()
    raw_analysis = payload.get("analysis")
    analysis = str(raw_analysis).strip() if raw_analysis else "op"
    errors = []
    if analysis not in CE_ANALYSES:
        errors.append("analysis must be op, ac, or tran")

    values = {}
    for field, label, unit_field, scale, default_unit in CE_QUANTITIES:
        values[field] = _ce_quantity(
            payload, field, label, unit_field, scale, default_unit, errors
        )

    vcc = _ce_number(payload, "vcc_v", "VCC", errors)
    beta = _ce_number(payload, "beta", "beta", errors)
    vbe = _ce_number(payload, "vbe_v", "VBE", errors)

    if beta is not None and beta < 1:
        errors.append("beta must be at least 1")
    if vbe is not None:
        if vbe <= 0:
            errors.append("VBE must be greater than 0")
        elif vcc is not None and vbe >= vcc:
            errors.append("VBE must be less than VCC")

    if errors:
        return jsonify({
            "status": "error",
            "analysis": analysis,
            "errors": errors,
        }), 400

    params = CECircuitParams(
        vcc_v=vcc,
        r1_ohm=values["r1"],
        r2_ohm=values["r2"],
        rc_ohm=values["rc"],
        re_ohm=values["re"],
        rl_ohm=values["rl"],
        cin_f=values["cin"],
        cout_f=values["cout"],
        amp_v=values["source_amp"],
        freq_hz=values["source_freq"],
    )
    params_errors = validate_ce_params(params)
    if params_errors:
        return jsonify({
            "status": "error",
            "analysis": analysis,
            "errors": params_errors,
        }), 400

    result = simulate_ce(params, analysis)
    if result["status"] != "success":
        status_code = 504 if "timed out" in result.get("error", "").lower() else 500
        body = {
            "status": "error",
            "analysis": analysis,
            "model_name": result.get("model_name", "Q2N2222"),
            "engine": {"name": "ngspice_con", "status": "error"},
            "error": result.get("error", "ngspice simulation failed"),
        }
        if result.get("stderr"):
            body["stderr"] = result["stderr"]
        return jsonify(body), status_code

    bias = BiasInput(
        vcc_v=vcc,
        r1_ohm=values["r1"],
        r2_ohm=values["r2"],
        rc_ohm=values["rc"],
        re_ohm=values["re"],
        beta=beta,
        vbe_v=vbe,
    )
    base = solve_base_loop(bias)
    analytical_values = (
        base.vb_v, base.ve_v, base.vc_v, base.vce_v,
        base.ib_a, base.ic_a, base.ie_a,
    )
    if all(math.isfinite(value) for value in analytical_values):
        analytical = {
            "source": "Lab 3 analytical (bjt.py)",
            "beta": beta,
            "vbe_v": vbe,
            "vb_v": base.vb_v,
            "ve_v": base.ve_v,
            "vc_v": base.vc_v,
            "vce_v": base.vce_v,
            "ib_a": base.ib_a,
            "ic_a": base.ic_a,
            "ie_a": base.ie_a,
            "region": base.region,
            "in_active": base.in_active,
        }
    else:
        analytical = {
            "source": "Lab 3 analytical (bjt.py)",
            "unavailable": True,
            "reason": "values exceed the representable numeric range",
        }

    return jsonify({
        "status": "success",
        "analysis": analysis,
        "model_name": result["model_name"],
        "engine": {
            "name": "ngspice_con",
            "status": "success",
            "elapsed_s": result.get("elapsed_s"),
        },
        "units": CE_UNITS_METADATA,
        "params": {
            "vcc_v": vcc,
            "r1_ohm": values["r1"],
            "r2_ohm": values["r2"],
            "rc_ohm": values["rc"],
            "re_ohm": values["re"],
            "rl_ohm": values["rl"],
            "cin_f": values["cin"],
            "cout_f": values["cout"],
            "source_amp_v": values["source_amp"],
            "source_freq_hz": values["source_freq"],
            "beta": beta,
            "vbe_v": vbe,
        },
        "spice": result["data"],
        "analytical": analytical,
        "netlist": result.get("netlist", ""),
    })


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
