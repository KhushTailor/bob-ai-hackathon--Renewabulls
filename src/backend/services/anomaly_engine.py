"""
GridPulse Anomaly & Red-Flag Engine
=====================================
Deterministic, rule-based anomaly detection applied to grid telemetry.

Twelve rules are evaluated against a Pandas DataFrame row (or the latest
dataset row).  Each triggered rule produces an Alert object with a
structured message, severity, and traceable rule identifier.

This is a simulated decision-support prototype.
It does NOT control real grid hardware or provide certified grid protection.

Rules
-----
ANO-001  Frequency deviation — CRITICAL   |freq - 50| > 0.5 Hz
ANO-002  Frequency drift    — WARNING     |freq - 50| > 0.2 Hz
ANO-003  Voltage excursion  — WARNING     voltage < 0.95 or > 1.05 pu
ANO-004  Voltage severe     — CRITICAL    voltage < 0.90 or > 1.10 pu
ANO-005  Demand surge       — WARNING     demand > DEMAND_SURGE_WARN  MW
ANO-006  Demand surge crit  — CRITICAL    demand > DEMAND_SURGE_CRIT  MW
ANO-007  Battery low        — WARNING     SOC < 15 %
ANO-008  Battery critical   — CRITICAL    SOC < 5 %
ANO-009  Battery high       — INFO        SOC > 92 % (over-charge risk)
ANO-010  Solar underperform — WARNING     solar PR < 0.55 when irradiance > 200 W/m²
ANO-011  High import        — WARNING     import > 90 % of import capacity
ANO-012  Low RE contribution— INFO        renewable_pct < 15 %
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

import pandas as pd

from backend.services.data_loader import get_latest_rows, load_dataset

# ---------------------------------------------------------------------------
# Thresholds (centralised — change here, not scattered through rules)
# ---------------------------------------------------------------------------
FREQ_NOMINAL_HZ: float = 50.0
FREQ_CRIT_BAND_HZ: float = 0.5        # ANO-001
FREQ_WARN_BAND_HZ: float = 0.2        # ANO-002

VOLT_WARN_LO: float = 0.95            # ANO-003 lower bound
VOLT_WARN_HI: float = 1.05            # ANO-003 upper bound
VOLT_CRIT_LO: float = 0.90            # ANO-004 lower bound
VOLT_CRIT_HI: float = 1.10            # ANO-004 upper bound

DEMAND_SURGE_WARN_MW: float = 230.0   # ANO-005 — ~p95 of normal demand
DEMAND_SURGE_CRIT_MW: float = 245.0   # ANO-006

BATT_WARN_LO_PCT: float = 15.0        # ANO-007
BATT_CRIT_LO_PCT: float = 5.0         # ANO-008
BATT_HIGH_PCT: float = 92.0           # ANO-009

SOLAR_UNDERPERF_PR: float = 0.55      # ANO-010 performance ratio threshold
SOLAR_UNDERPERF_MIN_IRR: float = 200.0 # only check when irradiance > 200 W/m²
SOLAR_EFFICIENCY: float = 0.18        # fraction of (irr/1000) × capacity → MW
SOLAR_CAPACITY_MW: float = 150.0      # must match generate_dataset.py

IMPORT_WARN_PCT: float = 0.90         # ANO-011  fraction of import capacity
IMPORT_CAPACITY_MW: float = 180.0     # must match generate_dataset.py

RE_LOW_WARN_PCT: float = 15.0         # ANO-012 renewable utilisation threshold

WIND_UNDERPERF_PR: float = 0.55       # ANO-013 performance ratio threshold
WIND_UNDERPERF_MIN_SPEED: float = 4.0 # only check when wind > 4 m/s
WIND_CAPACITY_MW: float = 80.0        # must match generate_dataset.py

CURTAILMENT_EXPORT_MW: float = 59.0   # ANO-014 export limit proxy

TEMP_WARN_HI: float = 35.0            # ANO-015
TEMP_WARN_LO: float = -5.0            # ANO-015

IMPORT_CRIT_PCT: float = 0.98         # ANO-016


# ---------------------------------------------------------------------------
# Alert data class
# ---------------------------------------------------------------------------
@dataclass
class Alert:
    """A single triggered anomaly alert."""

    rule_id: str                   # e.g. "ANO-001"
    severity: str                  # "CRITICAL" | "WARNING" | "INFO"
    category: str                  # e.g. "frequency", "voltage", "battery"
    title: str
    message: str
    metric_name: str               # name of the primary measured value
    metric_value: float            # current value
    threshold: float | None = None # threshold that was breached (None for info)
    timestamp: str = field(default_factory=lambda: _now_utc())
    alert_id: str = ""

    def __post_init__(self) -> None:
        if not self.alert_id:
            safe_ts = self.timestamp.replace(":", "").replace(" ", "T").replace("+00:00", "Z")
            self.alert_id = f"{self.rule_id}-{safe_ts}"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Individual rule functions
# (each takes a pandas Series row and returns an Alert or None)
# ---------------------------------------------------------------------------

def _rule_ano001(row: pd.Series) -> Alert | None:
    """ANO-001: Frequency deviation — CRITICAL."""
    freq = float(row["frequency_hz"])
    deviation = abs(freq - FREQ_NOMINAL_HZ)
    if deviation > FREQ_CRIT_BAND_HZ:
        return Alert(
            rule_id="ANO-001",
            severity="CRITICAL",
            category="frequency",
            title="Frequency deviation — CRITICAL",
            message=(
                f"Grid frequency is {freq:.3f} Hz, deviating {deviation:.3f} Hz "
                f"from nominal {FREQ_NOMINAL_HZ} Hz (threshold ±{FREQ_CRIT_BAND_HZ} Hz). "
                "Immediate balancing action required."
            ),
            metric_name="frequency_hz",
            metric_value=round(freq, 4),
            threshold=FREQ_CRIT_BAND_HZ,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano002(row: pd.Series) -> Alert | None:
    """ANO-002: Frequency drift — WARNING."""
    freq = float(row["frequency_hz"])
    deviation = abs(freq - FREQ_NOMINAL_HZ)
    # Only warn if not already at critical level
    if FREQ_WARN_BAND_HZ < deviation <= FREQ_CRIT_BAND_HZ:
        return Alert(
            rule_id="ANO-002",
            severity="WARNING",
            category="frequency",
            title="Frequency drift — WARNING",
            message=(
                f"Grid frequency is {freq:.3f} Hz, drifting {deviation:.3f} Hz "
                f"from nominal {FREQ_NOMINAL_HZ} Hz (threshold ±{FREQ_WARN_BAND_HZ} Hz). "
                "Monitor closely; prepare balancing action."
            ),
            metric_name="frequency_hz",
            metric_value=round(freq, 4),
            threshold=FREQ_WARN_BAND_HZ,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano003(row: pd.Series) -> Alert | None:
    """ANO-003: Voltage excursion — WARNING."""
    volt = float(row["voltage_pu"])
    if (volt < VOLT_WARN_LO or volt > VOLT_WARN_HI) and not (
        volt < VOLT_CRIT_LO or volt > VOLT_CRIT_HI
    ):
        direction = "low" if volt < VOLT_WARN_LO else "high"
        limit = VOLT_WARN_LO if direction == "low" else VOLT_WARN_HI
        return Alert(
            rule_id="ANO-003",
            severity="WARNING",
            category="voltage",
            title=f"Voltage excursion {direction} — WARNING",
            message=(
                f"Grid voltage is {volt:.4f} pu ({direction} of {limit} pu band). "
                "Check reactive power compensation."
            ),
            metric_name="voltage_pu",
            metric_value=round(volt, 4),
            threshold=limit,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano004(row: pd.Series) -> Alert | None:
    """ANO-004: Severe voltage excursion — CRITICAL."""
    volt = float(row["voltage_pu"])
    if volt < VOLT_CRIT_LO or volt > VOLT_CRIT_HI:
        direction = "low" if volt < VOLT_CRIT_LO else "high"
        limit = VOLT_CRIT_LO if direction == "low" else VOLT_CRIT_HI
        return Alert(
            rule_id="ANO-004",
            severity="CRITICAL",
            category="voltage",
            title=f"Severe voltage excursion {direction} — CRITICAL",
            message=(
                f"Grid voltage is {volt:.4f} pu, breaching critical threshold "
                f"({direction} limit {limit} pu). Immediate voltage regulation required."
            ),
            metric_name="voltage_pu",
            metric_value=round(volt, 4),
            threshold=limit,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano005(row: pd.Series) -> Alert | None:
    """ANO-005: Demand surge — WARNING."""
    demand = float(row["demand_mw"])
    if DEMAND_SURGE_WARN_MW <= demand < DEMAND_SURGE_CRIT_MW:
        return Alert(
            rule_id="ANO-005",
            severity="WARNING",
            category="demand",
            title="Demand surge — WARNING",
            message=(
                f"Grid demand has reached {demand:.1f} MW, exceeding the surge "
                f"warning threshold of {DEMAND_SURGE_WARN_MW} MW. "
                "Prepare additional generation or load-shedding resources."
            ),
            metric_name="demand_mw",
            metric_value=round(demand, 2),
            threshold=DEMAND_SURGE_WARN_MW,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano006(row: pd.Series) -> Alert | None:
    """ANO-006: Extreme demand surge — CRITICAL."""
    demand = float(row["demand_mw"])
    if demand >= DEMAND_SURGE_CRIT_MW:
        return Alert(
            rule_id="ANO-006",
            severity="CRITICAL",
            category="demand",
            title="Extreme demand surge — CRITICAL",
            message=(
                f"Grid demand has reached {demand:.1f} MW, exceeding the critical "
                f"surge threshold of {DEMAND_SURGE_CRIT_MW} MW. "
                "Immediate balancing action required to prevent load shedding."
            ),
            metric_name="demand_mw",
            metric_value=round(demand, 2),
            threshold=DEMAND_SURGE_CRIT_MW,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano007(row: pd.Series) -> Alert | None:
    """ANO-007: Battery low — WARNING."""
    soc = float(row["battery_soc_pct"])
    if BATT_CRIT_LO_PCT <= soc < BATT_WARN_LO_PCT:
        return Alert(
            rule_id="ANO-007",
            severity="WARNING",
            category="battery",
            title="Battery state of charge low — WARNING",
            message=(
                f"Battery SOC is {soc:.1f}%, below the warning threshold "
                f"of {BATT_WARN_LO_PCT}%. Reduce battery discharge or increase "
                "renewable generation to recharge."
            ),
            metric_name="battery_soc_pct",
            metric_value=round(soc, 2),
            threshold=BATT_WARN_LO_PCT,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano008(row: pd.Series) -> Alert | None:
    """ANO-008: Battery critical — CRITICAL."""
    soc = float(row["battery_soc_pct"])
    if soc < BATT_CRIT_LO_PCT:
        return Alert(
            rule_id="ANO-008",
            severity="CRITICAL",
            category="battery",
            title="Battery state of charge critical — CRITICAL",
            message=(
                f"Battery SOC is {soc:.1f}%, below the critical threshold "
                f"of {BATT_CRIT_LO_PCT}%. Battery reserves nearly exhausted. "
                "Switch to grid import immediately."
            ),
            metric_name="battery_soc_pct",
            metric_value=round(soc, 2),
            threshold=BATT_CRIT_LO_PCT,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano009(row: pd.Series) -> Alert | None:
    """ANO-009: Battery over-charged — INFO."""
    soc = float(row["battery_soc_pct"])
    if soc > BATT_HIGH_PCT:
        return Alert(
            rule_id="ANO-009",
            severity="INFO",
            category="battery",
            title="Battery at high state of charge — INFO",
            message=(
                f"Battery SOC is {soc:.1f}%, above {BATT_HIGH_PCT}%. "
                "Consider exporting surplus energy or curtailing charging."
            ),
            metric_name="battery_soc_pct",
            metric_value=round(soc, 2),
            threshold=BATT_HIGH_PCT,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano010(row: pd.Series) -> Alert | None:
    """ANO-010: Solar underperformance — WARNING.

    Only evaluates when solar irradiance is above the minimum threshold
    (daytime, meaningful generation expected).
    """
    irr = float(row["solar_irradiance_wm2"])
    solar = float(row["solar_actual_mw"])

    if irr <= SOLAR_UNDERPERF_MIN_IRR:
        return None  # night-time or low-light — rule not applicable

    expected = (irr / 1000.0) * SOLAR_EFFICIENCY * SOLAR_CAPACITY_MW
    if expected <= 0:
        return None

    pr = solar / expected
    if pr < SOLAR_UNDERPERF_PR:
        return Alert(
            rule_id="ANO-010",
            severity="WARNING",
            category="solar",
            title="Solar PV underperformance — WARNING",
            message=(
                f"Solar performance ratio is {pr:.2f} (actual {solar:.1f} MW vs "
                f"expected {expected:.1f} MW at {irr:.0f} W/m² irradiance). "
                f"Threshold PR: {SOLAR_UNDERPERF_PR}. "
                "Possible soiling, shading, or inverter fault."
            ),
            metric_name="solar_pr",
            metric_value=round(pr, 4),
            threshold=SOLAR_UNDERPERF_PR,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano011(row: pd.Series) -> Alert | None:
    """ANO-011: Import approaching capacity limit — WARNING."""
    imp = float(row["grid_import_mw"])
    pct = imp / IMPORT_CAPACITY_MW
    # Only fire WARNING if not already CRITICAL
    if IMPORT_WARN_PCT <= pct < IMPORT_CRIT_PCT:
        return Alert(
            rule_id="ANO-011",
            severity="WARNING",
            category="import",
            title="Grid import near interconnection capacity — WARNING",
            message=(
                f"Grid import is {imp:.1f} MW ({pct*100:.1f}% of "
                f"{IMPORT_CAPACITY_MW} MW interconnection capacity). "
                "Reduce demand or increase local generation to avoid import limit breach."
            ),
            metric_name="grid_import_mw",
            metric_value=round(imp, 2),
            threshold=IMPORT_CAPACITY_MW * IMPORT_WARN_PCT,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano012(row: pd.Series) -> Alert | None:
    """ANO-012: Low renewable contribution — INFO."""
    demand = float(row["demand_mw"])
    solar = float(row["solar_actual_mw"])
    wind = float(row["wind_actual_mw"])
    re_pct = ((solar + wind) / demand * 100) if demand > 0 else 0.0
    if re_pct < RE_LOW_WARN_PCT:
        return Alert(
            rule_id="ANO-012",
            severity="INFO",
            category="renewables",
            title="Low renewable energy contribution — INFO",
            message=(
                f"Renewable generation is {re_pct:.1f}% of current demand "
                f"({solar:.1f} MW solar + {wind:.1f} MW wind out of {demand:.1f} MW demand). "
                f"Below {RE_LOW_WARN_PCT}% utilisation target."
            ),
            metric_name="renewable_pct",
            metric_value=round(re_pct, 2),
            threshold=RE_LOW_WARN_PCT,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano013(row: pd.Series) -> Alert | None:
    """ANO-013: Wind underperformance — WARNING."""
    ws = float(row["wind_speed_ms"])
    wind = float(row["wind_actual_mw"])

    if ws < WIND_UNDERPERF_MIN_SPEED or ws >= 25.0:
        return None

    if ws >= 12.0:
        frac = 1.0
    else:
        frac = (ws - 3.0) / (12.0 - 3.0)
        
    expected = frac * WIND_CAPACITY_MW
    if expected <= 0:
        return None

    pr = wind / expected
    if pr < WIND_UNDERPERF_PR:
        return Alert(
            rule_id="ANO-013",
            severity="WARNING",
            category="wind",
            title="Wind turbine underperformance — WARNING",
            message=(
                f"Wind performance ratio is {pr:.2f} (actual {wind:.1f} MW vs "
                f"expected {expected:.1f} MW at {ws:.1f} m/s wind speed). "
                f"Threshold PR: {WIND_UNDERPERF_PR}. "
                "Possible turbine fault or maintenance required."
            ),
            metric_name="wind_pr",
            metric_value=round(pr, 4),
            threshold=WIND_UNDERPERF_PR,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano014(row: pd.Series) -> Alert | None:
    """ANO-014: Renewable curtailment — INFO."""
    export = float(row["grid_export_mw"])
    if export >= CURTAILMENT_EXPORT_MW:
        return Alert(
            rule_id="ANO-014",
            severity="INFO",
            category="curtailment",
            title="Renewable curtailment active — INFO",
            message=(
                f"Grid export is {export:.1f} MW, near the interconnection limit. "
                "Excess renewable generation is likely being curtailed."
            ),
            metric_name="grid_export_mw",
            metric_value=round(export, 2),
            threshold=CURTAILMENT_EXPORT_MW,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano015(row: pd.Series) -> Alert | None:
    """ANO-015: Temperature extreme — WARNING."""
    temp = float(row["temperature_c"])
    if temp > TEMP_WARN_HI or temp < TEMP_WARN_LO:
        direction = "High" if temp > TEMP_WARN_HI else "Low"
        threshold = TEMP_WARN_HI if temp > TEMP_WARN_HI else TEMP_WARN_LO
        return Alert(
            rule_id="ANO-015",
            severity="WARNING",
            category="temperature",
            title=f"{direction} temperature extreme — WARNING",
            message=(
                f"Ambient temperature is {temp:.1f} °C, breaching the {direction.lower()} "
                f"warning threshold of {threshold} °C. Expect demand shifts and equipment stress."
            ),
            metric_name="temperature_c",
            metric_value=round(temp, 2),
            threshold=threshold,
            timestamp=str(row["timestamp"]),
        )
    return None


def _rule_ano016(row: pd.Series) -> Alert | None:
    """ANO-016: Grid import capacity risk — CRITICAL."""
    imp = float(row["grid_import_mw"])
    pct = imp / IMPORT_CAPACITY_MW
    if pct >= IMPORT_CRIT_PCT:
        return Alert(
            rule_id="ANO-016",
            severity="CRITICAL",
            category="import",
            title="Grid import capacity risk — CRITICAL",
            message=(
                f"Grid import is {imp:.1f} MW ({pct*100:.1f}% of "
                f"{IMPORT_CAPACITY_MW} MW interconnection capacity). "
                "Critical risk of cascading failure. Immediate load shedding required."
            ),
            metric_name="grid_import_mw",
            metric_value=round(imp, 2),
            threshold=IMPORT_CAPACITY_MW * IMPORT_CRIT_PCT,
            timestamp=str(row["timestamp"]),
        )
    return None


# ---------------------------------------------------------------------------
# Rule registry — order determines evaluation and output ordering
# ---------------------------------------------------------------------------
_RULES = [
    _rule_ano001,
    _rule_ano002,
    _rule_ano003,
    _rule_ano004,
    _rule_ano005,
    _rule_ano006,
    _rule_ano007,
    _rule_ano008,
    _rule_ano009,
    _rule_ano010,
    _rule_ano016,  # CRITICAL import checked before WARNING import
    _rule_ano011,
    _rule_ano012,
    _rule_ano013,
    _rule_ano014,
    _rule_ano015,
]

_SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_row(row: pd.Series) -> list[Alert]:
    """Evaluate all 12 rules against a single dataset row.

    Returns a list of triggered Alert objects, sorted by severity
    (CRITICAL first, then WARNING, then INFO).
    """
    alerts: list[Alert] = []
    for rule_fn in _RULES:
        alert = rule_fn(row)
        if alert is not None:
            alerts.append(alert)
    alerts.sort(key=lambda a: _SEVERITY_ORDER.get(a.severity, 99))
    return alerts


def get_active_alerts(window_rows: int = 1) -> list[Alert]:
    """Return alerts for the most recent *window_rows* rows of the dataset.

    With the default of 1, this reflects the current (latest simulated)
    grid state.  A larger window can be used to surface recent events.
    When multiple rows are evaluated, duplicate rule firings are deduplicated
    by rule_id, keeping the most-recent occurrence.
    """
    rows_df = get_latest_rows(n=window_rows)
    seen_rules: dict[str, Alert] = {}
    for _, row in rows_df.iterrows():
        for alert in evaluate_row(row):
            seen_rules[alert.rule_id] = alert  # last occurrence wins
    alerts = list(seen_rules.values())
    alerts.sort(key=lambda a: _SEVERITY_ORDER.get(a.severity, 99))
    return alerts
