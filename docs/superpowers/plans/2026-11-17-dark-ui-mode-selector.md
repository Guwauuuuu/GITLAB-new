# Dark UI, Mode Selector, Live Circuit and MΩ Units — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Lab 02 bias app a balanced mode selector, mode-aware inputs, a live SVG circuit, `MΩ` units, and a dark theme, with every DC equation still in Python.

**Architecture:** `app.py` gains unit/display metadata (`UNIT_SCALE`, `UNIT_SYMBOLS`, `FIELD_VISIBILITY`, `circuit_labels`) and a Flask context processor. `templates/index.html` becomes mode-aware and data-slot-driven. A new `static/app.js` toggles visibility and rewrites SVG label text only. `static/style.css` is re-themed with dark tokens.

**Tech Stack:** Python 3 / Flask / Jinja2, vanilla JS, HTML/CSS/SVG, unittest, Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-11-17-dark-ui-mode-selector-design.md`

## Global Constraints

- DC bias equations, validation, and region checks stay in `bjt.py`, `bias_modes.py`, `independent.py`, and `app.py`. `static/app.js` may only format display strings and toggle visibility — never compute IB/IC/IE/VB/VE/VC/VCE.
- Unit values posted to the server are exactly `ohm`, `kohm`, `mohm`; anything else falls back to `ohm`.
- Keep `name="vcc_v" value=""` attribute order in the number inputs.
- Keep the existing route contract: `GET /`, `GET /calculate` → 302, `POST /calculate` → 200/400.
- No new runtime dependencies; no build step.
- Tests run with `python -m unittest discover -s tests -v` from the repo root.

## Review Focus

- Empty input must render `= —` in the SVG, never `undefined`, `null`, or a bare unit.
- `RB = 1` with unit `MΩ` must produce the same result as `RB = 1000000` with unit `Ω` (fixed bias: IC 1.13 mA, VCE 9.514 V).
- Switching modes must keep previously typed values so switching back restores them; hidden fields must not be submitted-empty by accident (they stay in the DOM and still post).
- Unknown or missing unit strings must fall back to `ohm` and return 200/400, never 500.
- After a 400 validation error the submitted mode, units, and the SVG labels must all reflect the user's input.

---

### Task 1: `MΩ` unit end to end

**Files:**
- Modify: `app.py` (unit whitelist and conversion)
- Modify: `templates/index.html` (MΩ options, unit select `id`s, footer copy)
- Modify: `README.md` (units line)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `UNIT_SCALE: dict[str, float] = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}` and `UNIT_SYMBOLS: dict[str, str] = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}` in `app.py`; unit select ids `r1_ohm_unit`, `r2_ohm_unit`, `rb_ohm_unit`, `rc_ohm_unit`, `re_ohm_unit`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_app.py` inside `TestAppRoutes`:

```python
    def test_mohm_units_are_converted(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("9.514 V", html)
        self.assertIn("1.13 mA", html)

    def test_mohm_option_present_on_every_resistor_unit_select(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertEqual(html.count('value="mohm"'), 5)

    def test_selected_unit_is_retained_after_post(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertIn('value="mohm" selected', html)

    def test_unknown_unit_falls_back_to_ohm(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1000000", rb_ohm_unit="gohm",
                    rc_ohm="2200", beta="100", vbe_v="0.70")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("1.13 mA", response.data.decode("utf-8"))
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest tests.test_app -v`
Expected: the two `mohm` assertions fail (500 or missing `9.514 V` / `value="mohm"`), `test_unknown_unit_falls_back_to_ohm` fails with `1.13 mA` missing.

- [ ] **Step 3: Add unit scale and conversion in `app.py`**

Add below `RESISTOR_FIELDS`:

```python
UNIT_SCALE = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}
UNIT_SYMBOLS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}
```

Replace the whitelist line with `units = {name: (unit if unit in UNIT_SCALE else "ohm") for name, unit in units.items()}` and the conversion loop body with `parsed[name] *= UNIT_SCALE[units[name]]`.

- [ ] **Step 4: Add the `MΩ` option and unit `id`s in `templates/index.html`**

For each of the five resistors, give the select `id="<field>_unit"` (e.g. `id="r1_ohm_unit"`), keep `aria-label="R1 unit"`, and add the third option:

```html
<option value="mohm" {{ 'selected' if units.r1_ohm == 'mohm' else '' }}>M&#937;</option>
```

Update the empty-state hint to `Voltages in V, resistances in &#937;, k&#937; or M&#937;.` and the `README.md` unit sentence the same way.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `python -m unittest tests.test_app -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app.py templates/index.html tests/test_app.py README.md
git commit -m "feat: add MΩ resistance units"
```

---

### Task 2: Mode selector and per-mode field visibility

**Files:**
- Modify: `app.py` (derived visibility map + context processor)
- Modify: `templates/index.html` (fieldset radios, wrappers `data-field` / `data-modes`)
- Modify: `static/style.css` (segmented control styles; full dark theme comes in Task 4)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `MODE_FIELDS` from Task 0 (existing).
- Produces: `FIELD_VISIBILITY: dict[str, tuple[str, ...]]` and Jinja context key `field_visibility`; field wrappers carry `data-field="<name>"` and `data-modes="<mode> <mode>"`; radios `mode_divider`, `mode_fixed`, `mode_emitter`.

- [ ] **Step 1: Write the failing tests**

```python
    def test_bias_mode_is_three_radios(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertEqual(html.count('name="mode"'), 3)
        for value in ("divider", "fixed", "emitter"):
            self.assertIn(f'id="mode_{value}"', html)
            self.assertIn(f'value="{value}"', html)

    def test_divider_mode_hides_rb_field(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertRegex(html, r'data-field="rb_ohm"[^>]*hidden')

    def test_fixed_mode_hides_divider_and_re_fields(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertRegex(html, r'data-field="r1_ohm"[^>]*hidden')
        self.assertRegex(html, r'data-field="r2_ohm"[^>]*hidden')
        self.assertRegex(html, r'data-field="re_ohm"[^>]*hidden')
        self.assertNotRegex(html, r'data-field="rb_ohm"[^>]*hidden')

    def test_every_label_for_matches_an_element_id(self):
        html = self.client.get("/").data.decode("utf-8")
        for_ids = set(re.findall(r'<label for="([^"]+)"', html))
        ids = set(re.findall(r'id="([^"]+)"', html))
        self.assertTrue(for_ids)
        self.assertLessEqual(for_ids, ids)
```

`import re` goes at the top of `tests/test_app.py`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest tests.test_app -v`
Expected: `test_bias_mode_is_three_radios` fails (`name="mode"` count is 1), the two `hidden` tests fail, the label test fails on the mode `<select>`.

- [ ] **Step 3: Derive visibility in `app.py` and expose it to templates**

```python
FIELD_VISIBILITY = {
    name: tuple(mode for mode, fields in MODE_FIELDS.items() if name in fields)
    for name in ALL_FIELDS
}


@app.context_processor
def inject_form_metadata():
    return {"field_visibility": FIELD_VISIBILITY}
```

- [ ] **Step 4: Replace the mode `<select>` with a radio group and tag every field wrapper**

Mode block (inside the form, replacing the existing `.field` + `<select id="mode">`):

```html
<fieldset class="mode-field">
  <legend>Bias Mode <span>(Circuit Configuration)</span></legend>
  <div class="mode-group" role="radiogroup" aria-label="Bias Mode (Circuit Configuration)">
    <input type="radio" id="mode_divider" name="mode" value="divider" {{ 'checked' if mode == 'divider' else '' }}>
    <label for="mode_divider">Voltage Divider Bias</label>
    <input type="radio" id="mode_fixed" name="mode" value="fixed" {{ 'checked' if mode == 'fixed' else '' }}>
    <label for="mode_fixed">Fixed Bias</label>
    <input type="radio" id="mode_emitter" name="mode" value="emitter" {{ 'checked' if mode == 'emitter' else '' }}>
    <label for="mode_emitter">Emitter Bias</label>
  </div>
  <p class="circuit-note">Divider uses R1/R2. Fixed and Emitter use RB. RE is used by Divider and Emitter.</p>
</fieldset>
```

Every input wrapper becomes:

```html
<div class="field" data-field="rb_ohm" data-modes="{{ field_visibility.rb_ohm|join(' ') }}" {{ 'hidden' if mode not in field_visibility.rb_ohm else '' }}>
```

applied to `vcc_v`, `r1_ohm`, `r2_ohm`, `rb_ohm`, `rc_ohm`, `re_ohm`, `beta`, `vbe_v` with their own names.

- [ ] **Step 5: Style the segmented control in `static/style.css`**

`.mode-field` borderless; `.mode-group` a three-column grid; radios visually hidden but present (`position:absolute; opacity:0; width:1px; height:1px`); `.mode-group label` equal-height bordered buttons; `input:checked + label` uses the accent fill; `input:focus-visible + label` gets an outline. Keep `.field[hidden] { display: none; }` implicit via the HTML attribute.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python -m unittest tests.test_app -v`
Expected: all tests PASS, including the pre-existing `test_get_form_has_empty_defaults`.

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html static/style.css tests/test_app.py
git commit -m "feat: mode-aware bias input selector"
```

---

### Task 3: Live circuit labels from the real inputs

**Files:**
- Create: `static/app.js`
- Modify: `app.py` (`circuit_labels`)
- Modify: `templates/index.html` (data-driven SVG, `{% set labels = circuit_labels(raw, units) %}`, script tag)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `UNIT_SYMBOLS` from Task 1, `mode` and `raw`/`units` context already passed to the template.
- Produces: `circuit_labels(raw: dict[str, str], units: dict[str, str]) -> dict[str, str]` returning keys `vcc, r1, r2, rb, rc, re, beta, vbe`; SVG `data-slot="<key>"` value spans and `data-component="r1|r2|rb|re"` groups; JS globals `applyMode(mode)` and `updateCircuit()`.

- [ ] **Step 1: Write the failing tests**

```python
    def test_svg_has_data_slots_for_every_parameter(self):
        html = self.client.get("/").data.decode("utf-8")
        for slot in ("vcc", "r1", "r2", "rb", "rc", "re", "beta", "vbe"):
            self.assertIn(f'data-slot="{slot}"', html)

    def test_svg_shows_submitted_values_with_units(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertIn("= 1 MΩ", html)
        self.assertIn("= 2.2 kΩ", html)
        self.assertIn("= 12 V", html)

    def test_circuit_labels_use_dash_for_empty_values(self):
        from app import circuit_labels
        labels = circuit_labels({}, {"r1_ohm": "kohm"})
        self.assertEqual(labels["r1"], "= —")
        self.assertEqual(labels["vcc"], "= —")

    def test_fixed_mode_hides_divider_components_in_svg(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertRegex(html, r'data-component="r1"[^>]*is-hidden')
        self.assertNotRegex(html, r'data-component="rb"[^>]*is-hidden')
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL — no `data-slot` attributes, `circuit_labels` import error.

- [ ] **Step 3: Implement `circuit_labels` in `app.py`**

```python
def _display(raw_value: str, unit: str | None = None, suffix: str = "") -> str:
    value = (raw_value or "").strip()
    if not value:
        return "= —"
    if unit:
        return f"= {value} {UNIT_SYMBOLS[unit]}"
    return f"= {value}{(' ' + suffix) if suffix else ''}"


def circuit_labels(raw, units):
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
```

Register it for the template: `app.jinja_env.globals["circuit_labels"] = circuit_labels`.

Do not add any DC formula here.

- [ ] **Step 4: Rebuild the SVG with slots and components**

At the top of the circuit panel add `{% set labels = circuit_labels(raw, units) %}` (or pass `circuit_labels=circuit_labels` and call it in the section). Then:

- Each value text becomes `<text ...><tspan>R</tspan><tspan baseline-shift="sub" font-size="10">1</tspan><tspan data-slot="r1">{{ labels.r1 }}</tspan></text>` and likewise for `vcc`, `r2`, `rb`, `rc`, `re`, `beta`, `vbe`.
- Wrap R1, R2, RB, RE drawings (wire + rect + label) in `<g data-component="r1" class="{{ 'is-hidden' if mode != 'divider' else '' }}">` etc. Rules: `r1`/`r2` → divider only; `rb` → fixed, emitter; `re` → divider, emitter.
- Add an RB branch (vertical wire from the top rail at x=236 down to the base line, resistor rect, label) so fixed/emitter have a real RB in the drawing.
- Replace inline `stroke`/`fill` with `class="wire"`, `class="comp"`, `class="lbl"` (classes defined in Task 4).
- Replace the static note with `Values shown follow your inputs; results are computed from the same values.`
- Load the script before `</body>`: `<script src="{{ url_for('static', filename='app.js') }}" defer></script>`.

- [ ] **Step 5: Write `static/app.js`**

```js
const UNIT_SYMBOLS = { ohm: "Ω", kohm: "kΩ", mohm: "MΩ" };

function labelText(id, unitId, suffix) {
  const input = document.getElementById(id);
  const raw = input ? input.value.trim() : "";
  if (!raw) return "= —";
  const unit = unitId ? document.getElementById(unitId) : null;
  if (unit) return `= ${raw} ${UNIT_SYMBOLS[unit.value] || ""}`.trimEnd();
  return `= ${raw}${suffix ? " " + suffix : ""}`;
}

function updateCircuit() {
  const values = {
    vcc: labelText("vcc_v", null, "V"),
    r1: labelText("r1_ohm", "r1_ohm_unit"),
    r2: labelText("r2_ohm", "r2_ohm_unit"),
    rb: labelText("rb_ohm", "rb_ohm_unit"),
    rc: labelText("rc_ohm", "rc_ohm_unit"),
    re: labelText("re_ohm", "re_ohm_unit"),
    beta: labelText("beta"),
    vbe: labelText("vbe_v", null, "V"),
  };
  for (const [slot, text] of Object.entries(values)) {
    const el = document.querySelector(`[data-slot="${slot}"]`);
    if (el) el.textContent = text;
  }
}

function applyMode(mode) {
  document.querySelectorAll("[data-field]").forEach((field) => {
    const modes = (field.dataset.modes || "").split(" ");
    field.hidden = !modes.includes(mode);
  });
  document.querySelectorAll("[data-component]").forEach((group) => {
    const modes = (group.dataset.modes || "").split(" ");
    group.classList.toggle("is-hidden", !modes.includes(mode));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const checked = document.querySelector('input[name="mode"]:checked');
  if (checked) applyMode(checked.value);
  updateCircuit();
  document.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.addEventListener("change", () => applyMode(radio.value));
  });
  document.querySelectorAll("input, select").forEach((control) => {
    control.addEventListener("input", updateCircuit);
    control.addEventListener("change", updateCircuit);
  });
});
```

`data-component` groups also need `data-modes`. No DC equation may appear in this file.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python -m unittest tests.test_app -v`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html static/app.js tests/test_app.py
git commit -m "feat: live circuit labels from user inputs"
```

---

### Task 4: Dark theme

**Files:**
- Modify: `static/style.css`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: SVG classes `wire`, `comp`, `lbl` from Task 3.
- Produces: dark CSS variables `--bg: #0B0D10`, `--panel: #14171C`, `--panel-soft: #1B1F26`, `--line: #262B33`, `--ink: #E8EAF0`, `--muted: #9AA3B2`, `--accent: #F5B301`, `--wire: #C9D1DE`; `.is-hidden { display: none; }`.

- [ ] **Step 1: Write the failing test**

```python
    def test_stylesheet_uses_dark_theme_tokens(self):
        import pathlib
        css = pathlib.Path("static/style.css").read_text(encoding="utf-8")
        for token in ("--bg: #0B0D10", "--panel: #14171C", "--ink: #E8EAF0", "--accent: #F5B301"):
            self.assertIn(token, css)
        self.assertIn(".is-hidden", css)
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python -m unittest tests.test_app -v`
Expected: FAIL — old cream tokens are still present.

- [ ] **Step 3: Replace the palette and component colours**

Rewrite `:root` with the dark tokens above (keep `--yellow-*` aliases only if a rule still uses them). Update `body` background (dark radial glow from `#1A1400`), header/panel/box shadows for dark, inputs/selects/unit chips to `--panel-soft` with `--line` borders and `--ink` text, table borders to `--line`, `.thevenin`/empty-state/notes to muted colours, status boxes to dark tinted green/red (`#0F2417`/`#2A1113` with `#4ADE80`/`#F87171` text), goal bar to `--panel` with accent border.

- [ ] **Step 4: Add SVG classes**

```css
.circuit { background: var(--panel-soft); border-color: var(--line); }
.circuit .wire { stroke: var(--wire); }
.circuit .comp { fill: var(--panel); stroke: var(--wire); }
.circuit .lbl { fill: var(--ink); }
.circuit .lbl-muted { fill: var(--muted); }
.circuit .dot { fill: var(--wire); }
.is-hidden { display: none; }
```

Ensure the transistor circle/nodes are visible against the dark fill and that the chip icon and footer SVG no longer use cream-only fills.

- [ ] **Step 5: Run the test and confirm it passes**

Run: `python -m unittest tests.test_app -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add static/style.css tests/test_app.py
git commit -m "feat: dark theme"
```

---

### Task 5: Regression and documentation

**Files:**
- Modify: `docs/validation.md`
- Test: manual Playwright MCP run + full unittest suite

**Interfaces:**
- Consumes: everything above.
- Produces: recorded evidence and docs.

- [ ] **Step 1: Run the full Python suite**

Run: `python -m unittest discover -s tests -v`
Expected: all tests PASS.

- [ ] **Step 2: Restart the app and re-run A1–A5 in Playwright MCP**

Navigate to `http://127.0.0.1:5000/`, select modes with the radio labels, fill values, click **Calculate DC Bias**, and re-snapshot after each submit. Expected: A1 1.23 mA / 8.052 V, A2 1.13 mA / 9.514 V, A3 1.03 mA / 8.705 V, A4 0.94 mA / 8.033 V, A5 alert `RB must be greater than 0` with cleared results and HTTP 400.

- [ ] **Step 3: Verify the live circuit and MΩ in the browser**

On the form, type `R1 = 100` unit `kΩ` and confirm the SVG text becomes `R1 = 100 kΩ` without pressing Calculate; switch to Fixed Bias and confirm R1/R2/RE fields and their SVG components disappear while RB appears; set `RB = 1` unit `MΩ` and confirm Calculate returns IC 1.13 mA / VCE 9.514 V.

- [ ] **Step 4: Capture evidence**

Take `browser_take_screenshot` of the dark form and of one result page; keep them under `.playwright-mcp/`.

- [ ] **Step 5: Update `docs/validation.md`**

Add a short section: units now include MΩ, mode selector behaviour, live circuit, dark theme, plus the A1–A5 rerun table with PASS/FAIL.

- [ ] **Step 6: Commit**

```bash
git add docs/validation.md
git commit -m "docs: record dark UI and MΩ validation"
```
