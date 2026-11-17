# Dark UI, Mode Selector, Live Circuit and MΩ Units — Design

**Date:** 2026-11-17
**Status:** Approved by the user ("เอาเลย")

## Intent

Improve the Lab 02 BJT DC bias web app without moving any DC operating-point
math out of Python: a balanced bias-mode selector that shows only the fields a
mode uses, an SVG circuit that reflects the values the user typed, an `MΩ`
resistance unit, and a dark theme.

## Why

Students mis-read the three-column form because every field is always visible,
and the centre circuit shows hard-coded example values that disagree with what
was entered. The bright cream theme is also hard to read in a dark room.

## Goals

1. Bias Mode as three equal, labelled radio buttons (Divider / Fixed / Emitter).
2. Only the fields a mode actually uses are visible; switching modes is instant.
3. `<label for>` matches the `id` of every labelled control.
4. SVG circuit shows VCC, R1, R2, RB, RC, RE, β, VBE from the real inputs, both
   while typing and after submit, and hides resistors the mode does not use.
5. `MΩ` available on all five resistor unit selects; `app.py` converts it.
6. Dark theme for the page and the SVG.
7. All DC equations stay in Python. JavaScript only formats/displays values.

## Non-goals

- No change to calculation results, validation limits, or the independent nodal
  cross-check.
- No framework, build step, or new dependency.
- No change to the Flask routes or field names.

## Constraints

- Existing tests in `tests/` must keep passing; `name="vcc_v" value=""` markup
  order is asserted by `test_get_form_has_empty_defaults`.
- JavaScript must never implement a bias equation. Unit-to-symbol mapping and
  (value, unit) string formatting are display concerns and are allowed.
- `MODE_FIELDS` in `app.py` remains the single source of truth for which fields
  each mode uses; the template and JS read from it.
- Unit values sent to the server stay `ohm`, `kohm`, `mohm`.

## Approaches Considered

1. **Segmented radio group + `static/app.js` (chosen).** Native radios keep the
   form working without JS, are reliable for Playwright, and let the server
   render the correct initial state. One small vanilla JS file handles toggling
   and SVG text.
2. **Full-width `<select>` + no JS.** Simplest, but cannot hide unused fields
   until submit and cannot update the SVG while typing.
3. **Server round-trip per mode change.** No JS, but slow and loses the live
   circuit requirement.

## Design

### Mode selector

`<fieldset>` with three `<input type="radio" name="mode">` (`mode_divider`,
`mode_fixed`, `mode_emitter`) and matching `<label for>`; styled as a segmented
control with three equal columns. `app.py` keeps accepting `mode` values
`divider`, `fixed`, `emitter`.

### Field visibility

`app.py` exposes `FIELD_VISIBILITY = {field: (modes...)}` derived from
`MODE_FIELDS` through a context processor. Each field wrapper carries
`data-field="<name>"` and `data-modes="divider fixed"`, and is rendered with the
`hidden` attribute when the current mode is not listed. `static/app.js` re-applies
`hidden` on radio change and on load.

### Circuit

SVG groups carry `data-component="r1|r2|rb|re"`; value spans carry
`data-slot="vcc|r1|r2|rb|rc|re|beta|vbe"`. `app.py` provides
`circuit_labels(raw, units)` returning display strings (`"= 100 kΩ"`, `"= —"`
for empty input); the template renders the initial text from it. JS recomputes the
same strings on `input`/`change`. SVG visibility uses a CSS class `is-hidden`
because the HTML `hidden` attribute does not apply to SVG elements.

### Units

`UNIT_SCALE = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}` and
`UNIT_SYMBOLS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}`. Unknown unit strings
fall back to `ohm`. Selected units survive the POST because the template re-selects
from the `units` context, as before.

### Dark theme

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#0B0D10` | page background |
| `--panel` | `#14171C` | cards |
| `--panel-soft` | `#1B1F26` | inner blocks, SVG fill |
| `--line` | `#262B33` | borders |
| `--ink` | `#E8EAF0` | primary text |
| `--muted` | `#9AA3B2` | secondary text |
| `--accent` | `#F5B301` | buttons, focus, highlights |
| `--wire` | `#C9D1DE` | SVG wires |
| `--green` / `--red` | `#4ADE80` / `#F87171` | status boxes |

SVG shapes move from inline colours to classes (`.wire`, `.comp`, `.lbl`) so the
theme owns the colours.

## What is left to the builder

Spacing/typography details, exact SVG label positions, and the wording of
`docs/validation.md` additions.
