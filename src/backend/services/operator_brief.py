"""
AI Operator Brief Service — Stage S9.

Translates the current GridPulse operational state into a concise, high-value,
operator-facing brief answering six core operational questions:
  1. What is happening now? (situation)
  2. What is the likely cause? (likely_cause)
  3. What is the main risk? (main_risk)
  4. What action is recommended? (recommended_action)
  5. Why is that action recommended? (rationale)
  6. What could happen if no action is taken? (consequence_if_ignored)

Grounding & Guardrails:
- Pure decision-support assistant: does not claim autonomous grid control or physical switching.
- Deterministic Jinja2 template fallback: operates 100% offline without IBM credentials.
- Optional IBM watsonx.ai enhancement: attempts Granite Instruct if configured, with graceful fallback.
"""
from __future__ import annotations

import json
import logging
from typing import Any
import pandas as pd
from jinja2 import Template

from backend import config
from backend.services.data_loader import get_latest_rows
from backend.services.anomaly_engine import get_active_alerts, Alert
from backend.services.renewables import get_renewable_metrics
from backend.services.forecaster import get_demand_forecast
from backend.services.simulator import evaluate_scenarios

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Jinja2 Deterministic Brief Templates
# ---------------------------------------------------------------------------

TEMPLATES = {
    # 1. High Interconnection Import (Critical or Warning)
    "IMPORT_ALERT": {
        "situation": Template(
            "Grid import is currently at {{ status.grid_import_mw }} MW ({{ import_pct }}% of {{ import_cap }} MW capacity). "
            "System demand is {{ status.demand_mw }} MW with local renewables supplying {{ status.total_renewable_mw }} MW "
            "({{ status.renewable_pct }}% of demand). Battery SOC is {{ status.battery_soc_pct }}%."
        ),
        "likely_cause": Template(
            "High net load ({{ net_load }} MW) driven by regional demand ({{ status.demand_mw }} MW) "
            "exceeding local generation (solar: {{ status.solar_actual_mw }} MW, wind: {{ status.wind_actual_mw }} MW), "
            "forcing heavy reliance on the primary interconnection tie-line."
        ),
        "main_risk": Template(
            "Exceeding the {{ import_cap }} MW interconnection limit risks triggering protective line overcurrent relays, "
            "intertie disconnect, and cascading local power deficits."
        ),
        "recommended_action": Template(
            "Execute {{ rec_action }} to immediately relieve tie-line stress below 160.0 MW."
        ),
        "rationale": Template(
            "Simulated dispatch reduces grid import by {{ sim_relief }} MW, restoring a stable operational buffer "
            "while maintaining battery storage above the 5.0% safety floor."
        ),
        "consequence_if_ignored": Template(
            "Unchecked import will breach the {{ import_cap }} MW physical limit, causing an emergency breaker trip "
            "and forced under-frequency load shedding across local distribution feeders."
        ),
    },

    # 2. Battery Storage Critical / Low
    "BATTERY_ALERT": {
        "situation": Template(
            "Battery state of charge is {{ status.battery_soc_pct }}%, operating below the {{ batt_threshold }}% threshold. "
            "Current usable reserve is {{ usable_mwh }} MWh out of 80.0 MWh total capacity. Demand is {{ status.demand_mw }} MW."
        ),
        "likely_cause": Template(
            "Sustained battery discharge to satisfy peak net load during periods of low local renewable generation, "
            "without sufficient subsequent recharge opportunities."
        ),
        "main_risk": Template(
            "Depletion of fast-acting battery storage leaves the balancing area vulnerable to unexpected generator trips, "
            "frequency transients, and loss of synthetic inertia."
        ),
        "recommended_action": Template(
            "Suspend battery discharge and initiate demand-side load shifting ({{ rec_action }}) to stabilize battery SOC."
        ),
        "rationale": Template(
            "Halting discharge preserves remaining storage buffer, protects battery cell health, and keeps emergency "
            "fast-frequency response capability on standby."
        ),
        "consequence_if_ignored": Template(
            "Battery will exhaust its remaining reserves, entering a critical lockout state with zero emergency peaking capacity."
        ),
    },

    # 3. Renewable Underperformance
    "RENEWABLE_ALERT": {
        "situation": Template(
            "Local renewable generation is underperforming expectations. Solar is delivering {{ solar.actual_generation_mw }} MW "
            "vs {{ solar.expected_generation_mw }} MW expected (PR: {{ solar_pr }}%), and wind is generating {{ wind.actual_generation_mw }} MW "
            "vs {{ wind.expected_generation_mw }} MW expected (PR: {{ wind_pr }}%). Total renewable output is {{ status.total_renewable_mw }} MW."
        ),
        "likely_cause": Template(
            "Localized atmospheric shading, cloud cover, or aerodynamic turbulence reducing photovoltaic and turbine efficiency "
            "below seasonal baseline projections."
        ),
        "main_risk": Template(
            "A {{ deficit_mw }} MW renewable deficit widens the supply gap, driving unplanned grid import surges and "
            "hastening battery depletion."
        ),
        "recommended_action": Template(
            "Increase scheduled grid import or dispatch {{ rec_action }} to smoothly compensate for the {{ deficit_mw }} MW shortfall."
        ),
        "rationale": Template(
            "Compensating through scheduled flexibility avoids rapid reserve depletion and stabilizes the supply balance."
        ),
        "consequence_if_ignored": Template(
            "Continued uncompensated renewable shortfalls will drain battery storage and push grid imports toward interconnection capacity limits."
        ),
    },

    # 4. Grid Frequency Excursion / Drift
    "FREQUENCY_ALERT": {
        "situation": Template(
            "Grid frequency has drifted to {{ status.frequency_hz }} Hz, a deviation of {{ freq_dev }} Hz from nominal 50.00 Hz "
            "(operational limit: ±{{ freq_thresh }} Hz). System load is {{ status.demand_mw }} MW."
        ),
        "likely_cause": Template(
            "Active power imbalance between total generation and instantaneous consumer load across the regional balancing authority."
        ),
        "main_risk": Template(
            "Frequency divergence destabilizes synchronized generators and risks automated relay-driven under-frequency load shedding."
        ),
        "recommended_action": Template(
            "Deploy fast battery active-power response ({{ batt_resp }}) to arrest frequency deviation and restore 50.00 Hz nominal."
        ),
        "rationale": Template(
            "Battery energy storage responds in under 200 ms, providing the fastest primary frequency control to arrest grid frequency decay."
        ),
        "consequence_if_ignored": Template(
            "Sustained under-frequency will trigger statutory Under-Frequency Load Shedding (UFLS), disconnecting customer distribution circuits."
        ),
    },

    # 5. Grid Voltage Excursion
    "VOLTAGE_ALERT": {
        "situation": Template(
            "Grid bus voltage is at {{ status.voltage_pu }} pu, exceeding the statutory tolerance boundary of {{ volt_thresh }} pu. "
            "Current feeder loading is {{ status.demand_mw }} MW."
        ),
        "likely_cause": Template(
            "Reactive power imbalance or excessive line loading on distribution transformers during high-transfer conditions."
        ),
        "main_risk": Template(
            "Off-nominal voltage degrades power quality, stresses substation insulation, and risks tripping industrial loads."
        ),
        "recommended_action": Template(
            "Command solar inverters into dynamic reactive power (VAR) support mode and throttle feeder demand."
        ),
        "rationale": Template(
            "Inverter Volt-VAR control provides local voltage correction without mechanical tap changer wear."
        ),
        "consequence_if_ignored": Template(
            "Voltage collapse on downstream distribution feeders, triggering automated over/under-voltage protection lockouts."
        ),
    },

    # 6. High Curtailment / Surplus
    "CURTAILMENT_ALERT": {
        "situation": Template(
            "Surplus renewable generation has driven grid export to {{ status.grid_export_mw }} MW, near the 60.0 MW export limit. "
            "Renewables are supplying {{ status.total_renewable_mw }} MW against a demand of {{ status.demand_mw }} MW."
        ),
        "likely_cause": Template(
            "Midday renewable generation peak combined with full battery storage ({{ status.battery_soc_pct }}% SOC) and saturated local demand."
        ),
        "main_risk": Template(
            "Exceeding the 60.0 MW export limit risks reverse-power breaker trips and wasted green energy through forced curtailment."
        ),
        "recommended_action": Template(
            "Incentivize demand response load absorption or apply controlled renewable curtailment of {{ rec_curtail }} MW."
        ),
        "rationale": Template(
            "Controlled curtailment prevents uncontrolled reverse-power feeder protection trips while maximizing green energy export."
        ),
        "consequence_if_ignored": Template(
            "Automatic reverse-power relay trips will abruptly disconnect export circuits, causing severe local overvoltage."
        ),
    },

    # 7. Nominal Stable State
    "NOMINAL": {
        "situation": Template(
            "The grid is operating under nominal, stable conditions. System demand is {{ status.demand_mw }} MW, supported by "
            "{{ status.total_renewable_mw }} MW of renewable generation ({{ status.renewable_pct }}% of demand). "
            "Grid frequency is stable at {{ status.frequency_hz }} Hz, voltage is {{ status.voltage_pu }} pu, "
            "and battery SOC is healthy at {{ status.battery_soc_pct }}%."
        ),
        "likely_cause": Template(
            "Balanced active and reactive power flows between local renewable resources (solar: {{ status.solar_actual_mw }} MW, "
            "wind: {{ status.wind_actual_mw }} MW), scheduled interconnection import ({{ status.grid_import_mw }} MW), and steady demand."
        ),
        "main_risk": Template(
            "Upcoming diurnal demand peak: 72-hour forecast projects peak demand reaching {{ forecast.peak_demand_mw }} MW "
            "(next 4 hours peak: {{ forecast.next_4h_peak_mw }} MW), which will tighten reserve margins."
        ),
        "recommended_action": Template(
            "Maintain current economic dispatch. Pre-charge battery during upcoming surplus windows to prepare for evening peak demand."
        ),
        "rationale": Template(
            "Pre-charging during high-renewable periods preserves low operating costs and ensures full flexibility during peak hours."
        ),
        "consequence_if_ignored": Template(
            "Failure to optimize storage timing will increase exposure to peak import tariffs and reduce reserve margins during demand spikes."
        ),
    },
}


# ---------------------------------------------------------------------------
# Helper: Extract context for template rendering
# ---------------------------------------------------------------------------

def _build_context(
    row: dict,
    alerts: list[Alert],
    renewables: dict,
    forecast: dict,
) -> tuple[str, str, dict]:
    """Analyze the operational state and return (dominant_scenario, severity, context)."""
    # 1. Classify dominant scenario and severity
    critical_alerts = [a for a in alerts if a.severity == "CRITICAL"]
    warning_alerts = [a for a in alerts if a.severity == "WARNING"]
    info_alerts = [a for a in alerts if a.severity == "INFO"]
    
    severity = "NOMINAL"
    dominant_key = "NOMINAL"

    if critical_alerts:
        severity = "CRITICAL"
        # Prioritize critical alerts
        rule_ids = {a.rule_id for a in critical_alerts}
        if "ANO-001" in rule_ids:
            dominant_key = "FREQUENCY_ALERT"
        elif "ANO-004" in rule_ids:
            dominant_key = "VOLTAGE_ALERT"
        elif "ANO-016" in rule_ids:
            dominant_key = "IMPORT_ALERT"
        elif "ANO-008" in rule_ids:
            dominant_key = "BATTERY_ALERT"
        else:
            dominant_key = "IMPORT_ALERT"
            
    elif warning_alerts:
        severity = "WARNING"
        rule_ids = {a.rule_id for a in warning_alerts}
        if "ANO-011" in rule_ids or float(row.get("grid_import_mw", 0)) >= 162.0:
            dominant_key = "IMPORT_ALERT"
        elif "ANO-007" in rule_ids or float(row.get("battery_soc_pct", 50)) < 15.0:
            dominant_key = "BATTERY_ALERT"
        elif "ANO-009" in rule_ids or "ANO-010" in rule_ids or renewables.get("solar", {}).get("underperforming") or renewables.get("wind", {}).get("underperforming"):
            dominant_key = "RENEWABLE_ALERT"
        elif "ANO-002" in rule_ids:
            dominant_key = "FREQUENCY_ALERT"
        elif "ANO-003" in rule_ids:
            dominant_key = "VOLTAGE_ALERT"
        elif "ANO-014" in rule_ids:
            dominant_key = "CURTAILMENT_ALERT"
        else:
            dominant_key = "IMPORT_ALERT"
            
    elif info_alerts:
        severity = "INFO"
        rule_ids = {a.rule_id for a in info_alerts}
        if "ANO-009" in rule_ids or float(row.get("grid_export_mw", 0)) > 50.0:
            dominant_key = "CURTAILMENT_ALERT"
        else:
            dominant_key = "NOMINAL"
            
    # Check renewable underperformance even if not in alerts list
    elif renewables.get("solar", {}).get("underperforming") or renewables.get("wind", {}).get("underperforming"):
        severity = "WARNING"
        dominant_key = "RENEWABLE_ALERT"

    # 2. Compute numeric context values
    demand_mw = float(row.get("demand_mw", 200.0))
    solar_actual_mw = float(row.get("solar_actual_mw", 0.0))
    wind_actual_mw = float(row.get("wind_actual_mw", 0.0))
    total_renewable_mw = round(solar_actual_mw + wind_actual_mw, 2)
    renewable_pct = round((total_renewable_mw / demand_mw * 100.0), 1) if demand_mw > 0 else 0.0
    grid_import_mw = float(row.get("grid_import_mw", 0.0))
    import_cap = 180.0
    import_pct = round((grid_import_mw / import_cap * 100.0), 1)
    
    soc_pct = float(row.get("battery_soc_pct", 50.0))
    usable_mwh = max(0.0, round((soc_pct - 5.0) / 100.0 * 80.0, 1))
    
    solar_info = renewables.get("solar", {})
    wind_info = renewables.get("wind", {})
    solar_pr = round(float(solar_info.get("performance_ratio", 1.0)) * 100.0, 1)
    wind_pr = round(float(wind_info.get("performance_ratio", 1.0)) * 100.0, 1)
    deficit_mw = round(
        max(0.0, float(solar_info.get("expected_generation_mw", 0)) - solar_actual_mw) +
        max(0.0, float(wind_info.get("expected_generation_mw", 0)) - wind_actual_mw),
        1
    )
    
    freq_hz = float(row.get("frequency_hz", 50.0))
    freq_dev = round(freq_hz - 50.0, 3)
    freq_thresh = 0.5 if severity == "CRITICAL" else 0.2
    
    volt_pu = float(row.get("voltage_pu", 1.0))
    volt_thresh = "0.90 / 1.10" if severity == "CRITICAL" else "0.95 / 1.05"
    
    forecast_points = forecast.get("points", [])
    if forecast_points:
        peak_demand_mw = round(max(p["predicted_demand_mw"] for p in forecast_points), 1)
        next_4h_peak_mw = round(max(p["predicted_demand_mw"] for p in forecast_points[:16]), 1)
    else:
        peak_demand_mw = demand_mw
        next_4h_peak_mw = demand_mw

    # Dynamic simulated recommendations
    rec_action = "20.0 MW Battery Dispatch for 1 hour"
    sim_relief = 20.0
    if dominant_key == "IMPORT_ALERT":
        if soc_pct > 20.0:
            rec_action = "20.0 MW Battery Dispatch for 1 hour"
            sim_relief = 20.0
        else:
            rec_action = "25.0 MW Load Shift for 2 hours"
            sim_relief = 25.0
    elif dominant_key == "BATTERY_ALERT":
        rec_action = "15.0 MW Demand Load Shift for 2 hours"
        sim_relief = 15.0
    elif dominant_key == "RENEWABLE_ALERT":
        rec_action = f"{max(10.0, deficit_mw)} MW Load Shift or Import Reserve"
        sim_relief = deficit_mw

    context = {
        "status": {
            "demand_mw": round(demand_mw, 2),
            "solar_actual_mw": round(solar_actual_mw, 2),
            "wind_actual_mw": round(wind_actual_mw, 2),
            "total_renewable_mw": total_renewable_mw,
            "renewable_pct": renewable_pct,
            "grid_import_mw": round(grid_import_mw, 2),
            "grid_export_mw": round(float(row.get("grid_export_mw", 0.0)), 2),
            "battery_soc_pct": round(soc_pct, 1),
            "frequency_hz": round(freq_hz, 4),
            "voltage_pu": round(volt_pu, 4),
            "timestamp": str(row.get("timestamp", "")),
        },
        "solar": solar_info,
        "wind": wind_info,
        "forecast": {
            "peak_demand_mw": peak_demand_mw,
            "next_4h_peak_mw": next_4h_peak_mw,
        },
        "import_cap": import_cap,
        "import_pct": import_pct,
        "net_load": round(demand_mw - total_renewable_mw, 2),
        "batt_threshold": 5.0 if severity == "CRITICAL" else 15.0,
        "usable_mwh": usable_mwh,
        "solar_pr": solar_pr,
        "wind_pr": wind_pr,
        "deficit_mw": deficit_mw,
        "freq_dev": freq_dev,
        "freq_thresh": freq_thresh,
        "volt_thresh": volt_thresh,
        "batt_resp": "discharge 10 MW" if freq_dev < 0 else "charge 10 MW",
        "rec_action": rec_action,
        "sim_relief": sim_relief,
        "rec_curtail": round(float(row.get("grid_export_mw", 0.0)) - 55.0, 1) if float(row.get("grid_export_mw", 0.0)) > 55.0 else 10.0,
    }

    return dominant_key, severity, context


# ---------------------------------------------------------------------------
# watsonx.ai integration (optional enhancement)
# ---------------------------------------------------------------------------

def _try_watsonx_generation(context: dict, dominant_key: str, severity: str) -> dict | None:
    """Attempt brief generation via IBM watsonx.ai if configured and installed."""
    if not (config.WATSONX_BRIEF_ENABLED and config.WATSONX_API_KEY and config.WATSONX_PROJECT_ID):
        return None

    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        credentials = {
            "url": config.WATSONX_URL,
            "apikey": config.WATSONX_API_KEY,
        }
        model = ModelInference(
            model_id="ibm/granite-3-3-8b-instruct",
            credentials=credentials,
            project_id=config.WATSONX_PROJECT_ID,
            params={
                GenParams.MAX_NEW_TOKENS: 600,
                GenParams.TEMPERATURE: 0.1,
            },
        )
        prompt = (
            "You are an electricity-grid operations decision-support assistant. "
            "Do not claim to control physical grid equipment. "
            "Do not invent measurements, events, causes, or actions that are not supported by the supplied data.\n\n"
            f"Operational State: {json.dumps(context['status'])}\n"
            f"Dominant Situation: {dominant_key}, Severity: {severity}\n\n"
            "Produce a JSON object with keys: situation, likely_cause, main_risk, "
            "recommended_action, rationale, consequence_if_ignored."
        )
        raw_output = model.generate_text(prompt=prompt)
        parsed = json.loads(raw_output)
        required_keys = {"situation", "likely_cause", "main_risk", "recommended_action", "rationale", "consequence_if_ignored"}
        if required_keys.issubset(parsed.keys()):
            parsed["severity"] = severity
            parsed["generated_by"] = "watsonx-granite"
            parsed["timestamp"] = context["status"]["timestamp"]
            return parsed
    except Exception as exc:
        logger.warning(f"watsonx.ai generation unavailable or failed: {exc}. Using deterministic fallback.")

    return None


# ---------------------------------------------------------------------------
# Main Service Entrypoint
# ---------------------------------------------------------------------------

def generate_operator_brief(
    row: pd.Series | dict | None = None,
    alerts: list[Alert] | None = None,
    renewables: dict | None = None,
    forecast: dict | None = None,
) -> dict:
    """Generate a structured, deterministic AI Operator Brief.

    Uses real data from the status, alerts, renewables, forecast, and simulation services.
    Falls back gracefully to deterministic Jinja2 templates without credentials.
    """
    # 1. Fetch live service data if not passed in
    if row is None:
        latest_df = get_latest_rows(1)
        if latest_df.empty:
            raise ValueError("No grid data available to generate operator brief.")
        row_dict = latest_df.iloc[-1].to_dict()
    elif isinstance(row, pd.Series):
        row_dict = row.to_dict()
    else:
        row_dict = dict(row)

    if alerts is None:
        alerts = get_active_alerts()

    if renewables is None:
        renewables = get_renewable_metrics()

    if forecast is None:
        forecast = get_demand_forecast(horizon_hours=72)

    # 2. Build template context and classify dominant situation
    dominant_key, severity, context = _build_context(row_dict, alerts, renewables, forecast)

    # 3. Attempt watsonx.ai if enabled; fallback to deterministic template
    watsonx_result = _try_watsonx_generation(context, dominant_key, severity)
    if watsonx_result is not None:
        return watsonx_result

    # 4. Render Deterministic Jinja2 Template Fallback
    tpl_group = TEMPLATES.get(dominant_key, TEMPLATES["NOMINAL"])
    
    return {
        "timestamp": str(row_dict.get("timestamp", "")),
        "situation": tpl_group["situation"].render(**context),
        "likely_cause": tpl_group["likely_cause"].render(**context),
        "main_risk": tpl_group["main_risk"].render(**context),
        "recommended_action": tpl_group["recommended_action"].render(**context),
        "rationale": tpl_group["rationale"].render(**context),
        "consequence_if_ignored": tpl_group["consequence_if_ignored"].render(**context),
        "severity": severity,
        "generated_by": "template-fallback",
    }
