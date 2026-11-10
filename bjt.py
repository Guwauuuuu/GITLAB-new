"""DC bias analysis for an NPN common-emitter stage with voltage-divider bias.

All resistances in ohms, all voltages in volts, beta is unitless.
The reported solution is always the active-region solution; callers use
``region`` / ``in_active`` to decide whether it is physical.
"""

from dataclasses import dataclass
import math


@dataclass
class BiasInput:
    vcc_v: float
    r1_ohm: float
    r2_ohm: float
    rc_ohm: float
    re_ohm: float
    beta: float
    vbe_v: float


@dataclass
class BiasResult:
    vbb_v: float
    rb_ohm: float
    ib_a: float
    ic_a: float
    ie_a: float
    ve_v: float
    vc_v: float
    vb_v: float
    vce_v: float
    region: str
    in_active: bool


def validate(bias: BiasInput) -> list[str]:
    errors: list[str] = []
    if not math.isfinite(bias.vcc_v):
        errors.append("VCC must be a finite number")
    elif bias.vcc_v <= 0:
        errors.append("VCC must be greater than 0")
    if not math.isfinite(bias.r1_ohm):
        errors.append("R1 must be a finite number")
    elif bias.r1_ohm <= 0:
        errors.append("R1 must be greater than 0")
    if not math.isfinite(bias.r2_ohm):
        errors.append("R2 must be a finite number")
    elif bias.r2_ohm <= 0:
        errors.append("R2 must be greater than 0")
    if not math.isfinite(bias.rc_ohm):
        errors.append("RC must be a finite number")
    elif bias.rc_ohm <= 0:
        errors.append("RC must be greater than 0")
    if not math.isfinite(bias.re_ohm):
        errors.append("RE must be a finite number")
    elif bias.re_ohm <= 0:
        errors.append("RE must be greater than 0")
    if not math.isfinite(bias.beta):
        errors.append("beta must be a finite number")
    elif bias.beta < 1:
        errors.append("beta must be at least 1")
    if not math.isfinite(bias.vbe_v):
        errors.append("VBE must be a finite number")
    elif bias.vbe_v <= 0:
        errors.append("VBE must be greater than 0")
    if math.isfinite(bias.vbe_v) and math.isfinite(bias.vcc_v) and bias.vbe_v >= bias.vcc_v:
        errors.append("VBE must be less than VCC")
    return errors


def solve_base_loop(bias: BiasInput) -> BiasResult:
    vbb = bias.vcc_v * bias.r2_ohm / (bias.r1_ohm + bias.r2_ohm)
    rb = bias.r1_ohm * bias.r2_ohm / (bias.r1_ohm + bias.r2_ohm)
    ib = (vbb - bias.vbe_v) / (rb + (bias.beta + 1) * bias.re_ohm)
    ic = bias.beta * ib
    ie = (bias.beta + 1) * ib
    ve = ie * bias.re_ohm
    vc = bias.vcc_v - ic * bias.rc_ohm
    vb = ve + bias.vbe_v
    vce = vc - ve

    if ib <= 0:
        region = "cutoff"
    elif vce < 0.2:
        region = "saturation"
    else:
        region = "active"

    return BiasResult(
        vbb_v=vbb,
        rb_ohm=rb,
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        ve_v=ve,
        vc_v=vc,
        vb_v=vb,
        vce_v=vce,
        region=region,
        in_active=(region == "active"),
    )
