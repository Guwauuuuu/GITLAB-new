# BJT CE Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A smallest-working Flask web app for ENG29 2121 that computes the BJT common-emitter DC operating point from seven bias inputs (VCC, R1, R2, RC, RE, beta, VBE), validates input, warns when outside the active region, cross-checks against an independent nodal solution, and runs on localhost.

**Architecture:** Plain server-rendered Flask app: one `GET /` route serving a Jinja form, one `POST /calculate` route parsing and validating inputs and rendering results. Separate modules for the base-loop engineering solve, the independent nodal solve with Gaussian elimination, routes, templates, CSS, and unittest tests. No JavaScript, no WTForms, no API.

**Tech Stack:** Python 3.12, Flask 3.x (only new dependency), Jinja2, stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-webapp-design.md`

## Global Constraints

- Python 3.12; Flask is the only new runtime dependency (`requirements.txt` pins `Flask>=3.0,<4`).
- Existing lab-1 files (`electrical.py`, `test_electrical.py`, `README.md`) stay functional and are not restructured.
- Tests use stdlib `unittest`; no pytest dependency.
- Work directly on `main`; no worktree (single small app, same-day deadline).
- Git at `C:\Users\b6828295\AppData\Local\Programs\Git\cmd\git.exe`.
- Remote: `https://github.com/Guwauuuuu/eng29-2121-git-lab01.git`.

## Review Focus

1. Zero or negative VCC/R1/R2/RC/RE → validation error naming the field, HTTP 400, form re-rendered with typed values. (Task 4)
2. `beta < 1` → validation error naming `beta`. (Task 4)
3. `VBE <= 0` or `VBE >= VCC` → validation error naming `VBE`. (Task 4)
4. Cutoff (`VBB <= VBE`) → region `cutoff`, warning shown, no exception, active-region numbers still reported with a "not physical" note. (Task 2, Task 7)
5. Saturation (`VCE < 0.2 V`) → region `saturation`, warning shown, no exception. (Task 2, Task 7)

## File Structure

| File | Responsibility |
|---|---|
| `bjt.py` | `BiasInput` dataclass, `validate()`, `solve_base_loop()`, region verdict |
| `independent.py` | `solve_nodal()` via Gaussian elimination with partial pivoting, `compare()` |
| `app.py` | Flask app, `GET /` form, `POST /calculate` parse/validate/render |
| `templates/index.html` | Form + results table with units + region warning + cross-check panel |
| `static/style.css` | Page styling |
| `tests/__init__.py` | Package marker |
| `tests/test_bjt.py` | Engineering values, regions, validation errors |
| `tests/test_independent.py` | Nodal solver agreement with base-loop |
| `tests/test_app.py` | Route GET/POST behavior, errors, units in output |
| `requirements.txt` | `Flask>=3.0,<4` |
| `README.md` | Append run/test section only (existing content kept) |

## Tasks

### Task 1: Scaffolding — requirements, venv note, app skeleton with GET /

**Files:**
- Create: `requirements.txt`
- Create: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: nothing yet
- Produces: `app = Flask(__name__)` with `GET /` returning a 200 form page

- [ ] **Step 1: Write the failing test**

```python
import unittest
from app import app


class TestAppRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_form_returns_200_and_has_inputs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        for name in ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v"):
            self.assertIn(name, html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL — `ImportError: cannot import name 'app'`

- [ ] **Step 3: Implement `app.py`**

Create `app.py` with:

```python
from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")
```

Add `Flask>=3.0,<4` to `requirements.txt`. Create an empty `templates/index.html` stub so the route imports cleanly.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app.py templates/index.html tests/test_app.py
git commit -m "feat: add Flask app skeleton with GET / route"
```

### Task 2: Engineering solve module bjt.py

**Files:**
- Create: `bjt.py`
- Test: `tests/test_bjt.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `@dataclass class BiasInput(vcc_v: float, r1_ohm: float, rc_ohm: float, re_ohm: float, beta: float, vbe_v: float, r2_ohm: float)`
  - `validate(bias: BiasInput) -> list[str]`
  - `@dataclass class BiasResult(vbb_v, rb_ohm, ib_a, ic_a, ie_a, ve_v, vc_v, vb_v, vce_v: float; region: str; in_active: bool)`
  - `solve_base_loop(bias: BiasInput) -> BiasResult`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from bjt import BiasInput, validate, solve_base_loop


class TestBJT(unittest.TestCase):
    def defaults(self):
        return BiasInput(vcc_v=12, r1_ohm=47000, r2_ohm=10000,
                         rc_ohm=2200, re_ohm=470, beta=150, vbe_v=0.7)

    def test_known_active_point(self):
        result = solve_base_loop(self.defaults())
        self.assertAlmostEqual(result.vbb_v, 2.105263, places=6)
        self.assertAlmostEqual(result.rb_ohm, 8245.614, places=3)
        self.assertAlmostEqual(result.ib_a, 1.7740e-5, places=10)
        self.assertAlmostEqual(result.ic_a, 2.6610e-3, places=7)
        self.assertAlmostEqual(result.ie_a, 2.6787e-3, places=7)
        self.assertAlmostEqual(result.ve_v, 1.2590, places=4)
        self.assertAlmostEqual(result.vc_v, 6.1458, places=4)
        self.assertAlmostEqual(result.vb_v, 1.9590, places=4)
        self.assertAlmostEqual(result.vce_v, 4.8868, places=4)
        self.assertEqual(result.region, "active")
        self.assertTrue(result.in_active)

    def test_cutoff_region(self):
        bias = self.defaults()
        bias.r2_ohm = 100  # VBB well below VBE
        result = solve_base_loop(bias)
        self.assertEqual(result.region, "cutoff")
        self.assertFalse(result.in_active)

    def test_saturation_region(self):
        bias = self.defaults()
        bias.rc_ohm = 100000  # large collector resistor
        result = solve_base_loop(bias)
        self.assertEqual(result.region, "saturation")
        self.assertFalse(result.in_active)

    def test_validation_rejects_non_positive(self):
        bias = self.defaults()
        bias.vcc_v = 0
        self.assertIn("VCC", validate(bias)[0])

    def test_validation_rejects_beta_below_one(self):
        bias = self.defaults()
        bias.beta = 0
        self.assertIn("beta", validate(bias)[0])

    def test_validation_rejects_vbe_out_of_range(self):
        bias = self.defaults()
        bias.vbe_v = 13  # above VCC
        self.assertIn("VBE", validate(bias)[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_bjt -v`
Expected: FAIL — `ImportError: cannot import name 'BiasInput'`

- [ ] **Step 3: Implement `bjt.py`**

Implement `BiasInput` (dataclass, field order: `vcc_v, r1_ohm, r2_ohm, rc_ohm, re_ohm, beta, vbe_v`), `validate(bias)` returning a list of error strings naming each invalid field (`VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE`), `solve_base_loop(bias)` using the Thevenin base-loop equations from the spec, and `BiasResult` with region verdict: `cutoff` if `IB <= 0`, `saturation` if `VCE < 0.2`, else `active`; `in_active` accordingly.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_bjt -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bjt.py tests/test_bjt.py
git commit -m "feat: add base-loop BJT DC bias solver with region verdict"
```

### Task 3: Independent check module independent.py

**Files:**
- Create: `independent.py`
- Test: `tests/test_independent.py`

**Interfaces:**
- Consumes: `BiasInput` from `bjt.py` (import only, no shared formula code)
- Produces:
  - `@dataclass class NodalResult(vbb_v, rb_ohm, ib_a, ic_a, ie_a, ve_v, vc_v, vb_v, vce_v: float; region: str; in_active: bool)`
  - `solve_nodal(bias: BiasInput) -> NodalResult` — 6 unknowns `[VB, VC, VE, IB, IC, IE]`, Gaussian elimination with partial pivoting
  - `compare(base: BiasResult, nodal: NodalResult) -> dict[str, float | bool]` — `max_rel_diff`, `agree` (tol 1e-9)

- [ ] **Step 1: Write the failing test**

```python
import unittest
from bjt import BiasInput, solve_base_loop
from independent import solve_nodal, compare


class TestIndependent(unittest.TestCase):
    def defaults(self):
        return BiasInput(vcc_v=12, r1_ohm=47000, r2_ohm=10000,
                         rc_ohm=2200, re_ohm=470, beta=150, vbe_v=0.7)

    def test_nodal_agrees_with_base_loop_active(self):
        bias = self.defaults()
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertTrue(report["agree"])
        self.assertLess(report["max_rel_diff"], 1e-9)

    def test_nodal_agrees_with_base_loop_cutoff(self):
        bias = self.defaults()
        bias.r2_ohm = 100
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertTrue(report["agree"])
        self.assertEqual(nodal.region, "cutoff")

    def test_nodal_agrees_with_base_loop_saturation(self):
        bias = self.defaults()
        bias.rc_ohm = 100000
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertTrue(report["agree"])
        self.assertEqual(nodal.region, "saturation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_independent -v`
Expected: FAIL — `ImportError: cannot import name 'solve_nodal'`

- [ ] **Step 3: Implement `independent.py`**

Implement `solve_nodal(bias)` building the 6x6 nodal system (unknowns VB, VC, VE, IB, IC, IE) from the spec's KCL equations and solving by Gaussian elimination with partial pivoting, returning `NodalResult` with the same region rules. Implement `compare(base, nodal)` computing max relative difference `max(|a-b| / max(1, |a|))` across the eight quantities and `agree = max_rel_diff < 1e-9`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_independent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add independent.py tests/test_independent.py
git commit -m "feat: add independent nodal solver and cross-check comparison"
```

### Task 4: POST /calculate route with validation and results rendering

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `BiasInput`, `validate`, `solve_base_loop`, `solve_nodal`, `compare`
- Produces: `POST /calculate` handling form submission

- [ ] **Step 1: Write the failing test**

```python
    def test_valid_post_returns_results_with_units(self):
        data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="10000",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("4.887 V", html)
        self.assertIn("mA", html)
        self.assertIn("active", html.lower())

    def test_invalid_post_returns_400_and_retains_values(self):
        data = dict(vcc_v="abc", r1_ohm="0", r2_ohm="10000",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        html = response.data.decode("utf-8")
        self.assertIn("VCC", html)
        self.assertIn('value="0"', html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL — 404 or 500 on `/calculate`

- [ ] **Step 3: Implement `POST /calculate` in `app.py`**

Add route:

```python
@app.post("/calculate")
def calculate():
    raw = {name: request.form.get(name, "") for name in
           ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v")}
    try:
        bias = BiasInput(**{k: float(v) for k, v in raw.items()})
    except (ValueError, TypeError):
        bias = None
    errors = validate(bias) if bias else [f"{name} must be a number" ...]
    if errors:
        return render_template("index.html", errors=errors, raw=raw), 400
    base = solve_base_loop(bias)
    nodal = solve_nodal(bias)
    report = compare(base, nodal)
    return render_template("index.html", base=base, nodal=nodal, report=report, raw=raw)
```

Handle missing/non-numeric per field with field-specific messages; keep `raw` for re-rendering typed values.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: add POST /calculate with validation and cross-check results"
```

### Task 5: Templates and CSS — form, results, warnings, cross-check panel

**Files:**
- Create: `templates/index.html`
- Create: `static/style.css`
- Modify: `app.py` (defaults passed to template)

**Interfaces:**
- Consumes: `base`, `nodal`, `report`, `errors`, `raw` from `app.py`
- Produces: rendered page with form (default values), results table with units, region badge + warning sentence, cross-check panel with both values, max difference, pass/fail badge

- [ ] **Step 1: Write the failing test**

Extend `tests/test_app.py`:

```python
    def test_results_show_region_warning_outside_active(self):
        data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="100",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        html = response.data.decode("utf-8")
        self.assertIn("cutoff", html.lower())
        self.assertIn("warning", html.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL — warning text not present

- [ ] **Step 3: Implement `templates/index.html` and `static/style.css`**

Write `index.html` with:
- Form with seven numeric inputs prefilled from `raw` or defaults (VCC=12, R1=47000, R2=10000, RC=2200, RE=470, beta=150, VBE=0.7)
- Error list above the form when `errors`
- Results table showing VBB, RB, IB, IC, IE, VE, VC, VB, VCE with units (3-decimal V, 4-decimal mA)
- Region badge (`active` / `cutoff` / `saturation`) and one warning sentence when not active
- Cross-check panel: base-loop value, nodal value, max relative difference, pass/fail badge

Write `static/style.css` for a clean single-column lab page. Link it from the template.

Pass `defaults` into the `GET /` render so inputs are prefilled.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_app -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css app.py tests/test_app.py
git commit -m "feat: add results template, CSS, defaults, and region warnings"
```

### Task 6: End-to-end localhost demo, full test suite, README, final commit

**Files:**
- Modify: `README.md` (append run/test section)

**Interfaces:**
- Consumes: all prior tasks
- Produces: running `python app.py` on localhost:5000, full `python -m unittest discover -s tests -t . -v` green, README instructions

- [ ] **Step 1: Install dependency and run full suite**

Run: `python -m pip install -r requirements.txt`
Run: `python -m unittest discover -s tests -t . -v`
Expected: all tests PASS

- [ ] **Step 2: Start app and verify localhost demo**

Run: `python app.py` (background), then `curl http://127.0.0.1:5000/` and `curl -X POST -d ... http://127.0.0.1:5000/calculate`
Expected: 200 HTML with form and results

- [ ] **Step 3: Append run/test section to `README.md`**

Add section:

```markdown
## Run

```
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000/

## Test

```
python -m unittest discover -s tests -t . -v
```
```

- [ ] **Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: add run and test instructions"
git push origin main
```

## Self-Review (done)

1. **Spec coverage:** Seven inputs ✓ (Task 1 form, Task 4 parse), operating point with units ✓ (Task 5 table), validation ✓ (Task 2/4), region warnings ✓ (Task 2/5), independent comparison ✓ (Task 3/5), tests ✓ (Tasks 2–4), localhost demo ✓ (Task 6), GitHub commit ✓ (Task 6). No AC/transient/editor/FET — excluded by design.
2. **Step scan:** Every step writes exactly one thing; no TBD lines.
3. **Type consistency:** `BiasInput`, `BiasResult`, `NodalResult`, `compare` used identically in Tasks 2–5.
4. **Review Focus:** all five items pinned to tasks with tests.
5. **Proportion:** plan ~1.5x the spec; code blocks limited to skeletons and the nodal algorithm approach.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-10-bjt-ce-bias-webapp.md`.

Please review the plan. Which execution approach would you prefer?

- **Subagent-driven** — A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** — I implement every task myself in this session, then one fresh reviewer checks the whole branch. Cheapest and fastest; no independent review until the end.

**For this plan I recommend Native**, because the six tasks are tightly coupled through shared interfaces (`BiasInput` → `solve_base_loop` → `solve_nodal` → routes → template), there are only six of them, and a same-day localhost demo favors speed over independent per-task review.

**Does the plan capture what you want, and which approach should we use?** (You already said proceed — I'll start with Native on your confirmation, or switch to subagent-driven if you prefer.)
