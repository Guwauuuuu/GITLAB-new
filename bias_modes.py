"""DC bias solutions for fixed bias and emitter bias (single supply).

All inputs use SI units: volts, amperes, ohms, and unitless beta. The solvers
return a flat dict whose keys carry the SI unit suffix (``_v``, ``_a``); the
template is responsible for display units such as uA and mA.
"""

from dataclasses import dataclass
import math


@dataclass
class FixedBiasInput:
    vcc_v: float
    rb_ohm: float
    rc_ohm: float
    beta: float
    vbe_v: float


@dataclass
class EmitterBiasInput:
    vcc_v: float
    rb_ohm: float
    rc_ohm: float
    re_ohm: float
    beta: float
    vbe_v: float


def _check_positive(value, label, errors):
    if not math.isfinite(value):
        errors.append(f"{label} must be a finite number")
    elif value <= 0:
        errors.append(f"{label} must be greater than 0")


def _check_beta(beta, errors):
    if not math.isfinite(beta):
        errors.append("beta must be a finite number")
    elif beta < 1:
        errors.append("beta must be at least 1")


def _check_vbe(vbe_v, vcc_v, errors):
    if not math.isfinite(vbe_v):
        errors.append("VBE must be a finite number")
    elif vbe_v <= 0:
        errors.append("VBE must be greater than 0")
    if math.isfinite(vbe_v) and math.isfinite(vcc_v) and vbe_v >= vcc_v:
        errors.append("VBE must be less than VCC")


def validate_fixed(bias: FixedBiasInput) -> list[str]:
    errors: list[str] = []
    _check_positive(bias.vcc_v, "VCC", errors)
    _check_positive(bias.rb_ohm, "RB", errors)
    _check_positive(bias.rc_ohm, "RC", errors)
    _check_beta(bias.beta, errors)
    _check_vbe(bias.vbe_v, bias.vcc_v, errors)
    return errors


def validate_emitter(bias: EmitterBiasInput) -> list[str]:
    errors: list[str] = []
    _check_positive(bias.vcc_v, "VCC", errors)
    _check_positive(bias.rb_ohm, "RB", errors)
    _check_positive(bias.rc_ohm, "RC", errors)
    _check_positive(bias.re_ohm, "RE", errors)
    _check_beta(bias.beta, errors)
    _check_vbe(bias.vbe_v, bias.vcc_v, errors)
    return errors


def _result(mode, ib, ic, ie, vb, vc, ve, vce) -> dict:
    if ib <= 0:
        region = "cutoff"
    elif vce < 0.2:
        region = "saturation"
    else:
        region = "active"
    return {
        "mode": mode,
        "ib_a": ib,
        "ic_a": ic,
        "ie_a": ie,
        "vb_v": vb,
        "vc_v": vc,
        "ve_v": ve,
        "vce_v": vce,
        "region": region,
        "in_active": region == "active",
    }


def solve_fixed_bias(bias: FixedBiasInput) -> dict:
    ib = (bias.vcc_v - bias.vbe_v) / bias.rb_ohm
    ic = bias.beta * ib
    ie = (bias.beta + 1) * ib
    ve = 0.0
    vc = bias.vcc_v - ic * bias.rc_ohm
    vb = bias.vbe_v
    vce = vc - ve
    return _result("fixed", ib, ic, ie, vb, vc, ve, vce)


def solve_emitter_bias(bias: EmitterBiasInput) -> dict:
    ib = (bias.vcc_v - bias.vbe_v) / (bias.rb_ohm + (bias.beta + 1) * bias.re_ohm)
    ic = bias.beta * ib
    ie = (bias.beta + 1) * ib
    ve = ie * bias.re_ohm
    vc = bias.vcc_v - ic * bias.rc_ohm
    vb = ve + bias.vbe_v
    vce = vc - ve
    return _result("emitter", ib, ic, ie, vb, vc, ve, vce)
