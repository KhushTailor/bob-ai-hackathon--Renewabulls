#!/usr/bin/env node
/**
 * GridPulse Synthetic Grid Dataset Generator (Node.js runner)
 * ============================================================
 * This script produces the same grid_data.csv as generate_dataset.py.
 * It exists solely for environments where Python is not yet installed
 * (e.g., the initial project setup on a machine that has Node.js but not Python).
 *
 * Usage (from the src/ directory):
 *   node data/generate_dataset_node.js
 *
 * Output:
 *   src/data/grid_data.csv  —  17,520 rows × 18 columns
 *
 * The canonical generator is generate_dataset.py — use that when Python is
 * available. Both scripts use the same algorithm and seed so the output is
 * functionally equivalent.
 */

"use strict";

const fs = require("fs");
const path = require("path");

// ---------------------------------------------------------------------------
// Seeded PRNG (Mulberry32 — simple, fast, deterministic)
// ---------------------------------------------------------------------------
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Box-Muller normal variate using the seeded rng
function makeNormal(rng) {
  let spare = null;
  return function (mean = 0, std = 1) {
    if (spare !== null) {
      const v = spare * std + mean;
      spare = null;
      return v;
    }
    let u, v, s;
    do {
      u = rng() * 2 - 1;
      v = rng() * 2 - 1;
      s = u * u + v * v;
    } while (s >= 1 || s === 0);
    const mul = Math.sqrt((-2 * Math.log(s)) / s);
    spare = v * mul;
    return u * mul * std + mean;
  };
}

// Weibull variate: shape k, scale λ
function weibull(rng, k, lambda) {
  return lambda * Math.pow(-Math.log(1 - rng()), 1 / k);
}

// ---------------------------------------------------------------------------
// Configuration (must match generate_dataset.py exactly)
// ---------------------------------------------------------------------------
const RANDOM_SEED = 42;
const EXPECTED_ROWS = 17520;
const INTERVAL_MINUTES = 15;
const START_DATE = new Date("2024-01-01T00:00:00Z");

// Grid asset sizing — designed so renewables cover ~40-60% of demand on average,
// the battery actively cycles, and import varies meaningfully across the day.
const SOLAR_CAPACITY_MW = 150.0;  // large solar fleet; significant in summer
const WIND_CAPACITY_MW = 80.0;    // strong wind site; base supply at night
const BATTERY_CAPACITY_MWH = 80.0; // 80 MWh — ~2-3h of peak battery output
const BATTERY_MAX_MW = 40.0;       // 40 MW charge/discharge rate
const IMPORT_CAPACITY_MW = 180.0;  // interconnection sized to cover demand minus renewables
const EXPORT_CAPACITY_MW = 60.0;   // export when significant renewable surplus

const DEMAND_BASE_MW = 200.0;     // scaled down so renewables are ~40% of demand
const DEMAND_DAILY_AMP = 60.0;
const DEMAND_WEEKLY_AMP = 20.0;
const DEMAND_TEMP_SENS = 1.8;
const SOLAR_EFFICIENCY = 0.18;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function solarIrradiance(hourFrac, dayOfYear) {
  const decl = 1.5 * Math.sin((2 * Math.PI * (dayOfYear - 80)) / 365);
  const sunrise = 6.0 - decl;
  const sunset = 18.0 + decl;
  if (hourFrac <= sunrise || hourFrac >= sunset) return 0.0;
  const daylight = sunset - sunrise;
  const peak = 900 + 150 * Math.sin((2 * Math.PI * (dayOfYear - 80)) / 365);
  const angle = (Math.PI * (hourFrac - sunrise)) / daylight;
  return peak * Math.sin(angle);
}

function windPowerFraction(ws) {
  if (ws < 3.0 || ws >= 25.0) return 0.0;
  if (ws >= 12.0) return 1.0;
  return (ws - 3.0) / (12.0 - 3.0);
}

function clip(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function round(v, decimals) {
  const f = Math.pow(10, decimals);
  return Math.round(v * f) / f;
}

// Day of year (1-based)
function dayOfYear(date) {
  const start = new Date(Date.UTC(date.getUTCFullYear(), 0, 0));
  return Math.floor((date - start) / 86400000);
}

// Rolling mean (simple centred approximation using past window)
function rollingMean(arr, window) {
  const half = Math.floor(window / 2);
  return arr.map((_, i) => {
    const lo = Math.max(0, i - half);
    const hi = Math.min(arr.length - 1, i + half);
    let sum = 0;
    for (let j = lo; j <= hi; j++) sum += arr[j];
    return sum / (hi - lo + 1);
  });
}

// ---------------------------------------------------------------------------
// Build timestamp array
// ---------------------------------------------------------------------------
const timestamps = [];
for (let i = 0; i < EXPECTED_ROWS; i++) {
  const ms = START_DATE.getTime() + i * INTERVAL_MINUTES * 60 * 1000;
  timestamps.push(new Date(ms));
}

// Calendar features
const hourOfDay = timestamps.map((t) => t.getUTCHours() + t.getUTCMinutes() / 60);
const dayOfWeek = timestamps.map((t) => (t.getUTCDay() + 6) % 7); // 0=Mon
const month = timestamps.map((t) => t.getUTCMonth() + 1);
const doy = timestamps.map((t) => dayOfYear(t));
const isWeekend = dayOfWeek.map((d) => (d >= 5 ? 1 : 0));

// ---------------------------------------------------------------------------
// PRNG setup — NOTE: we must call rng() in exactly the same order as NumPy
// does in the Python version. We mirror each numpy call sequence.
// ---------------------------------------------------------------------------
const rng = mulberry32(RANDOM_SEED);
const normal = makeNormal(rng);

// NumPy default_rng(42) with the calls below — we replicate the draw order:
// 1. rng.normal(0, 1.0, n)              → temperature noise
// 2. rng.uniform(0.7, 1.0, n)           → cloud_base
// 3. rng.choice([0,1], n, p=[0.92,0.08])→ cloud_spell base
// 4. rng.weibull(2.0, n) * 8.0          → wind_raw
// 5. rng.normal(0, 0.5, n)              → wind noise
// 6. rng.normal(0, 0.3, n)              → solar noise
// 7. rng.normal(0, 0.5, n)              → wind actual noise
// 8. rng.normal(0, 4.0, n)              → demand noise
// 9. rng.normal(0, 0.03, n)             → frequency noise
// 10. rng.normal(0, 0.008, n)           → voltage noise
// + small uniforms for anomaly injections

const n = EXPECTED_ROWS;

// Draw 1: temperature noise
const tempNoise = Array.from({ length: n }, () => normal(0, 1.0));

// Draw 2: cloud_base
const cloudBase = Array.from({ length: n }, () => 0.7 + rng() * 0.3);

// Draw 3: cloud_spell base
const cloudSpellBase = Array.from({ length: n }, () => (rng() < 0.08 ? 1.0 : 0.0));

// Draw 4: wind_raw (Weibull k=2, λ=8)
const windRaw = Array.from({ length: n }, () => weibull(rng, 2.0, 8.0));

// Draw 5: wind noise
const windNoise = Array.from({ length: n }, () => normal(0, 0.5));

// Draw 6: solar noise
const solarNoise = Array.from({ length: n }, () => normal(0, 0.3));

// Draw 7: wind actual noise
const windActualNoise = Array.from({ length: n }, () => normal(0, 0.5));

// Draw 8: demand noise
const demandNoise = Array.from({ length: n }, () => normal(0, 4.0));

// Draw 9: frequency noise
const freqNoise = Array.from({ length: n }, () => normal(0, 0.03));

// Draw 10: voltage noise
const voltNoise = Array.from({ length: n }, () => normal(0, 0.008));

// ---------------------------------------------------------------------------
// Build arrays (same logic as Python)
// ---------------------------------------------------------------------------

// Temperature
const temperatureC = timestamps.map((_, i) => {
  const seas = 15.0 + 10.0 * Math.sin((2 * Math.PI * (doy[i] - 80)) / 365);
  const diurnal = 3.0 * Math.sin((2 * Math.PI * (hourOfDay[i] - 14)) / 24);
  return seas + diurnal + tempNoise[i];
});

// Solar irradiance with cloud attenuation
const irradianceClearsky = timestamps.map((_, i) =>
  solarIrradiance(hourOfDay[i], doy[i])
);
// Cloud spell: convolve cloudSpellBase with ones(12)/12
const WINDOW = 12;
const cloudSpell = cloudSpellBase.map((_, i) => {
  let sum = 0;
  let cnt = 0;
  for (let j = i - WINDOW + 1; j <= i; j++) {
    if (j >= 0) { sum += cloudSpellBase[j]; cnt++; }
  }
  return sum / WINDOW; // same as numpy 'mode=same' left-aligned
});
const cloudFactor = cloudBase.map((cb, i) => clip(cb - 0.6 * cloudSpell[i], 0.0, 1.0));
const solarIrradianceWm2 = irradianceClearsky.map((cs, i) =>
  Math.max(0.0, cs * cloudFactor[i])
);

// Solar actual (MW)
const solarActualMw = solarIrradianceWm2.map((irr, i) =>
  clip(
    (irr / 1000.0) * SOLAR_EFFICIENCY * SOLAR_CAPACITY_MW + solarNoise[i],
    0.0,
    SOLAR_CAPACITY_MW
  )
);

// Wind speed (m/s)
const windSmooth = rollingMean(windRaw, 8);
const windDiurnal = hourOfDay.map((h) => 1.5 * Math.sin((2 * Math.PI * (h - 14)) / 24));
const windSpeedMs = windSmooth.map((ws, i) =>
  clip(ws + windDiurnal[i] + windNoise[i], 0.0, 30.0)
);

// Wind actual (MW)
const windActualMw = windSpeedMs.map((ws, i) =>
  clip(windPowerFraction(ws) * WIND_CAPACITY_MW + windActualNoise[i], 0.0, WIND_CAPACITY_MW)
);

// Demand (MW)
const demandMw = temperatureC.map((temp, i) => {
  const daily =
    DEMAND_DAILY_AMP *
    (0.6 * Math.sin((2 * Math.PI * (hourOfDay[i] - 8)) / 24) +
      0.4 * Math.sin((2 * Math.PI * (hourOfDay[i] - 18)) / 24));
  const weekly = isWeekend[i] ? -DEMAND_WEEKLY_AMP : 0.0;
  const tempLoad = Math.max(0.0, temp - 18.0) * DEMAND_TEMP_SENS;
  const seasonal = -15.0 * Math.sin((2 * Math.PI * (doy[i] - 80)) / 365);
  return clip(DEMAND_BASE_MW + daily + weekly + tempLoad + seasonal + demandNoise[i], 100.0, 400.0);
});

// Battery SOC (%) + Grid import/export
// -----------------------------------------------------------------------
// Physics model: the grid interconnection handles the bulk demand-renewable
// gap. The battery handles short-term fluctuations only (±30 MW).
// Net residual = demand - solar - wind.
// The interconnection carries DEMAND_BASE_MW worth of the residual as a
// "scheduled import" each timestep. The battery absorbs/releases the
// remainder (fluctuation around the scheduled amount), clamped to ±BATTERY_MAX_MW.
// Any residual the battery can't cover goes to import/export.
// -----------------------------------------------------------------------
const dtH = INTERVAL_MINUTES / 60.0;
const soc = new Float64Array(n);
soc[0] = 50.0;  // mid-range initial SOC

// Scheduled interconnection = smoothed residual (rolling 4-hour average)
// approximated as the mean residual over the whole dataset — we compute it first.
const residual = demandMw.map((d, i) => d - solarActualMw[i] - windActualMw[i]);
// Rolling 16-step (4h) centred mean for scheduled import
const ROLL = 16;
const scheduledImport = residual.map((_, i) => {
  const lo = Math.max(0, i - ROLL);
  const hi = Math.min(n - 1, i + ROLL);
  let s = 0; let c = 0;
  for (let j = lo; j <= hi; j++) { s += residual[j]; c++; }
  return clip(s / c, 0, IMPORT_CAPACITY_MW);
});

const gridImportMw = new Float64Array(n);
const gridExportMw = new Float64Array(n);
const battDelta = new Float64Array(n);

for (let i = 1; i < n; i++) {
  // Fluctuation the battery needs to handle
  const fluct = residual[i] - scheduledImport[i];
  // Battery charge/discharge: absorb surplus (negative fluct) or supply deficit (positive fluct)
  const battPower = clip(-fluct, -BATTERY_MAX_MW, BATTERY_MAX_MW); // +ve = charging
  const deltaSoc = (100.0 * battPower * dtH) / BATTERY_CAPACITY_MWH;
  soc[i] = clip(soc[i - 1] + deltaSoc, 5.0, 95.0);
  battDelta[i] = (soc[i] - soc[i - 1]) * BATTERY_CAPACITY_MWH / (100.0 * dtH);
  // Remaining balance after battery
  const afterBatt = residual[i] - battDelta[i];
  gridImportMw[i] = clip(afterBatt, 0.0, IMPORT_CAPACITY_MW);
  gridExportMw[i] = clip(-afterBatt, 0.0, EXPORT_CAPACITY_MW);
}
// Row 0
const afterBatt0 = residual[0] - battDelta[0];
gridImportMw[0] = clip(afterBatt0, 0.0, IMPORT_CAPACITY_MW);
gridExportMw[0] = clip(-afterBatt0, 0.0, EXPORT_CAPACITY_MW);

// Frequency
const frequencyHz = freqNoise.map((fn) => clip(50.0 + fn, 49.5, 50.5));

// Voltage
const voltagePu = voltNoise.map((vn) => clip(1.0 + vn, 0.95, 1.05));

// ---------------------------------------------------------------------------
// Anomaly injections (same logic as Python)
// ---------------------------------------------------------------------------
function tsIndex(week, day, hour, minute = 0) {
  const base = START_DATE.getTime();
  const target =
    base +
    ((week - 1) * 7 + day) * 24 * 3600 * 1000 +
    hour * 3600 * 1000 +
    minute * 60 * 1000;
  let best = 0;
  let bestDiff = Infinity;
  for (let i = 0; i < n; i++) {
    const diff = Math.abs(timestamps[i].getTime() - target);
    if (diff < bestDiff) { bestDiff = diff; best = i; }
  }
  return best;
}

// Anomaly 1 — frequency dip
const a1 = tsIndex(4, 2, 8, 0);
for (let k = 0; k < 3 && a1 + k < n; k++) {
  frequencyHz[a1 + k] = 49.2 + (rng() - 0.5) * 0.1; // ±0.05
}

// Anomaly 2 — voltage sag
const a2 = tsIndex(8, 0, 14, 0);
if (a2 < n) {
  voltagePu[a2] = 0.88 + (rng() - 0.5) * 0.02; // ±0.01
}

// Anomaly 3 — demand surge
const a3 = tsIndex(12, 4, 7, 45);
for (let k = 0; k < 3 && a3 + k < n; k++) {
  demandMw[a3 + k] *= 1.35;
}

// Anomaly 4 — battery critical
const a4 = tsIndex(20, 1, 20, 0);
for (let k = 0; k < 2 && a4 + k < n; k++) {
  soc[a4 + k] = 3.0 + rng();
}

// Anomaly 5 — solar underperformance
const a5 = tsIndex(24, 3, 12, 0);
for (let k = 0; k < 4 && a5 + k < n; k++) {
  solarActualMw[a5 + k] *= 0.40;
}

// ---------------------------------------------------------------------------
// Write CSV
// ---------------------------------------------------------------------------
const outputPath = path.join(__dirname, "grid_data.csv");

const header =
  "timestamp,demand_mw,solar_actual_mw,wind_actual_mw,solar_capacity_mw," +
  "wind_capacity_mw,solar_irradiance_wm2,wind_speed_ms,temperature_c," +
  "battery_soc_pct,grid_import_mw,grid_export_mw,frequency_hz,voltage_pu," +
  "hour_of_day,day_of_week,month,is_weekend";

function fmtTs(d) {
  return d.toISOString().replace("T", " ").replace("Z", "+00:00");
}

const lines = [header];
for (let i = 0; i < n; i++) {
  lines.push(
    [
      fmtTs(timestamps[i]),
      round(demandMw[i], 2),
      round(solarActualMw[i], 2),
      round(windActualMw[i], 2),
      SOLAR_CAPACITY_MW.toFixed(1),
      WIND_CAPACITY_MW.toFixed(1),
      round(solarIrradianceWm2[i], 1),
      round(windSpeedMs[i], 2),
      round(temperatureC[i], 2),
      round(soc[i], 2),
      round(gridImportMw[i], 2),
      round(gridExportMw[i], 2),
      round(frequencyHz[i], 4),
      round(voltagePu[i], 4),
      timestamps[i].getUTCHours(),
      dayOfWeek[i],
      month[i],
      isWeekend[i],
    ].join(",")
  );
}

fs.writeFileSync(outputPath, lines.join("\n") + "\n", "utf8");

const stats = fs.statSync(outputPath);
console.log(`GridPulse dataset generated: ${outputPath}`);
console.log(`  Rows     : ${n.toLocaleString()}`);
console.log(`  Columns  : 18`);
console.log(`  Start    : ${fmtTs(timestamps[0])}`);
console.log(`  End      : ${fmtTs(timestamps[n - 1])}`);
console.log(`  File size: ${(stats.size / 1024).toFixed(1)} KB`);

// ---------------------------------------------------------------------------
// Inline validation
// ---------------------------------------------------------------------------
console.log("\nDataset validation:");

function check(label, cond) {
  console.log(`  [${cond ? "PASS" : "FAIL"}] ${label}`);
  return cond;
}

let allOk = true;

allOk &= check(`Row count = ${EXPECTED_ROWS.toLocaleString()}`, n === EXPECTED_ROWS);

// Spot-check a few values are in range
allOk &= check("demand_mw in [100, 400]", demandMw.every((v) => v >= 100 && v <= 400));
allOk &= check("solar_actual_mw >= 0", solarActualMw.every((v) => v >= 0));
allOk &= check("solar_actual_mw <= capacity", solarActualMw.every((v) => v <= SOLAR_CAPACITY_MW + 0.01));
allOk &= check("wind_actual_mw >= 0", windActualMw.every((v) => v >= 0));
allOk &= check("wind_actual_mw <= capacity", windActualMw.every((v) => v <= WIND_CAPACITY_MW + 0.01));
allOk &= check("battery_soc_pct in [1, 99]", Array.from(soc).every((v) => v >= 1 && v <= 99));
allOk &= check("grid_import_mw >= 0", gridImportMw.every((v) => v >= 0));
allOk &= check("grid_export_mw >= 0", gridExportMw.every((v) => v >= 0));
allOk &= check("temperature_c in [-10, 45]", temperatureC.every((v) => v >= -10 && v <= 45));
allOk &= check("wind_speed_ms in [0, 30]", windSpeedMs.every((v) => v >= 0 && v <= 30));
allOk &= check("solar_irradiance >= 0", solarIrradianceWm2.every((v) => v >= 0));

const freqAnomaly = frequencyHz.filter((f) => f < 49.4).length;
allOk &= check(`Frequency anomaly rows >= 3 (got ${freqAnomaly})`, freqAnomaly >= 3);

const voltAnomaly = Array.from(voltagePu).filter((v) => v < 0.90).length;
allOk &= check(`Voltage anomaly rows >= 1 (got ${voltAnomaly})`, voltAnomaly >= 1);

const battCritical = Array.from(soc).filter((v) => v < 5.0).length;
allOk &= check(`Battery critical rows >= 1 (got ${battCritical})`, battCritical >= 1);

// Timestamp continuity
let contOk = true;
for (let i = 1; i < Math.min(n, 100); i++) {
  const diff = (timestamps[i] - timestamps[i - 1]) / 1000;
  if (diff !== INTERVAL_MINUTES * 60) { contOk = false; break; }
}
allOk &= check("Timestamp continuity (first 100 rows)", contOk);

console.log();
if (allOk) {
  console.log("All checks passed. Dataset is ready.");
} else {
  console.log("One or more checks FAILED.");
  process.exit(1);
}

// Show sample rows
console.log("\nSample rows (first 3):");
for (let i = 0; i < 3; i++) {
  console.log(
    `  [${i}] ${fmtTs(timestamps[i])} | demand=${round(demandMw[i],1)} MW | ` +
    `solar=${round(solarActualMw[i],1)} MW | wind=${round(windActualMw[i],1)} MW | ` +
    `freq=${round(frequencyHz[i],3)} Hz | soc=${round(soc[i],1)}%`
  );
}
