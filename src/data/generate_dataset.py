"""
GridPulse Synthetic Grid Dataset Generator
===========================================
Generates a 6-month, 15-minute-interval synthetic electricity grid dataset
for use by all GridPulse features (forecasting, monitoring, anomaly detection,
simulation, and operator briefs).

Usage (from the src/ directory):
    python data/generate_dataset.py

Output:
    src/data/grid_data.csv  —  17,520 rows × 18 columns

Generation is deterministic: the same seed always produces the same CSV.

Column definitions
------------------
timestamp           UTC datetime, 15-min intervals, 6 months
demand_mw           Total grid electricity demand (MW)
solar_actual_mw     Actual solar photovoltaic generation (MW)
wind_actual_mw      Actual wind turbine generation (MW)
solar_capacity_mw   Installed solar capacity, constant (MW)
wind_capacity_mw    Installed wind capacity, constant (MW)
solar_irradiance_wm2  Surface solar irradiance (W/m²)
wind_speed_ms       10-m wind speed (m/s)
temperature_c       Ambient dry-bulb temperature (°C)
battery_soc_pct     Battery energy storage state of charge (%)
grid_import_mw      Power imported from external interconnection (MW)
grid_export_mw      Power exported to external interconnection (MW)
frequency_hz        Grid frequency (nominal 50.0 Hz)
voltage_pu          Grid voltage in per-unit (nominal 1.0 pu)
hour_of_day         Hour 0-23 (derived from timestamp)
day_of_week         Day 0=Mon … 6=Sun (derived)
month               Month 1-12 (derived)
is_weekend          1 if Saturday or Sunday, else 0 (derived)

Anomaly injections
------------------
A small number of deterministic anomalous periods are embedded so the
GridPulse anomaly engine has meaningful events to detect in the demo:

  Period 1  — week 4, day 3  08:00-08:45  frequency dip  (49.2 Hz)
  Period 2  — week 8, day 1  14:00-14:15  voltage sag    (0.91 pu)
  Period 3  — week 12, day 5 07:45-08:30  demand surge   (+ 25 %)
  Period 4  — week 20, day 2 20:00-20:30  battery critical (<5 %)
  Period 5  — week 24, day 4 12:00-12:45  solar underperf (PR 0.55)
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
START_DATE: str = "2024-01-01"
MONTHS: int = 6
INTERVAL_MINUTES: int = 15
EXPECTED_ROWS: int = 17_520

# Grid asset constants — sized so renewables cover ~40-60% of demand,
# battery actively cycles, and import varies meaningfully across the day.
SOLAR_CAPACITY_MW: float = 150.0   # large solar fleet; significant in summer
WIND_CAPACITY_MW: float = 80.0     # strong wind site; base supply at night
BATTERY_CAPACITY_MWH: float = 80.0 # 80 MWh — ~2-3h of peak battery output
BATTERY_MAX_MW: float = 40.0       # battery max charge/discharge rate
IMPORT_CAPACITY_MW: float = 180.0  # interconnection sized to cover demand minus renewables
EXPORT_CAPACITY_MW: float = 60.0   # max interconnection export

# Demand baseline parameters
DEMAND_BASE_MW: float = 200.0      # scaled down so renewables are ~40% of demand
DEMAND_DAILY_AMPLITUDE: float = 60.0
DEMAND_WEEKLY_AMPLITUDE: float = 20.0
DEMAND_TEMP_SENSITIVITY: float = 1.8  # MW per °C above 18°C

# Output path (relative to this file's directory)
OUTPUT_PATH: Path = Path(__file__).parent / "grid_data.csv"


# ---------------------------------------------------------------------------
# Helper: solar irradiance model
# ---------------------------------------------------------------------------

def _solar_irradiance(hour_frac: float, day_of_year: int) -> float:
    """Return clear-sky irradiance in W/m² for a given fractional hour and DOY.

    Uses a simple sinusoidal approximation of the diurnal cycle with a seasonal
    amplitude shift. Returns 0 during night hours.
    """
    # Solar declination shifts sunrise/sunset by ~±1.5 h between solstices
    declination_shift = 1.5 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
    sunrise = 6.0 - declination_shift
    sunset = 18.0 + declination_shift
    if hour_frac <= sunrise or hour_frac >= sunset:
        return 0.0
    daylight = sunset - sunrise
    solar_noon = (sunrise + sunset) / 2
    # Peak irradiance varies with season (higher in summer)
    peak = 900 + 150 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
    angle = math.pi * (hour_frac - sunrise) / daylight
    return peak * math.sin(angle)


# ---------------------------------------------------------------------------
# Helper: wind power curve (IEC Class II approximation)
# ---------------------------------------------------------------------------

def _wind_power_fraction(wind_speed_ms: float) -> float:
    """Return fraction of rated capacity [0, 1] for given wind speed (m/s).

    Piecewise linear approximation of a standard IEC Class II turbine:
      cut-in: 3 m/s,  rated: 12 m/s,  cut-out: 25 m/s
    """
    if wind_speed_ms < 3.0 or wind_speed_ms >= 25.0:
        return 0.0
    if wind_speed_ms >= 12.0:
        return 1.0
    return (wind_speed_ms - 3.0) / (12.0 - 3.0)


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    """Generate the synthetic GridPulse dataset and write it to *output_path*.

    Returns the resulting DataFrame for inspection.
    """
    rng = np.random.default_rng(RANDOM_SEED)

    # Build timestamp index (6 months, 15-min intervals, UTC)
    timestamps = pd.date_range(
        start=START_DATE,
        periods=EXPECTED_ROWS,
        freq=f"{INTERVAL_MINUTES}min",
        tz="UTC",
    )
    n = len(timestamps)

    # ------------------------------------------------------------------
    # Calendar features
    # ------------------------------------------------------------------
    hour_of_day = timestamps.hour + timestamps.minute / 60.0  # fractional hour
    day_of_week = timestamps.dayofweek                         # 0=Mon, 6=Sun
    month = timestamps.month
    day_of_year = timestamps.day_of_year
    is_weekend = (day_of_week >= 5).astype(int)

    # ------------------------------------------------------------------
    # Temperature (°C)
    #   Seasonal sinusoid (winter low ~5°C, summer high ~25°C) +
    #   daily cycle (±3°C) + Gaussian noise
    # ------------------------------------------------------------------
    seasonal_temp = 15.0 + 10.0 * np.sin(
        2 * math.pi * (day_of_year - 80) / 365
    )
    diurnal_temp = 3.0 * np.sin(
        2 * math.pi * (hour_of_day.values - 14) / 24
    )
    temperature_c = (
        seasonal_temp + diurnal_temp + rng.normal(0, 1.0, n)
    )

    # ------------------------------------------------------------------
    # Solar irradiance (W/m²)
    #   Deterministic clear-sky curve × random cloud factor (0.6–1.0)
    # ------------------------------------------------------------------
    irradiance_clearsky = np.array([
        _solar_irradiance(hf, doy)
        for hf, doy in zip(hour_of_day.values, day_of_year.values)
    ])
    # Cloud attenuation: mostly clear (0.85) with occasional overcast patches
    cloud_base = rng.uniform(0.7, 1.0, n)
    # Introduce multi-hour cloudy spells using a running low-pass filter
    cloud_spell = np.convolve(
        rng.choice([0.0, 1.0], size=n, p=[0.92, 0.08]),
        np.ones(12) / 12,
        mode="same",
    )
    cloud_factor = np.clip(cloud_base - 0.6 * cloud_spell, 0.0, 1.0)
    solar_irradiance_wm2 = np.maximum(0.0, irradiance_clearsky * cloud_factor)

    # ------------------------------------------------------------------
    # Wind speed (m/s)
    #   Weibull-like: k=2, λ=8, smoothed with rolling average to simulate
    #   temporal autocorrelation, plus a slight daily cycle
    # ------------------------------------------------------------------
    wind_raw = rng.weibull(2.0, n) * 8.0
    wind_smooth = pd.Series(wind_raw).rolling(8, min_periods=1, center=True).mean().values
    diurnal_wind = 1.5 * np.sin(2 * math.pi * (hour_of_day.values - 14) / 24)
    wind_speed_ms = np.clip(wind_smooth + diurnal_wind + rng.normal(0, 0.5, n), 0.0, 30.0)

    # ------------------------------------------------------------------
    # Solar actual generation (MW)
    #   irradiance × capacity × efficiency factor (0.18)
    # ------------------------------------------------------------------
    SOLAR_EFFICIENCY = 0.18  # fraction of irradiance → MW per unit capacity
    # Normalise: 1000 W/m² × efficiency × capacity_MW → actual_MW
    solar_actual_mw = np.clip(
        (solar_irradiance_wm2 / 1000.0) * SOLAR_EFFICIENCY * SOLAR_CAPACITY_MW
        + rng.normal(0, 0.3, n),
        0.0,
        SOLAR_CAPACITY_MW,
    )

    # ------------------------------------------------------------------
    # Wind actual generation (MW)
    # ------------------------------------------------------------------
    wind_fractions = np.array([_wind_power_fraction(ws) for ws in wind_speed_ms])
    wind_actual_mw = np.clip(
        wind_fractions * WIND_CAPACITY_MW + rng.normal(0, 0.5, n),
        0.0,
        WIND_CAPACITY_MW,
    )

    # ------------------------------------------------------------------
    # Demand (MW)
    #   Base + daily peak pattern + weekly weekend dip + temperature
    #   sensitivity above a comfort threshold of 18°C + small noise
    # ------------------------------------------------------------------
    # Daily cycle: peaks at 08:00 and 18:00, trough at 03:00
    daily_cycle = DEMAND_DAILY_AMPLITUDE * (
        0.6 * np.sin(2 * math.pi * (hour_of_day.values - 8) / 24)
        + 0.4 * np.sin(2 * math.pi * (hour_of_day.values - 18) / 24)
    )
    # Weekly cycle: weekends ~7% lower
    weekly_dip = np.where(is_weekend, -DEMAND_WEEKLY_AMPLITUDE, 0.0)
    # Temperature sensitivity: cooling load above 18°C
    temp_load = np.maximum(0.0, temperature_c - 18.0) * DEMAND_TEMP_SENSITIVITY
    # Seasonal drift: slightly higher demand in winter
    seasonal_demand = -15.0 * np.sin(2 * math.pi * (day_of_year - 80) / 365)
    demand_mw = np.clip(
        DEMAND_BASE_MW
        + daily_cycle
        + weekly_dip
        + temp_load
        + seasonal_demand
        + rng.normal(0, 4.0, n),
        100.0,
        400.0,
    )

    # ------------------------------------------------------------------
    # Battery SOC (%) + Grid import / export (MW)
    #
    # Physics model: the grid interconnection handles the bulk demand-renewable
    # gap. The battery handles short-term fluctuations only (±BATTERY_MAX_MW).
    #
    # residual         = demand - solar - wind          (total gap each step)
    # scheduled_import = 4-hour rolling mean of residual, clamped to [0, import_cap]
    #                    represents the pre-scheduled interconnection flow
    # fluctuation      = residual - scheduled_import    (fast variation)
    # battery power    = clip(-fluctuation, -max, +max) (+ve = charging)
    # remaining        = fluctuation - battery response  → extra import/export
    # ------------------------------------------------------------------
    dt_h = INTERVAL_MINUTES / 60.0
    residual = demand_mw - solar_actual_mw - wind_actual_mw

    # Rolling 4-hour (16-step) centred mean of residual → scheduled import
    scheduled_import = (
        pd.Series(residual)
        .rolling(window=16, min_periods=1, center=True)
        .mean()
        .clip(lower=0.0, upper=IMPORT_CAPACITY_MW)
        .values
    )

    soc = np.empty(n)
    soc[0] = 50.0  # mid-range initial SOC
    battery_delta_mw = np.zeros(n)
    grid_import_mw = np.zeros(n)
    grid_export_mw = np.zeros(n)

    for i in range(1, n):
        fluct = residual[i] - scheduled_import[i]
        # Battery absorbs/releases fluctuation, clamped to rated power
        batt_power = float(np.clip(-fluct, -BATTERY_MAX_MW, BATTERY_MAX_MW))
        delta_soc = 100.0 * batt_power * dt_h / BATTERY_CAPACITY_MWH
        soc[i] = float(np.clip(soc[i - 1] + delta_soc, 5.0, 95.0))
        battery_delta_mw[i] = (soc[i] - soc[i - 1]) * BATTERY_CAPACITY_MWH / (100.0 * dt_h)
        after_batt = residual[i] - battery_delta_mw[i]
        grid_import_mw[i] = float(np.clip(after_batt, 0.0, IMPORT_CAPACITY_MW))
        grid_export_mw[i] = float(np.clip(-after_batt, 0.0, EXPORT_CAPACITY_MW))

    # Row 0 (no prior SOC to diff against)
    after_batt_0 = residual[0] - battery_delta_mw[0]
    grid_import_mw[0] = float(np.clip(after_batt_0, 0.0, IMPORT_CAPACITY_MW))
    grid_export_mw[0] = float(np.clip(-after_batt_0, 0.0, EXPORT_CAPACITY_MW))

    # ------------------------------------------------------------------
    # Grid frequency (Hz)  — nominal 50.0 Hz with small noise
    # ------------------------------------------------------------------
    frequency_hz = 50.0 + rng.normal(0, 0.03, n)
    frequency_hz = np.clip(frequency_hz, 49.5, 50.5)

    # ------------------------------------------------------------------
    # Grid voltage (pu)  — nominal 1.0 pu with small noise
    # ------------------------------------------------------------------
    voltage_pu = 1.0 + rng.normal(0, 0.008, n)
    voltage_pu = np.clip(voltage_pu, 0.95, 1.05)

    # ------------------------------------------------------------------
    # Anomaly injections
    #   Five deterministic abnormal periods injected at known positions.
    #   Each anomaly is tagged by its approximate timestamp for reference.
    # ------------------------------------------------------------------
    def _ts_index(week: int, day: int, hour: int, minute: int = 0) -> int:
        """Return row index for a given week (1-based), weekday (0=Mon), hour, minute."""
        base = pd.Timestamp(START_DATE, tz="UTC")
        target = base + pd.Timedelta(weeks=week - 1, days=day, hours=hour, minutes=minute)
        diffs = (timestamps - target).total_seconds().abs()
        return int(diffs.argmin())

    # Anomaly 1 — frequency dip (CRITICAL ANO-001: |freq - 50| > 0.5)
    a1_start = _ts_index(week=4, day=2, hour=8, minute=0)
    for k in range(3):   # 3 × 15-min = 45 minutes
        if a1_start + k < n:
            frequency_hz[a1_start + k] = 49.2 + rng.uniform(-0.05, 0.05)

    # Anomaly 2 — voltage sag (CRITICAL ANO-004: voltage < 0.90)
    a2_start = _ts_index(week=8, day=0, hour=14, minute=0)
    if a2_start < n:
        voltage_pu[a2_start] = 0.88 + rng.uniform(-0.01, 0.01)

    # Anomaly 3 — demand surge (CRITICAL ANO-006: demand > forecast × 1.25)
    # We set demand 35% above its neighbours; the forecaster will predict the
    # baseline, so the surge is clearly detectable as an anomaly.
    a3_start = _ts_index(week=12, day=4, hour=7, minute=45)
    for k in range(3):   # 3 × 15-min = 45 minutes
        if a3_start + k < n:
            demand_mw[a3_start + k] *= 1.35

    # Anomaly 4 — battery critical (CRITICAL ANO-008: SOC < 5%)
    a4_start = _ts_index(week=20, day=1, hour=20, minute=0)
    for k in range(2):   # 30 minutes of critical SOC
        if a4_start + k < n:
            soc[a4_start + k] = 3.0 + rng.uniform(0, 1.0)

    # Anomaly 5 — solar underperformance (WARNING ANO-009: solar PR < 0.80)
    # Achieved by cutting actual output to ~55% of expected for 3+ periods.
    a5_start = _ts_index(week=24, day=3, hour=12, minute=0)
    for k in range(4):   # 4 × 15-min = 1 hour of underperformance
        if a5_start + k < n:
            solar_actual_mw[a5_start + k] *= 0.40  # PR ≈ 0.40 × normal

    # ------------------------------------------------------------------
    # Assemble DataFrame
    # ------------------------------------------------------------------
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "demand_mw": np.round(demand_mw, 2),
            "solar_actual_mw": np.round(solar_actual_mw, 2),
            "wind_actual_mw": np.round(wind_actual_mw, 2),
            "solar_capacity_mw": float(SOLAR_CAPACITY_MW),
            "wind_capacity_mw": float(WIND_CAPACITY_MW),
            "solar_irradiance_wm2": np.round(solar_irradiance_wm2, 1),
            "wind_speed_ms": np.round(wind_speed_ms, 2),
            "temperature_c": np.round(temperature_c, 2),
            "battery_soc_pct": np.round(soc, 2),
            "grid_import_mw": np.round(grid_import_mw, 2),
            "grid_export_mw": np.round(grid_export_mw, 2),
            "frequency_hz": np.round(frequency_hz, 4),
            "voltage_pu": np.round(voltage_pu, 4),
            "hour_of_day": timestamps.hour,
            "day_of_week": day_of_week.values,
            "month": month.values,
            "is_weekend": is_weekend,
        }
    )

    # ------------------------------------------------------------------
    # Write CSV
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"GridPulse dataset generated: {output_path}")
    print(f"  Rows     : {len(df):,}")
    print(f"  Columns  : {len(df.columns)}")
    print(f"  Start    : {df['timestamp'].iloc[0]}")
    print(f"  End      : {df['timestamp'].iloc[-1]}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")

    return df


# ---------------------------------------------------------------------------
# Inline validation (run after generation)
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame) -> bool:
    """Run basic sanity checks on the generated dataset.

    Prints a PASS/FAIL line for each check and returns True if all pass.
    """
    EXPECTED_COLS = {
        "timestamp", "demand_mw", "solar_actual_mw", "wind_actual_mw",
        "solar_capacity_mw", "wind_capacity_mw", "solar_irradiance_wm2",
        "wind_speed_ms", "temperature_c", "battery_soc_pct",
        "grid_import_mw", "grid_export_mw", "frequency_hz", "voltage_pu",
        "hour_of_day", "day_of_week", "month", "is_weekend",
    }
    passed = True

    def check(label: str, condition: bool) -> None:
        nonlocal passed
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {label}")
        if not condition:
            passed = False

    print("\nDataset validation:")
    check(f"Row count = {EXPECTED_ROWS:,}", len(df) == EXPECTED_ROWS)
    check("All required columns present", EXPECTED_COLS <= set(df.columns))
    check("No null/NaN values", df.isnull().sum().sum() == 0)

    # Timestamp continuity
    deltas = df["timestamp"].diff().dropna().dt.total_seconds()
    check(
        f"All intervals = {INTERVAL_MINUTES} min",
        (deltas == INTERVAL_MINUTES * 60).all(),
    )

    # Numeric range checks
    check("demand_mw  in [100, 400]",  df["demand_mw"].between(100, 400).all())
    check("solar_actual_mw >= 0",       (df["solar_actual_mw"] >= 0).all())
    check("solar_actual_mw <= solar_capacity", (df["solar_actual_mw"] <= SOLAR_CAPACITY_MW + 0.01).all())
    check("wind_actual_mw >= 0",        (df["wind_actual_mw"] >= 0).all())
    check("wind_actual_mw <= wind_capacity",   (df["wind_actual_mw"] <= WIND_CAPACITY_MW + 0.01).all())
    check("battery_soc_pct in [1, 99]", df["battery_soc_pct"].between(1.0, 99.0).all())
    check("grid_import_mw >= 0",        (df["grid_import_mw"] >= 0).all())
    check("grid_export_mw >= 0",        (df["grid_export_mw"] >= 0).all())
    check("temperature_c in [-10, 45]", df["temperature_c"].between(-10, 45).all())
    check("wind_speed_ms in [0, 30]",   df["wind_speed_ms"].between(0, 30).all())
    check("solar_irradiance_wm2 >= 0",  (df["solar_irradiance_wm2"] >= 0).all())

    # Anomaly injections detectable
    freq_anomaly = (df["frequency_hz"] < 49.4).sum()
    check(f"Frequency anomaly rows injected (expected >=3, got {freq_anomaly})", freq_anomaly >= 3)
    volt_anomaly = (df["voltage_pu"] < 0.90).sum()
    check(f"Voltage anomaly rows injected (expected >=1, got {volt_anomaly})", volt_anomaly >= 1)
    batt_critical = (df["battery_soc_pct"] < 5.0).sum()
    check(f"Battery critical rows injected (expected >=1, got {batt_critical})", batt_critical >= 1)

    return passed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = generate()
    ok = validate(df)
    print()
    if ok:
        print("All checks passed. Dataset is ready.")
    else:
        print("One or more checks FAILED. Review output above.")
        sys.exit(1)
