# Fixed Bias + Emitter Bias (single supply) — Implementation Plan

**Date:** 2026-11-17  
**Status:** Implemented 2026-11-17 — awaiting Browser verification against the user's worksheet table  
**Baseline:** 28 existing `unittest` tests pass (`python -m unittest discover -s tests -t . -v`)

## Goal

Add two single-supply NPN common-emitter bias modes to the Flask app:

- **Fixed Bias** (base resistor to VCC, emitter grounded)
- **Emitter Bias** (base resistor to VCC, emitter resistor to ground)

The existing **Voltage Divider Bias** calculation, its output values, and its
independent nodal check must stay exactly as they are.

## Invariants

- `bjt.py` and `independent.py` are not modified.
- `solve_base_loop()`, `solve_nodal()`, `compare()`, `BiasInput`, and
  `validate()` keep their current interfaces and results.
- Existing tests stay untouched. No new `unittest` files or test cases.
- Verification of the new modes is manual in the Browser against the
  worksheet table supplied by the user.
- No JavaScript, no new dependency, no AC analysis, no PNP/dual-supply support.

## Mode selection

Add one form field:

```text
mode = divider | fixed | emitter
```

- Missing/empty `mode` → `divider` (preserves old POSTs and tests).
- Unknown mode → HTTP 400 with `mode must be divider, fixed, or emitter`.
- `app.py` uses a mapping to choose both the validation function and the
  solver, so only the fields needed by that mode are parsed and validated.

| mode | Required fields (besides `mode`) | Solver |
|---|---|---|
| `divider` | `vcc_v`, `r1_ohm`, `r2_ohm`, `rc_ohm`, `re_ohm`, `beta`, `vbe_v` | existing `solve_base_loop()` |
| `fixed` | `vcc_v`, `rb_ohm`, `rc_ohm`, `beta`, `vbe_v` | new `solve_fixed_bias()` |
| `emitter` | `vcc_v`, `rb_ohm`, `rc_ohm`, `re_ohm`, `beta`, `vbe_v` | new `solve_emitter_bias()` |

## Equations

All equations use SI units: volts, amperes, ohms, and unitless beta. No unit
conversion happens inside the equation module.

### Divider — unchanged

Keep the existing implementation in `bjt.py`:

```text
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
IB  = (VBB - VBE) / (RB + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VE + VBE
VCE = VC - VE
```

### Fixed Bias

```text
IB  = (VCC - VBE) / RB
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = 0.0
VC  = VCC - IC * RC
VB  = VBE
VCE = VC - VE
```

### Emitter Bias

```text
IB  = (VCC - VBE) / (RB + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VE + VBE        # equivalent to VCC - IB * RB
VCE = VC - VE
```

### Region verdict for the new modes

Use the same public threshold convention as the divider:

- `cutoff` when `IB <= 0`
- `saturation` when `VCE < 0.2 V`
- `active` otherwise

The solver still reports the active-region numbers in cutoff/saturation and
the page shows the existing "not a usable bias point" warning.

## Input validation per mode

Reuse the existing message style and finite-number checks:

| Check | Message |
|---|---|
| Missing/non-numeric field | `<FIELD> must be a number` |
| Non-finite value | `<FIELD> must be a finite number` |
| VCC, RC, RB, RE, R1, R2 <= 0 | `<FIELD> must be greater than 0` |
| beta < 1 | `beta must be at least 1` |
| VBE <= 0 or VBE >= VCC | `VBE must be less than VCC` / existing message |

- `divider`: existing `validate()` is used unchanged.
- `fixed`: new `validate_fixed()` checks VCC, RB, RC, beta, VBE only.
- `emitter`: new `validate_emitter()` checks VCC, RB, RC, RE, beta, VBE only.
- Irrelevant fields are ignored, not required. This lets the same form carry
  all input widgets without breaking old divider requests.

## Units and result-dict contract

- Form units: every resistor input has an `Ω` / `kΩ` selector.
  `app.py` multiplies the value by `1000.0` when `kΩ` is selected, exactly as
  the divider does today.
- The equation module receives ohms and volts only.
- The solver returns SI values in a flat dict. Keys carry the SI unit suffix:

```python
{
    "mode": "fixed",          # or "emitter"
    "ib_a": ...,
    "ic_a": ...,
    "ie_a": ...,
    "vb_v": ...,
    "vc_v": ...,
    "ve_v": ...,
    "vce_v": ...,
    "region": "active",       # cutoff / saturation / active
    "in_active": True,
}
```

- Display units in the template match the key suffixes and the existing table:
  `VB/VE/VC/VCE` → `%.3f V`; `IB` → `%.1f µA`; `IC/IE` → `%.2f mA`.
- No A→µA/mA conversion is stored in the dict; conversion happens only at
  rendering time, as it does for the divider.

## Files to change

| File | Change |
|---|---|
| **new** `bias_modes.py` | `FixedBiasInput`, `EmitterBiasInput`, `validate_fixed()`, `validate_emitter()`, `solve_fixed_bias()`, `solve_emitter_bias()`, local region helper. Pure equations, no Flask. |
| `app.py` | Add `rb_ohm` to form/default field lists; add mode→fields/validator/solver maps; parse only the selected mode's fields; convert `kΩ`→`Ω` for RB as well as the existing resistors; dispatch to divider or new solver; keep the divider render path unchanged; finite-result guard for new dicts. |
| `templates/index.html` | Add mode `<select>`; add RB input with Ω/kΩ selector; keep all existing divider inputs; add a results block for the new dict modes (same rows/units, same region badge), leaving the divider results/cross-check block untouched. |
| `static/style.css` | Optional small style for the mode selector/field group only if the existing form styles are insufficient. |
| `README.md` | Short note on the three modes and which fields each uses (after code works). |
| `tests/` | **No changes.** Existing 28 tests must remain green. |

## Implementation order

1. Create `bias_modes.py` with the two equation sets and per-mode validation.
2. Wire `app.py`: mode parsing, mode-specific field parsing, kΩ conversion,
   dispatch, finite-result guard.
3. Add the mode selector, RB input, and new-mode results table to
   `templates/index.html`.
4. Run the existing suite; confirm the divider fixture still renders
   `2.105 V`, `4.887 V`, and `agree pass`.
5. Start the app and verify all three modes in the Browser using the user's
   worksheet table, including one invalid input per mode and one kΩ input.
6. Update README only if needed.

## Acceptance checks

- Existing 28 tests unchanged and passing.
- Divider default POST output is identical in values and formatting.
- Fixed Bias: values match the worksheet table for the given RB/RC/beta/VBE.
- Emitter Bias: values match the worksheet table for the given RB/RC/RE/beta/VBE.
- `VE = 0 V` in Fixed Bias; `VE = IE * RE` in Emitter Bias.
- `kΩ` on RB/RE is converted before solving.
- Missing or invalid fields for the selected mode return 400 with the field
  name and retain typed values.
- Unknown `mode` returns 400.
- No new `unittest` tests; verification evidence comes from the Browser table.

## Confirmation needed

The repository does not contain the Lab 2 worksheet. This plan assumes the
standard single-supply equations shown above:

- Fixed Bias: RB from VCC to base, emitter grounded.
- Emitter Bias: RB from VCC to base, RE from emitter to ground, RC at collector.

Please confirm these match the worksheet table, or send the exact equations /
table values before implementation starts.
