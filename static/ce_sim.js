// Common-Emitter Amplifier Simulator v1 front end.
// Every plotted point comes from /api/ce-simulate, which runs real ngspice.
// Nothing is interpolated or cached when a run fails: stale plots are cleared
// before the request and are only drawn after a success response.

"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const API_URL = "/api/ce-simulate";
const RUN_LABEL = "Run ngspice Simulation";

const UNIT_SYMBOLS = {
  ohm: "Ω", kohm: "kΩ", mohm: "MΩ",
  uf: "µF", nf: "nF", pf: "pF", f: "F",
  mv: "mV", v: "V",
  hz: "Hz", khz: "kHz", mhz: "MHz",
};

const ERROR_FIELDS = [
  ["Source amplitude", "source_amp"],
  ["Source frequency", "source_freq"],
  ["VBE", "vbe_v"],
  ["VCC", "vcc_v"],
  ["R1", "r1"],
  ["R2", "r2"],
  ["RC", "rc"],
  ["RE", "re"],
  ["RL", "rl"],
  ["Cin", "cin"],
  ["Cout", "cout"],
  ["beta", "beta"],
];

let runToken = 0;

function $(id) {
  return document.getElementById(id);
}

function fmt(value, digits) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "—";
}

function formatHz(value) {
  if (!Number.isFinite(value)) return "—";
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)} MHz`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(2)} kHz`;
  return `${value.toFixed(0)} Hz`;
}

function clearFieldErrors() {
  document.querySelectorAll("#ce-form .field-error").forEach((node) => node.remove());
  document.querySelectorAll("#ce-form .field.has-error").forEach((field) => field.classList.remove("has-error"));
  document.querySelectorAll('#ce-form [aria-invalid="true"]').forEach((input) => {
    input.removeAttribute("aria-invalid");
    input.removeAttribute("aria-describedby");
  });
}

function fieldForError(message) {
  const text = String(message || "").toLowerCase();
  const match = ERROR_FIELDS.find(([label]) => text.includes(label.toLowerCase()));
  return match ? match[1] : null;
}

function markFieldErrors(messages) {
  clearFieldErrors();
  let firstInvalid = null;

  messages.forEach((message) => {
    const fieldId = fieldForError(message);
    const input = fieldId ? $(fieldId) : null;
    if (!input) return;

    const field = input.closest(".field");
    const errorId = `${fieldId}-error`;
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", errorId);
    if (field) field.classList.add("has-error");

    const note = document.createElement("p");
    note.id = errorId;
    note.className = "field-error";
    note.textContent = message;
    if (field) field.insertAdjacentElement("afterend", note);

    if (!firstInvalid) firstInvalid = input;
  });

  return firstInvalid;
}

function setStatus(state, detail) {
  const box = $("engine-status");
  if (!box) return;
  box.className = `engine-status ${state}`;
  const labels = { idle: "Idle", running: "Running", success: "Success", error: "Error" };
  $("engine-state").textContent = labels[state] || state;
  $("engine-detail").textContent = detail;

  const runStatus = $("run-status");
  const runText = $("run-status-text");
  const runLabels = {
    idle: "Ready",
    running: "Running ngspice…",
    success: "ngspice success",
    error: "Simulation failed",
  };
  if (runStatus) runStatus.className = `run-status ${state}`;
  if (runText) runText.textContent = runLabels[state] || labels[state] || state;
}

function clearResults() {
  clearFieldErrors();
  setSlot("vce", "= ?");
  for (const id of ["op-results", "ac-results", "tran-results"]) {
    const section = $(id);
    if (section) section.hidden = true;
  }
  for (const id of ["ac-mag-plot", "ac-phase-plot", "tran-plot"]) {
    const plot = $(id);
    if (plot) plot.textContent = "";
  }
  const errors = $("sim-errors");
  if (errors) {
    errors.hidden = true;
    errors.textContent = "";
  }
  const empty = $("results-empty");
  if (empty) empty.hidden = true;
  const card = $("analytical-card");
  if (card) card.hidden = true;
  const anEmpty = $("analytical-empty");
  if (anEmpty) anEmpty.hidden = false;
}

function showError(body) {
  const box = $("sim-errors");
  if (!box) return;
  box.hidden = false;
  box.textContent = "";

  const messages = [];
  if (body && Array.isArray(body.errors) && body.errors.length) {
    messages.push(...body.errors);
  } else if (body && body.error) {
    messages.push(body.error);
  } else {
    messages.push("Simulation failed without an error message.");
  }

  messages.forEach((message) => {
    const line = document.createElement("div");
    line.className = "error";
    line.textContent = message;
    box.appendChild(line);
  });

  const firstInvalid = markFieldErrors(messages);
  if (firstInvalid) {
    firstInvalid.focus({ preventScroll: true });
    firstInvalid.scrollIntoView({ block: "center" });
  }

  if (body && body.stderr) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "ngspice diagnostics";
    const pre = document.createElement("pre");
    pre.className = "engine-log";
    pre.textContent = body.stderr;
    details.appendChild(summary);
    details.appendChild(pre);
    box.appendChild(details);
  }
}

function setSlot(slot, text) {
  document.querySelectorAll(`[data-ce-slot="${slot}"]`).forEach((node) => {
    node.textContent = "\u00A0" + text;
  });
}

function updateCircuitLabels() {
  const raw = (id) => {
    const input = $(id);
    return input ? input.value.trim() : "";
  };
  const symbol = (id) => {
    const select = $(id);
    return select ? (UNIT_SYMBOLS[select.value] || "") : "";
  };
  const withUnit = (id, unitId) => {
    const value = raw(id);
    return value ? `= ${value} ${symbol(unitId)}` : "= —";
  };

  setSlot("vcc", raw("vcc_v") ? `= ${raw("vcc_v")} V` : "= —");
  setSlot("r1", withUnit("r1", "r1_unit"));
  setSlot("r2", withUnit("r2", "r2_unit"));
  setSlot("rc", withUnit("rc", "rc_unit"));
  setSlot("re", withUnit("re", "re_unit"));
  setSlot("rl", withUnit("rl", "rl_unit"));
  setSlot("cin", withUnit("cin", "cin_unit"));
  setSlot("cout", withUnit("cout", "cout_unit"));

  const amp = raw("source_amp");
  const freq = raw("source_freq");
  setSlot("source", `${amp || "—"} ${symbol("source_amp_unit")} / ${freq || "—"} ${symbol("source_freq_unit")}`);
  setSlot("vce", "= ?");
}

// ---------------------------------------------------------------------------
// SVG chart helpers
// ---------------------------------------------------------------------------

function svgEl(tag, attrs) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    node.setAttribute(key, String(value));
  }
  return node;
}

function addText(svg, x, y, text, attrs) {
  const node = svgEl("text", { x, y, ...(attrs || {}) });
  node.textContent = text;
  svg.appendChild(node);
  return node;
}

function niceTicks(min, max, targetCount) {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
    const center = Number.isFinite(min) ? min : 0;
    return { low: center - 1, high: center + 1, ticks: [center - 1, center, center + 1] };
  }

  const rawStep = (max - min) / Math.max(targetCount, 1);
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const normalized = rawStep / magnitude;
  const niceStep = (
    normalized <= 1 ? 1
      : normalized <= 2 ? 2
        : normalized <= 2.5 ? 2.5
          : normalized <= 5 ? 5 : 10
  ) * magnitude;
  const low = Math.floor(min / niceStep) * niceStep;
  const high = Math.ceil(max / niceStep) * niceStep;
  const count = Math.round((high - low) / niceStep);
  const ticks = [];
  for (let index = 0; index <= count; index += 1) {
    ticks.push(Number((low + index * niceStep).toFixed(6)));
  }
  return { low, high, ticks };
}

function tickLabel(value) {
  return String(Number(value.toFixed(2)));
}

function addLegend(svg, entries, x, y) {
  if (!entries || !entries.length) return;
  const width = Math.max(...entries.map((entry) => entry.label.length)) * 6.2 + 48;
  const height = entries.length * 16 + 8;
  svg.appendChild(svgEl("rect", {
    x: x - 8, y: y - 14, width, height,
    fill: "#14171C", stroke: "#262B33", "stroke-width": 1, rx: 4, opacity: 0.94,
  }));

  entries.forEach((entry, index) => {
    const lineY = y + index * 16;
    svg.appendChild(svgEl("line", {
      x1: x, y1: lineY - 4, x2: x + 18, y2: lineY - 4,
      stroke: entry.color, "stroke-width": 2.2,
      "stroke-dasharray": entry.dash ? "5 4" : "",
    }));
    addText(svg, x + 24, lineY, entry.label, {
      fill: "#C9D1DE", "font-size": "11",
    });
  });
}

function frequencyPlot(container, values, options) {
  if (!container) return;
  container.textContent = "";

  const width = 900;
  const height = 320;
  const margin = { top: 36, right: 26, bottom: 50, left: 78 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": options.title,
    class: "plot-svg",
  });
  svg.appendChild(svgEl("title", {})).textContent = options.title;

  const xMin = Math.log10(values.freq[0]);
  const xMax = Math.log10(values.freq[values.freq.length - 1]);
  const yMin = options.yMin;
  const yMax = options.yMax;

  const xOf = (freq) => margin.left + ((Math.log10(freq) - xMin) / (xMax - xMin)) * plotW;
  const yOf = (value) => margin.top + plotH - ((value - yMin) / (yMax - yMin)) * plotH;

  // horizontal grid + y ticks
  const yTicks = options.yTicks;
  yTicks.forEach((tick) => {
    const y = yOf(tick);
    svg.appendChild(svgEl("line", {
      x1: margin.left, y1: y, x2: margin.left + plotW, y2: y,
      stroke: "#262B33", "stroke-width": 1,
    }));
    addText(svg, margin.left - 10, y + 4, tickLabel(tick), {
      "text-anchor": "end", fill: "#9AA3B2", "font-size": "12",
      "font-family": "ui-monospace, Consolas, monospace",
    });
  });

  // vertical decade grid + x ticks
  const firstDecade = Math.ceil(xMin);
  const lastDecade = Math.floor(xMax);
  for (let power = firstDecade; power <= lastDecade; power += 1) {
    const freq = 10 ** power;
    const x = xOf(freq);
    svg.appendChild(svgEl("line", {
      x1: x, y1: margin.top, x2: x, y2: margin.top + plotH,
      stroke: "#21262E", "stroke-width": 1,
    }));
    addText(svg, x, margin.top + plotH + 20, formatHz(freq), {
      "text-anchor": "middle", fill: "#9AA3B2", "font-size": "12",
    });
  }

  // axes
  svg.appendChild(svgEl("line", {
    x1: margin.left, y1: margin.top + plotH, x2: margin.left + plotW, y2: margin.top + plotH,
    stroke: "#9AA3B2", "stroke-width": 1,
  }));
  svg.appendChild(svgEl("line", {
    x1: margin.left, y1: margin.top, x2: margin.left, y2: margin.top + plotH,
    stroke: "#9AA3B2", "stroke-width": 1,
  }));

  if (Number.isFinite(options.zeroLine) && options.zeroLine >= yMin && options.zeroLine <= yMax) {
    const y = yOf(options.zeroLine);
    svg.appendChild(svgEl("line", {
      x1: margin.left, y1: y, x2: margin.left + plotW, y2: y,
      stroke: "#F5B301", "stroke-width": 1, "stroke-dasharray": "5 5", opacity: 0.7,
    }));
    addText(svg, margin.left + plotW - 4, y - 6, options.zeroLabel || "", {
      "text-anchor": "end", fill: "#F5B301", "font-size": "11",
    });
  }

  // trace
  let path = "";
  values.freq.forEach((freq, index) => {
    const x = xOf(freq);
    const y = yOf(values.y[index]);
    path += `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)} `;
  });
  svg.appendChild(svgEl("path", {
    d: path.trim(), fill: "none", stroke: options.color || "#F5B301", "stroke-width": 2.2,
    "stroke-linejoin": "round", "stroke-linecap": "round",
  }));

  addLegend(svg, options.legend, margin.left + plotW - 176, margin.top + 12);

  addText(svg, margin.left + plotW / 2, height - 8, "Frequency (Hz, log scale)", {
    "text-anchor": "middle", fill: "#E8EAF0", "font-size": "13",
  });
  addText(svg, 18, margin.top + plotH / 2, options.yLabel, {
    "text-anchor": "middle", fill: "#E8EAF0", "font-size": "13",
    transform: `rotate(-90 18 ${margin.top + plotH / 2})`,
  });
  addText(svg, margin.left, 20, options.title, {
    fill: "#E8EAF0", "font-size": "14", "font-weight": "600",
  });

  container.appendChild(svg);
}

function drawGainPlot(container, spice) {
  const gainDb = spice.gain_db;
  let low = Math.floor(Math.min(...gainDb) - 1);
  let high = Math.ceil(Math.max(...gainDb) + 1);
  if (high - low < 4) {
    low -= 1;
    high += 1;
  }
  const range = niceTicks(low, high, 5);

  frequencyPlot(container, { freq: spice.freq_hz, y: gainDb }, {
    title: "Gain Magnitude — 20·log10(|Vout/Vin|)",
    yLabel: "Gain (dB, re 1 V/V)",
    yMin: range.low,
    yMax: range.high,
    yTicks: range.ticks,
    color: "#F5B301",
    legend: [{ label: "|Vout/Vin| (dB)", color: "#F5B301" }],
  });
}

function drawPhasePlot(container, spice) {
  const phase = spice.phase_deg;
  const range = niceTicks(Math.min(...phase) - 4, Math.max(...phase) + 4, 6);

  frequencyPlot(container, { freq: spice.freq_hz, y: phase }, {
    title: "Phase — unwrapped (degrees)",
    yLabel: "Phase (deg)",
    yMin: range.low,
    yMax: range.high,
    yTicks: range.ticks,
    color: "#4ADE80",
    zeroLine: -180,
    zeroLabel: "-180° (inversion)",
    legend: [
      { label: "Phase (unwrapped)", color: "#4ADE80" },
      { label: "-180° reference", color: "#F5B301", dash: true },
    ],
  });
}

function drawTranPlot(container, spice) {
  if (!container) return;
  container.textContent = "";

  const width = 900;
  const height = 350;
  const margin = { top: 36, right: 26, bottom: 52, left: 82 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  const times = spice.time_s;
  const vin = spice.vin_v;
  const vout = spice.vout_v;
  const tMax = times[times.length - 1];
  const timeScale = tMax <= 1 ? 1000 : 1;
  const timeUnit = tMax <= 1 ? "ms" : "s";

  const peak = Math.max(
    ...vin.map((value) => Math.abs(value)),
    ...vout.map((value) => Math.abs(value)),
  );
  const voltScale = peak < 0.5 ? 1000 : 1;
  const voltUnit = peak < 0.5 ? "mV" : "V";

  let low = Math.min(...vin, ...vout) * voltScale;
  let high = Math.max(...vin, ...vout) * voltScale;
  const pad = Math.max((high - low) * 0.12, 0.5);
  const yRange = niceTicks(low - pad, high + pad, 6);
  low = yRange.low;
  high = yRange.high;

  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": "Transient Vin and Vout over time",
    class: "plot-svg",
  });
  svg.appendChild(svgEl("title", {})).textContent = "Transient Vin(t) and Vout(t)";

  const xOf = (time) => margin.left + (time / tMax) * plotW;
  const yOf = (value) => margin.top + plotH - ((value - low) / (high - low)) * plotH;

  yRange.ticks.forEach((value) => {
    const y = yOf(value);
    svg.appendChild(svgEl("line", {
      x1: margin.left, y1: y, x2: margin.left + plotW, y2: y,
      stroke: "#262B33", "stroke-width": 1,
    }));
    addText(svg, margin.left - 10, y + 4, tickLabel(value), {
      "text-anchor": "end", fill: "#9AA3B2", "font-size": "12",
      "font-family": "ui-monospace, Consolas, monospace",
    });
  });

  const xTicks = 6;
  for (let i = 0; i <= xTicks; i += 1) {
    const time = (tMax * i) / xTicks;
    const x = xOf(time);
    svg.appendChild(svgEl("line", {
      x1: x, y1: margin.top, x2: x, y2: margin.top + plotH,
      stroke: "#21262E", "stroke-width": 1,
    }));
    addText(svg, x, margin.top + plotH + 20, (time * timeScale).toFixed(2), {
      "text-anchor": "middle", fill: "#9AA3B2", "font-size": "12",
    });
  }

  svg.appendChild(svgEl("line", {
    x1: margin.left, y1: margin.top + plotH, x2: margin.left + plotW, y2: margin.top + plotH,
    stroke: "#9AA3B2", "stroke-width": 1,
  }));
  svg.appendChild(svgEl("line", {
    x1: margin.left, y1: margin.top, x2: margin.left, y2: margin.top + plotH,
    stroke: "#9AA3B2", "stroke-width": 1,
  }));

  const zeroY = yOf(0);
  svg.appendChild(svgEl("line", {
    x1: margin.left, y1: zeroY, x2: margin.left + plotW, y2: zeroY,
    stroke: "#9AA3B2", "stroke-width": 1, "stroke-dasharray": "4 4", opacity: 0.6,
  }));

  const series = [
    { data: vin, color: "#F5B301", label: "Vin(t)" },
    { data: vout, color: "#4ADE80", label: "Vout(t)" },
  ];
  series.forEach((entry) => {
    let path = "";
    entry.data.forEach((value, index) => {
      const x = xOf(times[index]);
      const y = yOf(value * voltScale);
      path += `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)} `;
    });
    svg.appendChild(svgEl("path", {
      d: path.trim(), fill: "none", stroke: entry.color, "stroke-width": 1.9,
      "stroke-linejoin": "round", "stroke-linecap": "round",
    }));

    const legendX = margin.left + plotW - 150;
    const legendY = margin.top + (series.indexOf(entry) * 18) + 4;
    svg.appendChild(svgEl("rect", {
      x: legendX, y: legendY - 9, width: 18, height: 3, fill: entry.color,
    }));
    addText(svg, legendX + 24, legendY - 2, `${entry.label}`, {
      fill: "#E8EAF0", "font-size": "12",
    });
  });

  addText(svg, margin.left + plotW / 2, height - 10, `Time (${timeUnit})`, {
    "text-anchor": "middle", fill: "#E8EAF0", "font-size": "13",
  });
  addText(svg, 18, margin.top + plotH / 2, `Voltage (${voltUnit})`, {
    "text-anchor": "middle", fill: "#E8EAF0", "font-size": "13",
    transform: `rotate(-90 18 ${margin.top + plotH / 2})`,
  });
  addText(svg, margin.left, 20, "Transient — Vin(t) and Vout(t), 180° inversion", {
    fill: "#E8EAF0", "font-size": "14", "font-weight": "600",
  });

  container.appendChild(svg);
}

// ---------------------------------------------------------------------------
// Result rendering
// ---------------------------------------------------------------------------

function setRegion(elementId, region) {
  const node = $(elementId);
  if (!node) return;
  node.className = `region-badge ${region}`;
  node.textContent = `Region: ${region}`;
}

function renderAnalytical(analytical) {
  const card = $("analytical-card");
  const empty = $("analytical-empty");

  if (!analytical || analytical.unavailable) {
    card.hidden = true;
    empty.hidden = false;
    if (analytical && analytical.reason) {
      const note = empty.querySelector(".muted");
      if (note) note.textContent = analytical.reason;
    }
    return;
  }

  card.hidden = false;
  empty.hidden = true;

  $("an-vb").textContent = fmt(analytical.vb_v, 3);
  $("an-ve").textContent = fmt(analytical.ve_v, 3);
  $("an-vc").textContent = fmt(analytical.vc_v, 3);
  $("an-vce").textContent = fmt(analytical.vce_v, 3);
  $("an-ib").textContent = fmt(analytical.ib_a * 1e6, 1);
  $("an-ic").textContent = fmt(analytical.ic_a * 1e3, 2);
  $("an-ie").textContent = fmt(analytical.ie_a * 1e3, 2);
  setRegion("an-region", analytical.region);

  $("op-an-vb").textContent = fmt(analytical.vb_v, 3);
  $("op-an-ve").textContent = fmt(analytical.ve_v, 3);
  $("op-an-vc").textContent = fmt(analytical.vc_v, 3);
  $("op-an-vce").textContent = fmt(analytical.vce_v, 3);
  $("op-an-ib").textContent = fmt(analytical.ib_a * 1e6, 1);
  $("op-an-ic").textContent = fmt(analytical.ic_a * 1e3, 2);
  setRegion("op-an-region", analytical.region);
}

function renderOp(spice) {
  $("op-vb").textContent = fmt(spice.vb_v, 3);
  $("op-ve").textContent = fmt(spice.ve_v, 3);
  $("op-vc").textContent = fmt(spice.vc_v, 3);
  $("op-vce").textContent = fmt(spice.vce_v, 3);
  $("op-ib").textContent = fmt(spice.ib_a * 1e6, 2);
  $("op-ic").textContent = fmt(spice.ic_a * 1e3, 3);
  setRegion("op-region", spice.region);
  setSlot("vce", `= ${fmt(spice.vce_v, 3)} V`);
}

function renderAc(spice) {
  $("ac-vin-ref").textContent = spice.vin_reference;
  $("ac-midband-gain").textContent = `${fmt(spice.midband_gain_vv, 3)} V/V`;
  $("ac-midband-db").textContent = `${fmt(spice.midband_gain_db, 2)} dB`;
  $("ac-midband-phase").textContent = `${fmt(spice.midband_phase_deg, 1)}°`;

  const low = spice.f_low_3db_hz;
  const high = spice.f_high_3db_hz;
  if (Number.isFinite(low) && Number.isFinite(high)) {
    $("ac-band").textContent = `${formatHz(low)} – ${formatHz(high)}`;
  } else if (Number.isFinite(high)) {
    $("ac-band").textContent = `< ${formatHz(high)}`;
  } else if (Number.isFinite(low)) {
    $("ac-band").textContent = `> ${formatHz(low)}`;
  } else {
    $("ac-band").textContent = "not within 10 Hz – 10 MHz";
  }

  drawGainPlot($("ac-mag-plot"), spice);
  drawPhasePlot($("ac-phase-plot"), spice);
}

function renderTran(spice) {
  $("tran-vin-pp").textContent = `${fmt(spice.summary.vin_pp_v * 1e3, 2)} mV`;
  $("tran-vout-pp").textContent = `${fmt(spice.summary.vout_pp_v * 1e3, 2)} mV`;
  $("tran-gain").textContent = `${fmt(spice.summary.gain_vv, 3)} V/V`;
  $("tran-inverted").textContent = spice.summary.phase_inverted ? "180° (inverted)" : "not inverted";
  drawTranPlot($("tran-plot"), spice);
}

function renderResults(body) {
  const spice = body.spice;
  renderAnalytical(body.analytical);
  $("results-empty").hidden = true;

  if (body.analysis === "op") {
    renderOp(spice);
    $("op-results").hidden = false;
  } else if (body.analysis === "ac") {
    renderAc(spice);
    $("ac-results").hidden = false;
  } else if (body.analysis === "tran") {
    renderTran(spice);
    $("tran-results").hidden = false;
  }
}

// ---------------------------------------------------------------------------
// Form wiring
// ---------------------------------------------------------------------------

async function runSimulation(event) {
  event.preventDefault();
  const token = ++runToken;
  const button = $("ce-run");

  clearResults();
  setStatus("running", "Engine: ngspice_con · Model: Q2N2222 · running batch analysis");
  if (button) {
    button.disabled = true;
    button.textContent = "Running…";
    button.setAttribute("aria-busy", "true");
  }

  try {
    const form = $("ce-form");
    const response = await fetch(API_URL, {
      method: "POST",
      body: new URLSearchParams(new FormData(form)),
      headers: { Accept: "application/json" },
    });

    let body = null;
    try {
      body = await response.json();
    } catch (parseError) {
      body = null;
    }
    if (token !== runToken) return;

    if (!response.ok || !body || body.status !== "success") {
      showError(body);
      const reason = (body && (body.error || (body.errors || [])[0])) || `HTTP ${response.status}`;
      setStatus("error", `Engine: ngspice_con · Model: Q2N2222 · Error: ${reason}`);
      return;
    }

    try {
      renderResults(body);
    } catch (renderError) {
      showError({ error: `Could not render results: ${renderError.message}` });
      setStatus("error", "Engine: ngspice_con · Model: Q2N2222 · rendering failed");
      return;
    }

    const engine = body.engine || {};
    const elapsed = Number.isFinite(engine.elapsed_s) ? ` · ${engine.elapsed_s.toFixed(2)} s` : "";
    setStatus(
      "success",
      `Engine: ${engine.name || "ngspice_con"} · Model: ${body.model_name || "Q2N2222"}${elapsed}`,
    );
  } catch (error) {
    if (token !== runToken) return;
    showError({ error: `Request failed: ${error.message}` });
    setStatus("error", `Engine: ngspice_con · Model: Q2N2222 · request failed`);
  } finally {
    if (token === runToken && button) {
      button.disabled = false;
      button.textContent = RUN_LABEL;
      button.removeAttribute("aria-busy");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateCircuitLabels();
  document.querySelectorAll("#ce-form input, #ce-form select").forEach((control) => {
    control.addEventListener("input", updateCircuitLabels);
    control.addEventListener("change", updateCircuitLabels);
  });
  const form = $("ce-form");
  if (form) form.addEventListener("submit", runSimulation);
});
