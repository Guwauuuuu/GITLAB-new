"""Real ngspice simulation engine for the reference common-emitter stage.

Reference circuit (voltage-divider bias, unbypassed RE, no emitter bypass
capacitor)::

    VCC -- R1 --+-- RC --+-- Cout --+-- Vout
                |        |          |
                R2       Q1 (C)     RL
                |        |          |
               GND       Q1 (E)    GND
                         |
                         RE
                         |
                        GND

    Vin -- Cin -- Q1 (B)

Every simulation runs ``ngspice_con -b circuit.cir`` in a private temporary
directory. Nothing is cached between runs: a failure never leaves data from
an earlier run behind. Results are only reported as ``success`` when ngspice
exited cleanly and every parsed number is finite.
"""

from dataclasses import dataclass
import math
import pathlib
import re
import subprocess
import tempfile
import time

ENGINE_NAME = "ngspice_con"
DEFAULT_MODEL = "Q2N2222"

# Standard 2N2222 Gummel-Poon model shipped with ngspice's examples.
MODEL_CARD = (
    ".model Q2N2222 NPN(IS=14.34f XTI=3 EG=1.11 VAF=74.03 BF=255.9 "
    "NE=1.307 ISE=14.34f IKF=.2847 XTB=1.5 BR=6.092 NC=2 ISC=0 IKR=0 "
    "RC=1 CJC=7.306p MJC=.3416 VJC=.75 FC=.5 CJE=22.01p MJE=.377 "
    "VJE=.75 TR=46.91n TF=411.1p ITF=.6 VTF=1.7 XTF=3 RB=10)"
)

ANALYSES = ("op", "ac", "tran")

BASELINE_DEFAULTS = {
    "vcc_v": 12.0,
    "r1_ohm": 100e3,
    "r2_ohm": 22e3,
    "rc_ohm": 2.2e3,
    "re_ohm": 1e3,
    "rl_ohm": 10e3,
    "cin_f": 10e-6,
    "cout_f": 10e-6,
    "amp_v": 0.01,
    "freq_hz": 1000.0,
}

AC_START_HZ = 10.0
AC_STOP_HZ = 10e6
AC_POINTS_PER_DECADE = 25
AC_VIN_REFERENCE = "AC 1 V at input source node (before Cin)"


@dataclass
class CECircuitParams:
    vcc_v: float
    r1_ohm: float
    r2_ohm: float
    rc_ohm: float
    re_ohm: float
    rl_ohm: float
    cin_f: float
    cout_f: float
    amp_v: float
    freq_hz: float


def validate_ce_params(params: CECircuitParams) -> list[str]:
    """Return human-readable errors for non-physical CE component values."""
    errors: list[str] = []
    checks = (
        ("VCC", params.vcc_v),
        ("R1", params.r1_ohm),
        ("R2", params.r2_ohm),
        ("RC", params.rc_ohm),
        ("RE", params.re_ohm),
        ("RL", params.rl_ohm),
        ("Cin", params.cin_f),
        ("Cout", params.cout_f),
        ("Source amplitude", params.amp_v),
        ("Source frequency", params.freq_hz),
    )
    for label, value in checks:
        if not math.isfinite(value):
            errors.append(f"{label} must be a finite number")
        elif value <= 0:
            errors.append(f"{label} must be greater than 0")
    return errors


def _spice_number(value: float) -> str:
    """Format a float so ngspice parses it without thousands separators."""
    return f"{value:.10g}"


def _control_block(analysis: str) -> str:
    if analysis == "op":
        commands = (
            "op",
            "wrdata op.txt v(b) v(e) v(c) @q1[ib] @q1[ic]",
        )
    elif analysis == "ac":
        commands = (
            f"ac dec {AC_POINTS_PER_DECADE} {_spice_number(AC_START_HZ)} "
            f"{_spice_number(AC_STOP_HZ)}",
            "wrdata ac.txt vm(out) vp(out)",
        )
    elif analysis == "tran":
        commands = (
            "tran {tstep} {tstop}",
            "wrdata tran.txt v(in) v(out)",
        )
    else:
        raise ValueError(f"unsupported analysis: {analysis}")
    return ".control\nset wr_vecnames\nset wr_singlescale\n" + "\n".join(commands) + "\nquit\n.endc"


def build_netlist(
    params: CECircuitParams,
    analysis: str,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """Return a complete ngspice netlist for ``analysis`` (op/ac/tran)."""
    if analysis not in ANALYSES:
        raise ValueError(f"unsupported analysis: {analysis}")

    period = 1.0 / params.freq_hz
    # 4 cycles with 200 samples per cycle keeps transient data small but
    # resolves the 180 degree inversion clearly.
    tstep = period / 200.0
    tstop = period * 4.0

    control = _control_block(analysis)
    if analysis == "tran":
        control = control.replace("{tstep}", _spice_number(tstep))
        control = control.replace("{tstop}", _spice_number(tstop))

    lines = [
        "* Common-emitter amplifier, voltage-divider bias, unbypassed RE",
        f"VCC vcc 0 DC {_spice_number(params.vcc_v)}",
        f"R1 vcc b {_spice_number(params.r1_ohm)}",
        f"R2 b 0 {_spice_number(params.r2_ohm)}",
        f"RC vcc c {_spice_number(params.rc_ohm)}",
        f"RE e 0 {_spice_number(params.re_ohm)}",
        f"Cin in b {_spice_number(params.cin_f)}",
        f"Cout c out {_spice_number(params.cout_f)}",
        f"RL out 0 {_spice_number(params.rl_ohm)}",
        "Vin in 0 DC 0 AC 1 "
        f"SIN(0 {_spice_number(params.amp_v)} {_spice_number(params.freq_hz)})",
        f"Q1 c b e {model_name}",
        MODEL_CARD if model_name == DEFAULT_MODEL else f".model {model_name} NPN(BF=200 VAF=100)",
        control,
        ".end",
        "",
    ]
    return "\n".join(lines)


class SimulationError(Exception):
    """Raised for engine, parsing, or data-quality failures."""


def _column(header: list[str], name: str, fallback: int, width: int) -> int:
    for index, label in enumerate(header):
        if label.lower() == name:
            return index
    if fallback < width:
        return fallback
    raise SimulationError(f"missing {name!r} column (found {header or 'no header'})")


def run_ngspice(
    netlist_text: str,
    output_filename: str,
    timeout_s: float = 10.0,
    executable: str = ENGINE_NAME,
) -> dict:
    """Run one batch simulation in an isolated temporary directory.

    Returns ``{"status": "success", "text": ...}`` or
    ``{"status": "error", "error": ..., "stderr": ...}``. The temporary
    directory is always destroyed, so a failed run cannot leak stale data
    into a later one.
    """
    with tempfile.TemporaryDirectory(prefix="ce_sim_") as tmpdir:
        workdir = pathlib.Path(tmpdir)
        netlist_path = workdir / "circuit.cir"
        netlist_path.write_text(netlist_text, encoding="utf-8")
        started = time.monotonic()
        try:
            proc = subprocess.run(
                [executable, "-b", "circuit.cir"],
                cwd=workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                shell=False,
            )
        except FileNotFoundError:
            return {
                "status": "error",
                "error": f"ngspice executable not found: {executable}",
                "stderr": "",
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"ngspice timed out after {timeout_s:g} s",
                "stderr": "",
            }
        except OSError as exc:
            return {"status": "error", "error": f"could not start ngspice: {exc}", "stderr": ""}

        elapsed = time.monotonic() - started
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.returncode != 0:
            return {
                "status": "error",
                "error": f"ngspice exited with code {proc.returncode}",
                "stderr": _trim(combined),
                "elapsed_s": elapsed,
            }
        # ngspice can print an error yet exit 0 (e.g. "no such vector").
        match = re.search(r"(?im)^\s*(error|fatal)[:\s]", combined)
        if match:
            return {
                "status": "error",
                "error": f"ngspice reported an error: {match.group(0).strip()}",
                "stderr": _trim(combined),
                "elapsed_s": elapsed,
            }
        output_path = workdir / output_filename
        try:
            text = output_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {
                "status": "error",
                "error": f"could not read {output_filename}: {exc}",
                "stderr": _trim(combined),
                "elapsed_s": elapsed,
            }
        return {
            "status": "success",
            "text": text,
            "stderr": _trim(combined),
            "stdout": _trim(proc.stdout or ""),
            "elapsed_s": elapsed,
        }


def _trim(text: str, limit: int = 4000) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def _parse_op(text: str) -> dict:
    header, rows = _parse_wrdata_text(text, "op.txt")
    width = len(rows[0])
    vb_i = _column(header, "v(b)", 1, width)
    ve_i = _column(header, "v(e)", 2, width)
    vc_i = _column(header, "v(c)", 3, width)
    ib_i = _column(header, "@q1[ib]", 4, width)
    ic_i = _column(header, "@q1[ic]", 5, width)
    row = rows[0]
    vb, ve, vc = row[vb_i], row[ve_i], row[vc_i]
    ib, ic = row[ib_i], row[ic_i]
    vce = vc - ve

    if ic < 1e-9:
        region = "cutoff"
    elif vce < 0.2:
        region = "saturation"
    else:
        region = "active"

    return {
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vce_v": vce,
        "ib_a": ib,
        "ic_a": ic,
        "region": region,
        "in_active": region == "active",
    }


def _parse_wrdata_text(text: str, name: str) -> tuple[list[str], list[list[float]]]:
    header: list[str] = []
    rows: list[list[float]] = []
    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        try:
            values = [float(token) for token in tokens]
        except ValueError:
            header = tokens
            continue
        rows.append(values)
    if not rows:
        raise SimulationError(f"{name} contains no data")
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        raise SimulationError(f"{name} has inconsistent column counts: {sorted(widths)}")
    for row in rows:
        if not all(math.isfinite(value) for value in row):
            raise SimulationError(f"{name} contains NaN or infinite values")
    if len(rows[0]) < 2:
        raise SimulationError(f"{name} has fewer than two columns")
    return header, rows


def _parse_ac(text: str) -> dict:
    header, rows = _parse_wrdata_text(text, "ac.txt")
    width = len(rows[0])
    f_i = _column(header, "frequency", 0, width)
    mag_i = _column(header, "vm(out)", 1, width)
    phase_i = _column(header, "vp(out)", 2, width)

    freq_hz: list[float] = []
    gain_vv: list[float] = []
    gain_db: list[float] = []
    raw_phase_deg: list[float] = []
    for row in rows:
        frequency = row[f_i]
        magnitude = row[mag_i]
        if frequency <= 0:
            raise SimulationError("ac.txt contains a non-positive frequency")
        freq_hz.append(frequency)
        # Vin is a 1 V AC source, so |Vout| is the transfer magnitude.
        gain_vv.append(magnitude)
        gain_db.append(20.0 * math.log10(magnitude) if magnitude > 0 else float("-inf"))
        raw_phase_deg.append(math.degrees(row[phase_i]))

    # ngspice wraps vp() into (-180, 180]. The CE stage sits at -180 deg in
    # midband, so unwrap the sweep into one continuous curve instead of
    # letting a +180/-180 jump masquerade as a phase reversal.
    phase_deg: list[float] = []
    offset = 0.0
    for value in raw_phase_deg:
        if phase_deg:
            while value + offset - phase_deg[-1] > 180.0:
                offset -= 360.0
            while value + offset - phase_deg[-1] < -180.0:
                offset += 360.0
        phase_deg.append(value + offset)

    if not all(freq_hz[i] < freq_hz[i + 1] for i in range(len(freq_hz) - 1)):
        raise SimulationError("ac.txt frequencies are not strictly increasing")
    if not all(math.isfinite(value) for value in gain_db):
        raise SimulationError("ac.txt contains a non-positive gain")

    peak_index = max(range(len(gain_db)), key=lambda i: gain_db[i])
    peak_db = gain_db[peak_index]
    threshold = peak_db - 3.0103

    f_low = None
    for i in range(peak_index, -1, -1):
        if gain_db[i] < threshold:
            f_low = freq_hz[i]
            break
    f_high = None
    for i in range(peak_index, len(gain_db)):
        if gain_db[i] < threshold:
            f_high = freq_hz[i]
            break

    return {
        "freq_hz": freq_hz,
        "gain_vv": gain_vv,
        "gain_db": gain_db,
        "phase_deg": phase_deg,
        "vin_reference": AC_VIN_REFERENCE,
        "midband_freq_hz": freq_hz[peak_index],
        "midband_gain_vv": gain_vv[peak_index],
        "midband_gain_db": peak_db,
        "midband_phase_deg": phase_deg[peak_index],
        "f_low_3db_hz": f_low,
        "f_high_3db_hz": f_high,
    }


def _parse_tran(text: str) -> dict:
    header, rows = _parse_wrdata_text(text, "tran.txt")
    width = len(rows[0])
    t_i = _column(header, "time", 0, width)
    in_i = _column(header, "v(in)", 1, width)
    out_i = _column(header, "v(out)", 2, width)

    time_s = [row[t_i] for row in rows]
    vin_v = [row[in_i] for row in rows]
    vout_v = [row[out_i] for row in rows]
    if not all(time_s[i] < time_s[i + 1] for i in range(len(time_s) - 1)):
        raise SimulationError("tran.txt time values are not strictly increasing")

    vin_pp = max(vin_v) - min(vin_v)
    vout_pp = max(vout_v) - min(vout_v)
    # Ignore the first cycle so coupling-capacitor settling cannot decide
    # whether the steady-state output is inverted.
    start = time_s[0] + (time_s[-1] - time_s[0]) / 4.0
    tail = [i for i, t in enumerate(time_s) if t >= start]
    dot = sum(vin_v[i] * vout_v[i] for i in tail)

    return {
        "time_s": time_s,
        "vin_v": vin_v,
        "vout_v": vout_v,
        "summary": {
            "vin_pp_v": vin_pp,
            "vout_pp_v": vout_pp,
            "gain_vv": (vout_pp / vin_pp) if vin_pp > 0 else None,
            "phase_inverted": dot < 0,
        },
    }


def simulate_ce(
    params: CECircuitParams,
    analysis: str,
    timeout_s: float = 10.0,
    executable: str = ENGINE_NAME,
    model_name: str = DEFAULT_MODEL,
) -> dict:
    """Validate, run, and parse one real ngspice analysis.

    Never returns ``data`` for an error: a failed run has no traces to show.
    """
    base = {
        "analysis": analysis,
        "model_name": model_name,
        "engine": executable,
    }
    if analysis not in ANALYSES:
        return {**base, "status": "error", "error": f"unsupported analysis: {analysis}"}

    errors = validate_ce_params(params)
    if errors:
        return {**base, "status": "error", "error": "; ".join(errors), "errors": errors}

    try:
        netlist = build_netlist(params, analysis, model_name=model_name)
    except ValueError as exc:
        return {**base, "status": "error", "error": str(exc)}

    output_file = {"op": "op.txt", "ac": "ac.txt", "tran": "tran.txt"}[analysis]
    run = run_ngspice(netlist, output_file, timeout_s=timeout_s, executable=executable)
    if run["status"] != "success":
        return {
            **base,
            "status": "error",
            "error": run["error"],
            "stderr": run.get("stderr", ""),
        }

    try:
        if analysis == "op":
            data = _parse_op(run["text"])
        elif analysis == "ac":
            data = _parse_ac(run["text"])
        else:
            data = _parse_tran(run["text"])
    except SimulationError as exc:
        return {
            **base,
            "status": "error",
            "error": f"could not parse ngspice output: {exc}",
            "stderr": run.get("stderr", ""),
        }

    return {
        **base,
        "status": "success",
        "data": data,
        "netlist": netlist,
        "stderr": run.get("stderr", ""),
        "elapsed_s": run.get("elapsed_s"),
    }
