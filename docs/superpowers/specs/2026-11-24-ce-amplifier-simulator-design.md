# Common-Emitter Amplifier Simulator v1 (ngspice) Design

**Goal:** Extend the existing ENG29 2121 Flask BJT DC Bias web app (Lab 3) with a working Common-Emitter Amplifier Simulator v1 powered by real `ngspice_con -b` simulations, while preserving all three Lab 3 analytical DC bias modes and all existing tests.

## Architecture & Approach
- **Chosen approach:** Add a dedicated `/ce-simulator` route (`templates/ce_simulator.html`, `static/ce_sim.js`) and JSON API (`POST /api/ce-simulate`), connected via a shared header navigation switcher on `/` and `/ce-simulator`.
- **Why:** `tests/test_app.py` pins exact DOM invariants on `/` and `/calculate` (empty defaults, 8 `.field` divs, 3 bias mode radios, 5 `mohm` selects). Keeping Lab 3's `/` and `/calculate` routes untouched guarantees 100% compatibility while letting the CE Simulator have its own baseline defaults, schematic (`Cin`, `Cout`, `RL`, `Vin`, unbypassed `RE`), and interactive plots.
- **Reused modules:** `bjt.py` (`BiasInput`, `validate`, `solve_base_loop`) provides the Lab 3 analytical DC reference alongside the SPICE `.op` output. `bias_modes.py`, `independent.py`, `electrical.py`, and `test_electrical.py` remain unchanged.

## Reference Circuit & Baseline Defaults
Reference topology: Voltage-divider biased NPN Common-Emitter stage with unbypassed `RE` (no emitter bypass capacitor), input coupling capacitor `Cin`, output coupling capacitor `Cout`, and load resistor `RL`:
- `VCC = 12 V`
- `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`, `RL = 10 kΩ`
- `Cin = 10 µF`, `Cout = 10 µF`
- `Vin` source: `10 mV` peak, `1 kHz` sine (and `1 V` AC reference for `.ac` transfer `V(out)/V(in)`)
- Transistor: Standard NPN BJT model `Q2N2222` (real Gummel-Poon parameters in ngspice)
- Lab 3 analytical reference inputs: uses the same `VCC`, `R1`, `R2`, `RC`, `RE` plus user-configurable analytical `β` (default `100`) and `VBE` (default `0.7 V`), clearly labeled separately from the real SPICE model output.

## Analysis Modes & Expected Outputs
1. **`.op` (DC Operating Point):**
   - Extracts `VB`, `VE`, `VC`, `VCE = VC - VE`, `IB`, `IC` from ngspice (`@q1[ib]`, `@q1[ic]`, node voltages).
   - Derives region (`cutoff` if `IC <= 1e-9` or `IB <= 0`, `saturation` if `VCE < 0.2 V`, else `active`).
   - Displays SPICE results side-by-side with Lab 3 analytical reference (`solve_base_loop`) under clearly distinct headings.
2. **`.ac` (AC Frequency Response):**
   - Decades sweep (`10 Hz` to `10 MHz`, 25 pts/dec) with `Vin` AC magnitude `1 V`, phase `0°`.
   - Plots Gain Magnitude `|Vout / Vin|` (both dB and linear V/V, explicitly stating `Vin` = input source node `in` before `Cin`) and Phase (converted from radians to degrees) vs logarithmic frequency (`Hz`), plus midband gain and `-3 dB` points.
3. **`.tran` (Transient Simulation):**
   - Simulates `SIN(0 <amp_v> <freq_hz>)` over 4 cycles with bounded max timestep (`period / 200`).
   - Plots `Vin(t)` and `Vout(t)` vs time (`ms`/`µs`) demonstrating `180°` phase inversion and realistic clipping when overdriven.

## Error Handling & Integrity Rules
- Subprocess runs `["ngspice_con", "-b", "circuit.cir"]` with `shell=False`, `timeout=10.0`, inside an isolated `tempfile.TemporaryDirectory()`.
- Rejects invalid inputs (`RE <= 0`, non-positive or non-finite values) before running ngspice (HTTP `400`).
- Non-zero exit codes, timeouts, missing/empty `wrdata` files, or `NaN`/`Inf` values return explicit `Error` status with diagnostic text; never fabricates traces or hides errors.
- Frontend clears prior results/plots while status is `Running` and keeps plots cleared on `Error`.
