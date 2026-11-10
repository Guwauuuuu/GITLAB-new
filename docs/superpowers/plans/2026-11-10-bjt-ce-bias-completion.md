# BJT CE Bias Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish and harden the existing Flask BJT common-emitter DC bias app so it runs on localhost with a genuinely independent cross-check and is pushed to GitHub.

**Architecture:** Keep the current one-page server-rendered app. `bjt.py` owns the Thevenin base-loop solution, validation, and the region verdict. `independent.py` solves the same circuit from six nodal equations and compares only solved quantities. `app.py` renders one form and one result view.

**Tech Stack:** Python 3.15, Flask 3.x, Jinja templates, plain CSS, stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-webapp-design.md`

## Global Constraints

- Python 3.12+ (verified on 3.15.2); Flask>=3.0,<4 is the only runtime dependency.
- Keep `electrical.py`, `test_electrical.py`, and existing `README.md` content functional.
- Tests use stdlib `unittest`; no pytest.
- Work directly on `main`; no worktree.
- Thai UI copy, English symbols and units.
- Voltages `%.3f V`, currents `%.4f mA`.
- Validation messages: `<FIELD> must be a number`, `<FIELD> must be greater than 0`, `beta must be at least 1`, `VBE must be between 0 and VCC`.
- Region thresholds: cutoff `IB <= 0`, saturation `VCE < 0.2 V`, else active.

## Review Focus

- Non-finite input (`nan`, `inf` from the form) — must return 400, never render `nan V` as an active point. Test in Task 1 and Task 3.
- Cutoff (`VBB <= VBE`, negative IB) — page must show the cutoff badge and the "not a usable bias point" warning. Test in Task 3.
- Saturation (`VCE < 0.2 V`, very large RC) — page must show the saturation badge and the same warning. Test in Task 3.
- Extreme but finite resistance ratios (R1/R2 ~ 1e9, beta 1e5) — solvers must not raise or return NaN. Test in Task 2.
- Shared formula sneaking back into the "independent" module — `NodalResult` must expose no `vbb_v`, `rb_ohm`, or `region`. Test in Task 2.

---

### Task 1: Reject non-finite inputs

**Files:**
- Modify: `bjt.py` (`validate`)
- Test: `tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInput` dataclass from `bjt.py`.
- Produces: `validate(bias: BiasInput) -> list[str]` returns `<FIELD> must be a finite number` for any NaN/inf field.

- [ ] **Step 1: Write the failing tests**

```python
class TestValidationFinite(unittest.TestCase):
    def defaults(self):
        return BiasInput(vcc_v=12, r1_ohm=47000, r2_ohm=10000,
                         rc_ohm=2200, re_ohm=470, beta=150, vbe_v=0.7)

    def test_nan_vcc_is_rejected(self):
        bias = self.defaults(); bias.vcc_v = float("nan")
        self.assertIn("VCC must be a finite number", validate(bias))

    def test_inf_r1_is_rejected(self):
        bias = self.defaults(); bias.r1_ohm = float("inf")
        self.assertIn("R1 must be a finite number", validate(bias))

    def test_nan_beta_is_rejected(self):
        bias = self.defaults(); bias.beta = float("nan")
        self.assertIn("beta must be a finite number", validate(bias))

    def test_nan_vbe_is_rejected(self):
        bias = self.defaults(); bias.vbe_v = float("nan")
        self.assertIn("VBE must be a finite number", validate(bias))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_bjt -v`
Expected: the four new tests FAIL (`assertIn` finds no finite-number message); existing ones pass.

- [ ] **Step 3: Implement finite checks in `bjt.py`**

Add `import math`, then check `math.isfinite(value)` before the range checks for VCC, R1, R2, RC, RE, beta, and VBE. Emit `<FIELD> must be a finite number` and skip the range check for that field when it is not finite. Field labels are `VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_bjt -v`
Expected: 10 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add bjt.py tests/test_bjt.py
git commit -m "fix: reject non-finite bias inputs"
```

### Task 2: Make the independent check genuinely independent

**Files:**
- Modify: `independent.py` (`NodalResult`, `solve_nodal`, `compare`)
- Test: `tests/test_independent.py`

**Interfaces:**
- Consumes: `BiasInput`, `BiasResult` from `bjt.py`.
- Produces: `NodalResult` with exactly `ib_a, ic_a, ie_a, ve_v, vc_v, vb_v, vce_v`; `compare(base: BiasResult, nodal: NodalResult) -> dict` with keys `max_rel_diff` (float) and `agree` (bool), comparing only those seven fields.

- [ ] **Step 1: Write the failing tests**

```python
def test_result_exposes_only_solved_quantities(self):
    nodal = solve_nodal(self.defaults())
    for attr in ("vbb_v", "rb_ohm", "region", "in_active"):
        self.assertFalse(hasattr(nodal, attr), attr)

def test_extreme_ratios_do_not_crash(self):
    bias = BiasInput(vcc_v=12, r1_ohm=1e9, r2_ohm=1, rc_ohm=1e6,
                     re_ohm=1, beta=1e5, vbe_v=0.7)
    base = solve_base_loop(bias)
    nodal = solve_nodal(bias)
    report = compare(base, nodal)
    self.assertIsInstance(report["agree"], bool)
    for value in (nodal.ib_a, nodal.ic_a, nodal.ie_a, nodal.vb_v,
                  nodal.vc_v, nodal.ve_v, nodal.vce_v):
        self.assertTrue(math.isfinite(value))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_independent -v`
Expected: `test_result_exposes_only_solved_quantities` FAILS on `vbb_v`; `test_extreme_ratios_do_not_crash` may pass.

- [ ] **Step 3: Trim `NodalResult` and `compare()`**

Delete the `vbb_v`, `rb_ohm`, `region`, and `in_active` fields from `NodalResult`; delete the Thevenin `vbb`/`rb` computation and region block from `solve_nodal()`; return only the six unknowns plus VCE. In `compare()`, compare exactly `("ib_a", "ic_a", "ie_a", "ve_v", "vc_v", "vb_v", "vce_v")`. Update the two region tests to assert on `base.region`, not `nodal.region`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_bjt tests.test_independent -v`
Expected: 15 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add independent.py tests/test_independent.py
git commit -m "fix: compare only independently solved quantities"
```

### Task 3: Install Flask, add route coverage, run the full suite

**Files:**
- Modify: `tests/test_app.py`
- Verify: `requirements.txt`, `app.py`, `templates/index.html`

**Interfaces:**
- Consumes: `app.test_client()`, `POST /calculate` form fields `vcc_v, r1_ohm, r2_ohm, rc_ohm, re_ohm, beta, vbe_v`.
- Produces: route-level proof for non-finite input and for both out-of-region warnings.

- [ ] **Step 1: Install the runtime dependency**

Run: `python -m pip install -r requirements.txt`
Expected: Flask 3.x installed.

- [ ] **Step 2: Write the failing route tests**

```python
def test_nan_input_returns_400(self):
    data = dict(vcc_v="nan", r1_ohm="47000", r2_ohm="10000",
                rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
    response = self.client.post("/calculate", data=data)
    self.assertEqual(response.status_code, 400)
    self.assertIn("finite number", response.data.decode("utf-8"))

def test_cutoff_post_warns(self):
    data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="100",
                rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
    html = self.client.post("/calculate", data=data).data.decode("utf-8")
    self.assertIn("cutoff", html)
    self.assertIn("ไม่ใช่จุด bias ที่ใช้งานได้จริง", html)

def test_saturation_post_warns(self):
    data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="10000",
                rc_ohm="100000", re_ohm="470", beta="150", vbe_v="0.7")
    html = self.client.post("/calculate", data=data).data.decode("utf-8")
    self.assertIn("saturation", html)
    self.assertIn("ไม่ใช่จุด bias ที่ใช้งานได้จริง", html)
```

- [ ] **Step 3: Run the full suite to see the new tests fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: non-finite and warning tests FAIL; existing 19 pass.

- [ ] **Step 4: Make them pass with minimal changes**

If `nan` reaches the renderer, ensure `app.py` calls `validate()` for every parsed input (it already does). If a warning test fails, the template's warning paragraph or region class must be rendered for that region; fix `templates/index.html` only, keeping the existing Thai copy.

- [ ] **Step 5: Run the full suite to verify everything passes**

Run: `python -m unittest discover -s tests -t . -v`
Expected: 22 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add tests/test_app.py templates/index.html app.py
git commit -m "test: cover non-finite input and region warnings"
```

### Task 4: Verify the localhost demonstration

**Files:**
- Verify only; no code changes expected.

- [ ] **Step 1: Start the server in the background**

Run: `python -c "from app import app; app.run(host='127.0.0.1', port=5000, debug=False)"` in the background from the repo root.

- [ ] **Step 2: Verify GET `/`**

Run: `Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing`
Expected: 200; body contains all seven input names and `ตัวอย่างวงจร`.

- [ ] **Step 3: Verify a valid POST**

Run the defaults through `Invoke-WebRequest -Method Post -Body @{vcc_v=12; r1_ohm=47000; r2_ohm=10000; rc_ohm=2200; re_ohm=470; beta=150; vbe_v=0.7}`.
Expected: 200; body contains `4.887 V`, `mA`, `active`, and `ใช่` (cross-check pass).

- [ ] **Step 4: Show it in the browser**

Open `http://127.0.0.1:5000/` in the browser tool, submit the defaults, and capture a screenshot as demo evidence. Leave the server running until the final commit is pushed.

### Task 5: Commit the docs and push

**Files:**
- Modify: `docs/superpowers/specs/2026-11-10-bjt-ce-bias-webapp-design.md`, `docs/superpowers/plans/2026-11-10-bjt-ce-bias-completion.md` (already written)

- [ ] **Step 1: Confirm the tree and the suite**

Run: `git status --short` then `python -m unittest discover -s tests -t . -v`
Expected: only doc changes pending; 22 tests OK.

- [ ] **Step 2: Commit the docs**

```bash
git add docs/superpowers
git commit -m "docs: record baseline decision and completion plan"
```

- [ ] **Step 3: Push to GitHub**

```bash
git push origin main
```

Expected: `main` up to date with `origin/main`; `git rev-list --left-right --count origin/main...main` prints `0 0`.

### Task 6: Fix the example-circuit SVG geometry

**Files:**
- Modify: `templates/index.html` (example-circuit `<svg>` only)
- Test: `tests/test_app.py` (existing `test_get_form_contains_example_circuit` must stay green)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a static schematic whose labels do not overlap and whose transistor symbol reads as an NPN, keeping the existing `<svg ... role="img" aria-label="ตัวอย่างวงจร BJT Common-Emitter">`, the `ตัวอย่างวงจร` heading, and the same component values.

**Context:** The demo screenshot showed `12 V` colliding with `RC = 2.2 kΩ`, `β = 150` clipped at the left edge, and a single huge triangle standing in for the transistor. The section is decorative and static; only its geometry changes.

- [ ] **Step 1: Replace the SVG body**

Replace everything between `<svg ...>` and `</svg>` with exactly:

```html
<line x1="150" y1="50" x2="520" y2="50" stroke="#111" stroke-width="2"/>
<line x1="150" y1="42" x2="150" y2="58" stroke="#111" stroke-width="2"/>
<text x="160" y="36" font-size="14">12 V</text>
<line x1="150" y1="50" x2="150" y2="130" stroke="#111" stroke-width="2"/>
<rect x="144" y="70" width="12" height="40" fill="white" stroke="#111" stroke-width="2"/>
<text x="136" y="95" font-size="14" text-anchor="end">R1 = 47 kΩ</text>
<line x1="150" y1="130" x2="150" y2="300" stroke="#111" stroke-width="2"/>
<rect x="144" y="190" width="12" height="40" fill="white" stroke="#111" stroke-width="2"/>
<text x="136" y="215" font-size="14" text-anchor="end">R2 = 10 kΩ</text>
<circle cx="150" cy="150" r="3" fill="#111"/>
<line x1="150" y1="150" x2="310" y2="150" stroke="#111" stroke-width="2"/>
<line x1="310" y1="150" x2="325" y2="150" stroke="#111" stroke-width="2"/>
<line x1="325" y1="118" x2="325" y2="182" stroke="#111" stroke-width="4"/>
<line x1="325" y1="132" x2="375" y2="108" stroke="#111" stroke-width="2"/>
<line x1="325" y1="168" x2="375" y2="192" stroke="#111" stroke-width="2"/>
<line x1="375" y1="108" x2="375" y2="50" stroke="#111" stroke-width="2"/>
<rect x="369" y="65" width="12" height="30" fill="white" stroke="#111" stroke-width="2"/>
<text x="391" y="84" font-size="14">RC = 2.2 kΩ</text>
<line x1="375" y1="192" x2="375" y2="300" stroke="#111" stroke-width="2"/>
<rect x="369" y="215" width="12" height="40" fill="white" stroke="#111" stroke-width="2"/>
<text x="391" y="240" font-size="14">RE = 470 Ω</text>
<line x1="150" y1="300" x2="375" y2="300" stroke="#111" stroke-width="2"/>
<line x1="250" y1="306" x2="290" y2="306" stroke="#111" stroke-width="2"/>
<line x1="258" y1="312" x2="282" y2="312" stroke="#111" stroke-width="2"/>
<line x1="266" y1="318" x2="274" y2="318" stroke="#111" stroke-width="2"/>
<text x="298" y="312" font-size="14">GND</text>
<text x="205" y="140" font-size="14">β = 150</text>
<text x="205" y="176" font-size="14">VBE = 0.7 V</text>
<text x="430" y="120" font-size="14">VCE ≈ 4.89 V</text>
```

Keep the opening `<svg>` tag as-is but change its `viewBox` to `0 0 700 360`.

- [ ] **Step 2: Run the route tests**

Run: `python -m unittest tests.test_app -v`
Expected: 7 tests, OK (the example-circuit assertions still find `svg` and `ตัวอย่างวงจร`).

- [ ] **Step 3: Commit**

```bash
git add templates/index.html
git commit -m "fix: redraw example circuit without overlapping labels"
```

## Self-Review

- Spec coverage: inputs, units, validation, region warning, independent check, routes, tests, localhost, GitHub — each mapped to Task 1–5.
- Step scan: each step is one action with a checkable result; code bodies only where the algorithm or exact test is fixed.
- Type consistency: `NodalResult` fields used by `compare()`, `app.py`, and the template match after Task 2; `report` keys unchanged.
- Review Focus: all five failure modes have an owning test (Tasks 1–3).
- Proportion: two code changes, one route-test task, one demo task, one docs/commit task.

## Execution Handoff

No execution method supplied yet; ask the human partner to review this plan
and choose subagent-driven or native execution before implementation.

## Amendment 2026-11-10 — Yellow three-column UI

The human partner supplied a mockup and asked for the same layout in a yellow
theme. This supersedes two Global Constraints above for presentation only:

- UI copy is **English**, not Thai (symbols and units unchanged).
- Voltages `%.3f V`; currents are `%.1f µA` (IB) and `%.2f mA` (IC, IE).

Additional changes:

- `GET /` renders an **empty form**; the decorative example circuit keeps
  reference values.
- Resistor fields gained `Ω`/`kΩ` selectors (`<field>_unit`); `kΩ` is multiplied
  by 1000 in `app.py` before validation and solving.
- `templates/index.html` and `static/style.css` were rewritten for the header,
  three-column body (Input Parameters | Circuit | DC Bias Results), and
  "Week 2 Goal" footer.
- The SVG circuit was redrawn. Inside SVG text, `<sub>` must not be used: the
  HTML parser treats it as a breakout tag and closes the SVG. Use
  `<tspan baseline-shift="sub">` instead.

Engineering logic (`bjt.py`, `independent.py`), validation, region verdicts,
and the independent nodal check are unchanged.
