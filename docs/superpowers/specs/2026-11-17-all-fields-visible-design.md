# All Fields Always Visible — Design

**Date:** 2026-11-17
**Status:** Awaiting approval
**Supersedes (scope: field visibility only):** `2026-11-17-dark-ui-mode-selector-design.md`

## Intent

Every input on the form — VCC, R1, R2, RB, RC, RE, β, VBE — stays visible in
every Bias Mode. `app.py` keeps using (and validating) only the fields the
selected mode actually needs, so leftover values in the other boxes are never
parsed and never produce an error.

## Why

Students copy a circuit off a worksheet and want to see every parameter, not
have boxes disappear as they switch modes. Hiding R1/R2 also made the form jump
and made it hard to compare the three configurations. Skipping the unused
values server-side keeps the physics honest without punishing stale input.

## Goals

1. All eight field wrappers are rendered, visible, and enabled for divider,
   fixed and emitter modes — both on `GET /` and on every POST render.
2. `MODE_FIELDS` in `app.py` remains the single source of truth: POST parses,
   converts and validates only `MODE_FIELDS[mode]`.
3. Existing dark theme, balanced mode radios, `MΩ` units, live SVG values and
   the SVG's own per-mode component visibility (R1/R2 vs RB vs RE) are
   unchanged.
4. Every `<label for="...">` still matches an existing `id`.

## Non-goals

- No new per-field badge, hint, dimming or placeholder for unused fields. They
  look exactly like the fields the mode uses. The existing `.circuit-note`
  ("Divider uses R1/R2. Fixed and Emitter use RB…") is the only explanation.
- No change to equations, limits, results, routes, field names or units.
- No change to the SVG: it still draws only the components of the selected
  mode (approved by the user), because drawing R1, R2 and RB together would not
  be a real circuit.

## Approaches Considered

1. **Delete the field-visibility machinery (chosen).** Drop `data-field`,
   `data-modes` and the `hidden` render from field wrappers; drop
   `FIELD_VISIBILITY` and its context processor; `applyMode()` in `app.js` only
   toggles SVG `[data-component]` groups. Nothing left in the DOM claims a
   field can disappear.
2. Keep the attributes but always render visible, and stop toggling in JS.
   Works, but leaves dead `data-modes` markup and a confusing `FIELD_VISIBILITY`
   table that no longer describes the UI.
3. Keep `FIELD_VISIBILITY` as documentation only, with a test asserting every
   field lists all three modes. Rejected: it duplicates `MODE_FIELDS` and will
   drift.

## Design

### Template (`templates/index.html`)

Each parameter wrapper becomes plain `<div class="field">` — no `data-field`,
no `data-modes`, no `hidden` expression. Labels, ids, `name`s, unit selects and
values are untouched. SVG groups keep `data-component` / `data-modes` /
`is-hidden`, since the diagram still follows the mode.

### Server (`app.py`)

- Remove `FIELD_VISIBILITY` and `inject_form_metadata()`; nothing else uses
  `field_visibility`.
- Keep `MODE_FIELDS`, the per-mode parse/convert/validate loop, and all routes
  as they are. A fixed-bias POST with R1/R2/RE filled (even with junk like
  `"abc"`) must still return 200 and ignore them.
- `circuit_labels()` still formats all eight values, so the SVG text stays live
  for hidden-in-SVG components too.

### JavaScript (`static/app.js`)

`applyMode(mode)` keeps its name and only runs the `[data-component]` loop.
Field hiding code is deleted. `updateCircuit()` is unchanged and still updates
every `data-slot`, including slots inside groups the current mode hides.

### CSS (`static/style.css`)

No change. The `[hidden] { display: none !important; }` rule and `.is-hidden`
stay as generic utilities (`.is-hidden` is still used by the SVG).

### Tests (`tests/test_app.py`)

| Test | Change |
| --- | --- |
| `test_divider_mode_hides_rb_field` | Replace: divider GET renders all eight field ids with no `hidden`. |
| `test_fixed_mode_hides_divider_and_re_fields` | Replace: fixed POST renders all eight fields visible and RB visible. |
| `test_error_post_keeps_submitted_mode_and_units` | Drop the two `hidden` assertions; keep mode + unit assertions. |
| new `test_fixed_mode_ignores_stale_divider_and_re_values` | POST fixed with valid RB/RC and `r1_ohm="abc"`, `r2_ohm="-5"`, `re_ohm="abc"` → 200 and the same result as without them. |
| new `test_emitter_mode_ignores_stale_divider_values` | Same idea for emitter (R1/R2 junk ignored). |
| SVG, label, unit, theme tests | Unchanged. |

## What is left to the builder

Exact assertion wording for the "all fields visible" test (e.g. regex over each
`id="<name>"` block or a `data-field`-free check), and the `docs/validation.md`
entry for this round.
