# Common-Emitter Amplifier Simulator v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Lab 3 Flask BJT bias web app with a Common-Emitter Amplifier Simulator v1 backed by real `ngspice_con -b` runs for `.op`, `.ac`, and `.tran` analyses.

**Architecture:** Add `spice_engine.py` for netlist generation, isolated `ngspice_con -b` subprocess execution, and output parsing; add `/ce-simulator` and `/api/ce-simulate` routes in `app.py` reusing `bjt.py` for Lab 3 analytical reference; add `templates/ce_simulator.html` and `static/ce_sim.js` with shared header navigation and dark-theme styling. Preserve `/` and `/calculate` Lab 3 behavior untouched.

**Tech Stack:** Python 3.15, Flask 3.x, `ngspice_con` (ngspice-47) via `subprocess.run(..., shell=False)`, vanilla JS + inline SVG charts, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-24-ce-amplifier-simulator-design.md`

## Global Constraints
- Preserve all 3 Lab 3 DC bias modes (`divider`, `fixed`, `emitter`) and existing tests (`tests/test_app.py`, `tests/test_bjt.py`, `tests/test_independent.py`, `test_electrical.py`).
- Reference circuit: Voltage-divider CE with unbypassed `RE` (no bypass cap), `Cin`, `Cout`, `RL`, standard NPN model `Q2N2222`.
- Baseline defaults: `VCC=12 V`, `R1=100 kΩ`, `R2=22 kΩ`, `RC=2.2 kΩ`, `RE=1 kΩ`, `RL=10 kΩ`, `Cin=10 µF`, `Cout=10 µF`, `Source=10 mV peak / 1 kHz`.
- `ngspice_con -b` executed via list args without `shell=True`, with `timeout`, in an isolated temporary directory.
- Never fabricate traces, hard-code success values, or hide ngspice errors.

## Review Focus
- `RE = 0` or negative/NaN/Inf component values rejected cleanly before ngspice runs, returning HTTP 400 and error status.
- `ngspice_con` binary missing, non-zero exit code, or timeout returns explicit error state without stale plots or fake success.
- `.ac` phase extracted from ngspice `vp(out)` (radians) is converted accurately to degrees (`~ -180°` at midband, not `-3.14°`).
- `.tran` uses user-supplied amplitude and frequency (`10 mV / 1 kHz` default, or large signal clipping) and clearly shows `180°` inversion between `Vin(t)` and `Vout(t)`.
- Existing `/` and `/calculate` routes pass all 48 `tests/test_app.py` tests and 3 `test_electrical.py` tests unchanged.

---

### Task 1: Implement `spice_engine.py` with TDD

**Files:**
- Create: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces:
  - `BASELINE_DEFAULTS: dict`
  - `CECircuitParams` dataclass (`vcc_v`, `r1_ohm`, `r2_ohm`, `rc_ohm`, `re_ohm`, `rl_ohm`, `cin_f`, `cout_f`, `amp_v`, `freq_hz`)
  - `validate_ce_params(params: CECircuitParams) -> list[str]`
  - `build_netlist(params: CECircuitParams, analysis: str, model_name: str = "Q2N2222") -> str`
  - `run_ngspice(netlist_text: str, output_filename: str, timeout_s: float = 10.0, executable: str = "ngspice_con") -> dict`
  - `simulate_ce(params: CECircuitParams, analysis: str, timeout_s: float = 10.0, executable: str = "ngspice_con") -> dict`

- [ ] **Step 1: Write failing tests in `tests/test_spice_engine.py`**
  - Test validation rejects `RE=0`, negative values, `NaN`/`Inf`.
  - Test `simulate_ce(..., "op")` with baseline defaults returns real SPICE values (`vb_v ~ 2.0 V`, `ve_v ~ 1.36 V`, `vc_v ~ 9.0 V`, `vce_v ~ 7.65 V`, `ib_a > 0`, `ic_a ~ 1.36 mA`, `region == "active"`, `model_name == "Q2N2222"`, `status == "success"`).
  - Test `simulate_ce(..., "ac")` returns monotonic log frequencies (`10 Hz`..`10 MHz`), `gain_mag`, `gain_db`, `phase_deg` with midband gain near `1.77 V/V` (`~4.9 dB`) and midband phase near `-180°` (within `[-185, -170]`).
  - Test `simulate_ce(..., "tran")` returns `time_s`, `vin_v`, `vout_v` over 4 cycles of `1 kHz` with `max(|vin_v|) ~ 10 mV`, negative correlation / `180°` phase inversion (`vin` peak corresponds to `vout` trough), and `vout` peak-to-peak > `vin` peak-to-peak.
  - Test error paths: missing executable (`executable="nonexistent_ngspice_bin"`), timeout (`timeout_s=0.0001`), and invalid netlist/non-zero exit return `status == "error"` with non-empty `error` message and no fabricated data.

- [ ] **Step 2: Run tests to verify they fail**
  - Run: `python -m unittest tests/test_spice_engine.py -v`

- [ ] **Step 3: Implement `spice_engine.py`**
  - Implement `CECircuitParams`, `validate_ce_params`, `build_netlist`, `run_ngspice`, and `simulate_ce`.
  - Use `subprocess.run([executable, "-b", "circuit.cir"], cwd=tmpdir, capture_output=True, text=True, timeout=timeout_s, shell=False)`.
  - Parse `wrdata` files (`op.txt`, `ac.txt`, `tran.txt`), verify all values finite and non-empty, convert `.ac` phase from radians to degrees (`math.degrees`), and compute `.ac` summary (`midband_gain_vv`, `midband_gain_db`) and `.tran` summary (`vin_pp_v`, `vout_pp_v`, `gain_vv`, `phase_inverted`).

- [ ] **Step 4: Run tests to verify they pass**
  - Run: `python -m unittest tests/test_spice_engine.py -v`

---

### Task 2: Add `/ce-simulator` and `/api/ce-simulate` routes in `app.py`

**Files:**
- Modify: `app.py`
- Test: `tests/test_ce_app.py`

**Interfaces:**
- Consumes: `spice_engine.CECircuitParams`, `spice_engine.validate_ce_params`, `spice_engine.simulate_ce`, `bjt.BiasInput`, `bjt.validate`, `bjt.solve_base_loop`
- Produces:
  - `GET /ce-simulator` returning HTML (`200`)
  - `POST /api/ce-simulate` accepting JSON or form-encoded payload (`analysis` in `{"op", "ac", "tran"}`, circuit values + units, optional analytical `beta` and `vbe_v`) and returning JSON with `status`, `model_name`, `analysis`, `spice`, `analytical`, `errors`.

- [ ] **Step 1: Write failing tests in `tests/test_ce_app.py`**
  - Test `GET /ce-simulator` returns 200 with baseline defaults (`12`, `100`, `22`, `2.2`, `1`, `10`, `10`, `10`, `10`, `1`) and link back to `/`.
  - Test `POST /api/ce-simulate` for `op`, `ac`, and `tran` returns 200, `status == "success"`, `model_name == "Q2N2222"`, real `spice` payload, and distinct `analytical` payload from `bjt.solve_base_loop`.
  - Test `POST /api/ce-simulate` with `re_ohm=0` returns 400 with `status == "error"` and `errors` containing `RE`.
  - Test `POST /api/ce-simulate` with invalid `analysis="noise"` returns 400.
  - Test `POST /api/ce-simulate` when `spice_engine.simulate_ce` reports an engine error returns 500 with `status == "error"` and no fake data.

- [ ] **Step 2: Run tests to verify they fail**
  - Run: `python -m unittest tests/test_ce_app.py -v`

- [ ] **Step 3: Implement routes & parsing helpers in `app.py`**
  - Add unit scaling helpers for capacitance (`uF`, `nF`, `pF`, `F`), frequency (`Hz`, `kHz`, `MHz`), voltage (`V`, `mV`), and resistance (`ohm`, `kohm`, `mohm`).
  - Keep existing `/`, `/calculate`, `FIELD_NAMES`, `ALL_FIELDS`, and `MODE_FIELDS` untouched.

- [ ] **Step 4: Run tests to verify they pass**
  - Run: `python -m unittest tests/test_ce_app.py -v`

---

### Task 3: Build UI (`templates/ce_simulator.html`, `static/ce_sim.js`, nav link in `templates/index.html`, styles in `static/style.css`)

**Files:**
- Modify: `templates/index.html` (add header nav switcher only — preserve all 8 `.field` divs and form elements)
- Modify: `static/style.css` (nav tabs, status badge, plot containers, side-by-side SPICE vs Analytical cards)
- Create: `templates/ce_simulator.html`
- Create: `static/ce_sim.js`
- Modify: `README.md` (document CE Simulator v1 + `ngspice_con` usage)

- [ ] **Step 1: Update `templates/index.html` with header navigation switcher**
  - Add `<nav class="app-nav">` in `.app-header` linking `/` (**Lab 3: DC Bias**) and `/ce-simulator` (**CE Amplifier Simulator**).
  - Verify `tests/test_app.py` still passes 100% (all 48 tests).

- [ ] **Step 2: Create `templates/ce_simulator.html` and `static/ce_sim.js`, extend `static/style.css`**
  - Input panel pre-populated with baseline defaults (`VCC=12 V`, `R1=100 kΩ`, `R2=22 kΩ`, `RC=2.2 kΩ`, `RE=1 kΩ`, `RL=10 kΩ`, `Cin=10 µF`, `Cout=10 µF`, `Vin=10 mV peak`, `f=1 kHz`, plus analytical reference `β=100`, `VBE=0.7 V`).
  - Analysis mode selector: `.op` (DC Operating Point), `.ac` (AC Frequency Response), `.tran` (Transient Simulation).
  - Reference CE schematic SVG showing `Vin`, `Cin`, `R1`, `R2`, `Q1 (Q2N2222)`, `RC`, unbypassed `RE`, `Cout`, `RL`, and `Vout` with live-updating labels.
  - Status banner showing `Idle` / `Running` / `Success` / `Error` + `Model: Q2N2222`.
  - Clear separation between **Real ngspice Output** (results table + SVG Bode magnitude/phase plots for `.ac` + SVG time-domain `Vin(t)`/`Vout(t)` plot for `.tran`) and **Lab 3 Analytical DC Reference** (`bjt.py`).
  - On submit/run: clear old results & plots immediately, show `Running`, fetch `/api/ce-simulate`, render real traces or display error banner with no stale plots.

- [ ] **Step 3: Add UI/integration assertions to `tests/test_ce_app.py` and update `README.md`**
  - Verify `/` nav link, `/ce-simulator` DOM elements, and run full test suite.

- [ ] **Step 4: Full Verification (Tests + Live Browser Check)**
  - Run `python -m unittest discover -s tests -t . -v` and `python -m unittest test_electrical.py -v`.
  - Start Flask server temporarily and verify `/`, `/ce-simulator`, and all three simulation modes (`.op`, `.ac`, `.tran`) plus invalid input (`RE=0`) in headless browser or live HTTP requests, confirming zero console errors and real ngspice plots.
