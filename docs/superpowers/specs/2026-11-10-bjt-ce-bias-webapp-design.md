# BJT Common-Emitter DC Bias Web App — Design

**Course:** ENG29 2121 · **Date:** 2026-11-10

## Intent and why

Students need to check a voltage-divider-biased NPN common-emitter stage by
hand and see immediately whether the result is a usable amplifier bias point.
The app takes the seven bias values, computes the DC operating point, validates
the inputs, warns when the point leaves the active region, and shows a second,
independently derived solution so a wrong formula or arithmetic slip is
visible.

Success: a student enters values, gets the operating point with units, sees a
clear region verdict, and can compare the two calculations side by side. The
app runs on localhost and is committed to GitHub the same day.

## Goals

- One page, server-rendered, seven numeric inputs, one Calculate action.
- DC operating point: VBB, RB, IB, IC, IE, VB, VC, VE, VCE, with units.
- Per-field validation with clear messages and retained input.
- Region verdict: active / cutoff / saturation, with a plain-language warning.
- Independent check: full nodal KCL solution shown beside the base-loop result,
  with a pass/fail agreement indicator.
- Tests for engineering logic, independent solver, and routes.

## Non-goals

- AC analysis, gain, input/output impedance, frequency response.
- Transient or temperature analysis.
- Schematic editor, netlist import, PNP or FET support.
- Database, user accounts, result persistence, REST API, JavaScript.
- Deployment beyond localhost.

## Anti-goals

- Reporting a number without saying it is outside the active region.
- Silently clamping or hiding results.
- Duplicating the same formula in two places and calling it a cross-check.

## Constraints

- Python 3.12+ (verified on 3.15.2), Flask as the only new runtime dependency.
- Existing lab-1 files (`electrical.py`, `test_electrical.py`, `README.md`)
  stay functional and are not restructured.
- Tests use stdlib `unittest`; no pytest dependency.
- Work directly on `main` in this repo (single small app, same-day deadline);
  no worktree.
- Git 2.56 is on PATH on the current machine.
- Remote: `https://github.com/Guwauuuuu/eng29-2121-git-lab01.git`.

## Current state (2026-11-10)

Scaffolding, both solvers, routes, templates, CSS, and the test suite already
exist on `main` and are pushed to `origin/main` (latest `f73c4e2`). This
design is approved as the baseline: finish and harden that implementation
rather than rebuild it. Remaining work is the independence fix, the Flask
install, a full-suite run, the localhost demo, and a final commit.

## Approaches considered

1. **Plain Flask + Jinja form POST + `unittest` (chosen).** One route pair,
   server-rendered results, no JavaScript, no extra dependency. Smallest thing
   that meets the deliverable and is easy for a student to read.
2. **Flask JSON API + JavaScript front end.** Cleaner separation on paper, but
   adds a second language, fetch/error handling, and DOM rendering for no lab
   benefit.
3. **Flask-WTF / WTForms validation.** Less hand-written parsing, but a second
   dependency, more framework magic, and the validation rules are simple enough
   to state directly.

Approach 1 is chosen because the lab values readability and a same-day demo
over architectural ceremony.

## Engineering model

NPN, voltage-divider bias, active-region model. Inputs:

| Symbol | Meaning | Unit | Valid range |
|---|---|---|---|
| VCC | supply | V | > 0 |
| R1 | base to VCC | Ω | > 0 |
| R2 | base to ground | Ω | > 0 |
| RC | collector to VCC | Ω | > 0 |
| RE | emitter to ground | Ω | > 0 |
| beta | hFE | — | >= 1 |
| VBE | base-emitter drop | V | > 0 and < VCC |

### Base-loop (Thevenin) solution

```
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

### Region verdict (option A)

- `cutoff`: `IB <= 0` (equivalently `VBB <= VBE`).
- `saturation`: `VCE < 0.2 V`.
- `active`: otherwise.

The reported numbers are always the active-region solution. Outside the active
region the UI states that the numbers are not physical and must not be used as
a bias point. No clamping, no hidden values.

### Independent check

A second module solves the same circuit by nodal analysis with unknowns
`[VB, VC, VE, IB, IC, IE]` and Gaussian elimination with partial pivoting:

```
(1/R1 + 1/R2) VB + IB                    = VCC/R1
(1/RC) VC + IC                           = VCC/RC
(1/RE) VE - IE                           = 0
VB - VE                                  = VBE
IC - beta*IB                             = 0
IE - (beta + 1)*IB                       = 0
```

Agreement when `max(|a-b| / max(1, |a|)) < 1e-9` across the seven solved
quantities only: IB, IC, IE, VB, VC, VE, VCE. `VBB` and `RB` are excluded
because both modules would derive them from the same Thevenin formula, so
comparing them would fake agreement. `independent.py` keeps no copy of the
Thevenin formula and no region verdict; `bjt.py` is the single source for
both. The two modules share only the `BiasInput` dataclass.

## Application structure

```
app.py                      Flask routes, form parsing, template rendering
bjt.py                      BiasInput dataclass, validate(), solve_base_loop(), region verdict
independent.py              solve_nodal() (six nodal unknowns), compare()
templates/index.html        form + results + cross-check panel
static/style.css            page styling
tests/__init__.py
tests/test_bjt.py           engineering values, regions, validation
tests/test_independent.py   nodal solver and agreement
tests/test_app.py           GET/POST routes, errors, units in output
requirements.txt            Flask>=3.0,<4
README.md                   appended run/test section (existing content kept)
```

### Routes

- `GET /` — render the empty form, no results.
- `POST /calculate` — parse and validate; on error re-render with 400, error
  messages, and the values the user typed; on success render with results.

No app factory, no blueprints, no API.

### Defaults

All form fields start empty (`GET /` renders an empty form). The example circuit
drawing keeps reference values (`VCC=12`, `R1=100k`, `R2=22k`, `RC=2.2k`,
`RE=1.0k`, `beta=100`, `VBE=0.70`) for illustration only; it is decorative and
does not prefill the inputs. Resistor fields carry a unit selector (`Ω` default,
`kΩ`); a `kΩ` selection is multiplied by 1000 before solving, and a missing or
unknown unit falls back to `Ω`.

### Display

- Voltages: `{:.3f} V`; base current: `{:.1f} µA`; collector/emitter current:
  `{:.2f} mA`.
- Results table rows: `VB`, `VE`, `VC`, `VCE`, `IB`, `IC`, `IE`, followed by the
  Thevenin equivalent (`VBB`, `RB`).
- Region status panel: a green "Active region approximation OK" badge, or a red
  "Cutoff region" / "Saturation region" warning ending in "not a usable bias
  point".
- Cross-check panel: "Independent check (nodal)" showing the `VCE` agreement, a
  pass/fail badge ("Matches" / "Differs"), and the max relative difference.

### Layout and theme

English UI copy. Yellow theme. Fixed header (chip icon, app title, course badge),
a three-column body (Input Parameters | Circuit | DC Bias Results), and a
"Week 2 Goal" footer bar. Collapses to a single column below 1000 px.

### Error messages

- Missing or non-numeric: `<field> must be a number`.
- Non-positive VCC/R1/R2/RC/RE: `<field> must be greater than 0`.
- `beta < 1`: `beta must be at least 1`.
- `VBE <= 0` or `VBE >= VCC`: `VBE must be between 0 and VCC`.

All fields are validated; every error is shown at once.

## Testing

`python -m unittest discover -s tests -t . -v` from the repo root.

- Known active point (`47k`, `10k`, `2.2k`, `470`, `beta=150`, `VBE=0.7`)
  matches hand-calculated values to 1e-9.
- Cutoff case (`R2` small) yields region `cutoff` and a warning, no exception.
- Saturation case (`RC` large) yields region `saturation` and a warning.
- Validation rejects each invalid class and names the field.
- Nodal solver agrees with the base-loop solver on active, cutoff, and
  saturation cases, and compares only solved quantities (no VBB/RB).
- Structural guard: `NodalResult` exposes no `vbb_v`, `rb_ohm`, or `region`
  attribute, so the shared-formula duplicate cannot creep back in.
- Routes: `GET /` 200 with an empty form; valid POST 200 with operating point,
  units, and agreement badge; `kΩ` units converted before solving; invalid POST
  400 with message and retained value.

## What is left to the builder

- Commit message wording beyond the plan's given messages.
- Exact SVG geometry of the decorative example circuit in the Circuit panel.

## Approval

Approved by the human partner on 2026-11-10 as the baseline (existing
implementation kept). Implementation plan and execution method chosen after
that; see `docs/superpowers/plans/2026-11-10-bjt-ce-bias-completion.md`.
