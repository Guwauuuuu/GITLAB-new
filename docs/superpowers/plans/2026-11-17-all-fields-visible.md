# All Fields Always Visible — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep all eight input fields on the form in every Bias Mode while `app.py` validates and computes from only the fields the mode needs.

**Architecture:** Delete the field-visibility layer (`data-field` / `data-modes` / `hidden` on field wrappers, `FIELD_VISIBILITY`, and the JS field loop); `MODE_FIELDS` stays the single source of truth for server-side parsing and validation. The SVG keeps its own per-mode component visibility.

**Tech Stack:** Python 3 + Flask, Jinja2 template, vanilla JS, `unittest` (`python -m unittest discover -s tests -t .`).

**Spec:** `docs/superpowers/specs/2026-11-17-all-fields-visible-design.md`

## Global Constraints

- All eight fields (`vcc_v`, `r1_ohm`, `r2_ohm`, `rb_ohm`, `rc_ohm`, `re_ohm`, `beta`, `vbe_v`) are visible and enabled in divider, fixed and emitter modes, on GET and on every POST render.
- `MODE_FIELDS` in `app.py` remains the only list of fields a mode uses: divider = all of `FIELD_NAMES`; fixed = `vcc_v, rb_ohm, rc_ohm, beta, vbe_v`; emitter = `vcc_v, rb_ohm, rc_ohm, re_ohm, beta, vbe_v`.
- Unused fields are never parsed, converted, validated, rendered in errors, or used in results — even if they hold junk such as `abc`, `1e`, `-5`.
- No hint, badge, dimming or placeholder on unused fields; the existing `.circuit-note` is the only explanation.
- Every `<label for="...">` matches an existing `id`; field `name`s and unit values (`ohm`, `kohm`, `mohm`) do not change.
- No DC operating-point math in HTML or JavaScript; JS only formats display strings.
- SVG groups keep `data-component` / `data-modes` / `is-hidden`, and the SVG still hides R1/R2/tap or RB or RE per mode.
- Dark theme, balanced mode radios, `MΩ` conversion, live SVG values, `novalidate` form all stay.

## Review Focus

1. Fixed/emitter POST carrying junk in R1/R2/RE must return 200 with normal results, not a 400 "must be a number" page.
2. A leftover `MΩ`/`kΩ` unit choice on an unused field must not leak into the calculation.
3. Switching Bias Mode in the browser must not hide a field, clear a typed value, or need a reload.
4. The 400 error render must keep every field visible with the submitted values and mode.
5. The SVG must still hide the components a mode does not use.

---

### Task 1: Always render all eight fields (template + server cleanup)

**Files:**
- Modify: `templates/index.html:56-138` (eight `<div class="field" …>` wrappers)
- Modify: `app.py:52-55` (`FIELD_VISIBILITY`), `app.py:75-77` (`inject_form_metadata`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: existing `MODE_FIELDS`, `FIELD_NAMES`, `ALL_FIELDS`, `RESISTOR_FIELDS`, `UNIT_SCALE`, `circuit_labels()`.
- Produces: template with eight plain `<div class="field">` wrappers (no `data-field`, no `data-modes`, no `hidden`); `app.py` without `FIELD_VISIBILITY` / `field_visibility` context; new tests `test_every_mode_renders_all_fields_visible`, `test_fixed_mode_ignores_stale_divider_and_re_values`, `test_emitter_mode_ignores_stale_divider_values`.

- [ ] **Step 1: Replace the two hiding tests in `tests/test_app.py`**

Delete `test_divider_mode_hides_rb_field` and `test_fixed_mode_hides_divider_and_re_fields`, and add:

```python
    def test_every_mode_renders_all_fields_visible(self):
        good = {
            "divider": dict(vcc_v="12", r1_ohm="100", r1_ohm_unit="kohm",
                            r2_ohm="22", r2_ohm_unit="kohm",
                            rc_ohm="2.2", rc_ohm_unit="kohm",
                            re_ohm="1", re_ohm_unit="kohm",
                            beta="100", vbe_v="0.70"),
            "fixed": dict(vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                          rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70"),
            "emitter": dict(vcc_v="12", rb_ohm="1000", rb_ohm_unit="kohm",
                            rc_ohm="2.2", rc_ohm_unit="kohm",
                            re_ohm="1", re_ohm_unit="kohm",
                            beta="100", vbe_v="0.70"),
        }
        for mode, data in good.items():
            with self.subTest(mode=mode):
                response = self.client.post("/calculate", data=dict(data, mode=mode))
                self.assertEqual(response.status_code, 200)
                html = response.data.decode("utf-8")
                self.assertNotRegex(html, r'<div class="field"[^>]*\bhidden\b')
                self.assertEqual(html.count('<div class="field"'), 8)
                for name in ("vcc_v", "r1_ohm", "r2_ohm", "rb_ohm",
                             "rc_ohm", "re_ohm", "beta", "vbe_v"):
                    self.assertIn(f'id="{name}"', html)
```

- [ ] **Step 2: Add the stale-value guard tests**

```python
    def test_fixed_mode_ignores_stale_divider_and_re_values(self):
        base = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        stale = dict(base, r1_ohm="abc", r1_ohm_unit="mohm",
                     r2_ohm="-5", re_ohm="1e")
        html = self.client.post("/calculate", data=stale).data.decode("utf-8")
        self.assertNotIn('class="errors"', html)
        self.assertIn("1.13 mA", html)
        self.assertIn("9.514 V", html)

    def test_emitter_mode_ignores_stale_divider_values(self):
        base = dict(mode="emitter", vcc_v="12", rb_ohm="1000", rb_ohm_unit="kohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", re_ohm="1", re_ohm_unit="kohm",
                    beta="100", vbe_v="0.70")
        stale = dict(base, r1_ohm="abc", r2_ohm="0", r2_ohm_unit="mohm")
        html = self.client.post("/calculate", data=stale).data.decode("utf-8")
        self.assertNotIn('class="errors"', html)
        self.assertIn("1.03 mA", html)
        self.assertIn("8.705 V", html)
```

Also in `test_error_post_keeps_submitted_mode_and_units`, delete the two lines
`self.assertRegex(html, r'data-field="r1_ohm"[^>]*hidden')` and
`self.assertNotRegex(html, r'data-field="rb_ohm"[^>]*hidden')`, and add instead:

```python
        self.assertNotRegex(html, r'<div class="field"[^>]*\bhidden\b')
```

- [ ] **Step 3: Run the new tests**

Run: `python -m unittest tests.test_app.TestAppRoutes.test_every_mode_renders_all_fields_visible tests.test_app.TestAppRoutes.test_fixed_mode_ignores_stale_divider_and_re_values tests.test_app.TestAppRoutes.test_emitter_mode_ignores_stale_divider_values -v`

Expected: `test_every_mode_renders_all_fields_visible` FAILS (wrappers still carry `hidden` in fixed/emitter renders); the two stale-value tests PASS already — the server already parses only `MODE_FIELDS[mode]`. If a stale test fails, stop and fix `app.py`'s parse loop before touching the template.

- [ ] **Step 4: Simplify the eight field wrappers in `templates/index.html`**

Each of `vcc_v`, `r1_ohm`, `r2_ohm`, `rb_ohm`, `rc_ohm`, `re_ohm`, `beta`, `vbe_v` becomes exactly:

```html
        <div class="field">
```

with the existing `<label>`, `.control`, `<input>` and `<select>` children left byte-for-byte unchanged. The SVG section (`<g data-component=…>` groups) is not touched in this task.

- [ ] **Step 5: Remove the now-dead visibility metadata from `app.py`**

Delete the `FIELD_VISIBILITY = {...}` comprehension and the whole `inject_form_metadata` context processor with its `@app.context_processor` decorator. Leave `MODE_FIELDS`, `LABELS`, `DEFAULTS`, `DEFAULT_UNITS`, `circuit_labels`, routes and the POST logic untouched.

- [ ] **Step 6: Run the full suite**

Run: `python -m unittest discover -s tests -t .`

Expected: OK, 47 tests (46 − 2 deleted + 3 added).

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html tests/test_app.py \
  docs/superpowers/specs/2026-11-17-all-fields-visible-design.md \
  docs/superpowers/plans/2026-11-17-all-fields-visible.md
git commit -m "feat: show every input field in all bias modes"
```

---

### Task 2: Stop hiding fields from JavaScript

**Files:**
- Modify: `static/app.js:35-45` (`applyMode`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 1's template with no `data-field` wrappers.
- Produces: `applyMode(mode: string) -> void` that only toggles `is-hidden` on `[data-component]` groups; `updateCircuit()` unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_app.py`:

```python
    def test_javascript_does_not_hide_form_fields(self):
        import pathlib
        js = pathlib.Path("static/app.js").read_text(encoding="utf-8")
        self.assertNotIn("[data-field]", js)
        self.assertNotIn(".hidden", js)
        self.assertIn("data-component", js)
        self.assertIn("is-hidden", js)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest tests.test_app.TestAppRoutes.test_javascript_does_not_hide_form_fields -v`

Expected: FAIL — `assertNotIn("[data-field]", js)` trips on the current `applyMode`.

- [ ] **Step 3: Rewrite `applyMode` in `static/app.js`**

```javascript
function applyMode(mode) {
  document.querySelectorAll("[data-component]").forEach((group) => {
    const modes = (group.dataset.modes || "").split(" ").filter(Boolean);
    group.classList.toggle("is-hidden", !modes.includes(mode));
  });
}
```

Nothing else in the file changes: the `DOMContentLoaded` handler still calls `applyMode(checked.value)` and re-runs it on radio `change`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_app.TestAppRoutes.test_javascript_does_not_hide_form_fields -v`

Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover -s tests -t .`

Expected: OK, 48 tests.

- [ ] **Step 6: Commit**

```bash
git add static/app.js tests/test_app.py
git commit -m "refactor: limit mode switching in JS to the circuit diagram"
```

---

### Task 3: Docs, live acceptance run, and evidence

**Files:**
- Modify: `README.md:19`, `README.md:63-80`
- Modify: `docs/validation.md` (append a round-3 section)
- Test: browser (Playwright MCP) + `python -m unittest discover -s tests -t .`

**Interfaces:**
- Consumes: Tasks 1–2 (all fields visible, stale values ignored).
- Produces: README/validation text that matches the shipped behavior; screenshots in `.playwright-mcp/` (git-ignored).

- [ ] **Step 1: Update `README.md` wording**

- Line 19: `เลือกโหมดจากช่อง **Bias Mode** ในฟอร์ม` → `เลือกโหมดจากปุ่ม **Bias Mode** ในฟอร์ม`
- Line 65: same wording change.
- Table header line 71 `| โหมด | ช่องที่ต้องกรอก | หมายเหตุ |` → `| โหมด | ช่องที่ใช้คำนวณ | หมายเหตุ |`
- Line 79 bullet stays but add, directly above it: `- ฟอร์มแสดงช่องกรอกครบทั้ง 8 ช่องทุกโหมด ค่าที่โหมดนั้นไม่ใช้จะถูกมองข้าม` and keep `- ช่องที่โหมดนั้นไม่ใช้จะถูกมองข้าม (ไม่ถูกตรวจค่า) …` unchanged below it.

- [ ] **Step 2: Restart the dev server**

Flask runs with debug off, so template edits need a restart. Stop the process on port 5000, then start `python -m flask --app app run --port 5000` in the background and wait for `GET /` to return 200.

- [ ] **Step 3: Acceptance run B1–B5 in the browser**

Using Playwright against `http://127.0.0.1:5000/` (click the mode `label`s; the radios are `opacity:0`):

| ID | Action | Must see |
| --- | --- | --- |
| B1 | Load `/`, type R1 = `100` kΩ and R2 = `22` kΩ, click `label[for=mode_fixed]` | All 8 fields still visible; R1 = 100, R2 = 22 kept; SVG hides `r1`/`r2`/`divider-tap`, shows `rb` |
| B2 | In Fixed, put `1e` in R1 and R2, RB = `1` MΩ, RC = `2.2` kΩ, β 100, VBE 0.70 → Calculate | HTTP 200, I<sub>C</sub> 1.13 mA, V<sub>CE</sub> 9.514 V, no error box, all 8 fields visible |
| B3 | Switch to Emitter with RB `1000` kΩ, RC `2.2` kΩ, RE `1` kΩ → Calculate | I<sub>C</sub> 1.03 mA, V<sub>CE</sub> 8.705 V, all 8 fields visible |
| B4 | Switch to Divider with VCC 12, R1 100 k, R2 22 k, RC 2.2 k, RE 1 k → Calculate | I<sub>C</sub> 1.23 mA, V<sub>CE</sub> 8.052 V (unchanged from round 2) |
| B5 | Fixed with RB = `0` kΩ → Calculate | Alert `RB must be greater than 0`, POST 400, no results table, all 8 fields visible with the typed values |

Save `b1-fixed-all-fields.png` and `b5-error-all-fields.png` into `.playwright-mcp/`.

- [ ] **Step 4: Append the round-3 evidence to `docs/validation.md`**

Add a `## ตารางผลตรวจ B1–B5 (รอบที่ 3 — ทุกช่องแสดงตลอดเวลา)` section with the table above and its PASS results, plus a UI row replacing the old "ซ่อนช่องที่ไม่ใช้" behavior: `ทุกช่องแสดงตลอดเวลา | อ่าน computed display ของทั้ง 8 ช่องในแต่ละโหมด | เห็นครบ V_CC, R1, R2, R_B, R_C, R_E, β, V_BE ทั้ง Divider/Fixed/Emitter | PASS`. Keep the round-2 section as history; do not rewrite it.

- [ ] **Step 5: Final verification**

Run: `python -m unittest discover -s tests -t .` → OK, 48 tests.
Run: `git status --short` → only the intended files (`README.md`, `docs/validation.md`, plus `opencode.json` which stays uncommitted).

- [ ] **Step 6: Commit**

```bash
git add README.md docs/validation.md
git commit -m "docs: record all-fields-visible behaviour and round-3 acceptance"
```
