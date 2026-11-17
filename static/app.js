// Display-only helpers for the circuit diagram. Bias equations live in Python.
const UNIT_SYMBOLS = { ohm: "Ω", kohm: "kΩ", mohm: "MΩ" };

function labelText(id, unitId, suffix) {
  const input = document.getElementById(id);
  const raw = input ? input.value.trim() : "";
  if (!raw) return "= —";

  const unit = unitId ? document.getElementById(unitId) : null;
  if (unit) {
    const symbol = UNIT_SYMBOLS[unit.value] || UNIT_SYMBOLS.ohm;
    return `= ${raw} ${symbol}`;
  }
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
    if (el) el.textContent = "\u00A0" + text;
  }
}

function applyMode(mode) {
  document.querySelectorAll("[data-field]").forEach((field) => {
    const modes = (field.dataset.modes || "").split(" ").filter(Boolean);
    field.hidden = !modes.includes(mode);
  });

  document.querySelectorAll("[data-component]").forEach((group) => {
    const modes = (group.dataset.modes || "").split(" ").filter(Boolean);
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
