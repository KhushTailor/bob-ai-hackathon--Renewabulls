"""
72-Hour What-If & Action Generator (Simulator).

Deterministic decision-support simulator that evaluates proposed actions
across a 72-hour forecast horizon.

Battery Energy Model:
- Physical Capacity: 80.0 MWh
- Maximum Power: 40.0 MW (charge/discharge)
- Operational Reserve Bounds: 5.0% (4.0 MWh) to 95.0% (76.0 MWh)
- Timestep: 15 minutes (dt_h = 0.25 hours)
- Energy per timestep: energy_change_mwh = power_mw * dt_h
- SOC calculation: SOC% = (stored_energy_mwh / capacity_mwh) * 100%

Scoring Formula (Max 100 points):
- Grid/Stability Impact (35%): Penalizes interconnection limit violations or load shedding.
- Renewable Utilisation (30%): Penalizes curtailed renewable energy.
- Operational Cost (20%): Evaluates import costs vs export revenue.
- Operational Risk (15%): Penalizes dangerous Battery SOC boundaries (<5% or >95%).

Ranking:
- Feasible scenarios (is_feasible == True) always rank ahead of infeasible scenarios.
- Within each feasibility tier, scenarios are ranked by score descending.
"""
from __future__ import annotations

import pandas as pd

from backend.services.forecaster import get_demand_forecast
from backend.services.data_loader import get_latest_rows

# Grid asset constraints
BATTERY_CAPACITY_MWH: float = 80.0
BATTERY_MAX_MW: float = 40.0
BATTERY_MIN_SOC_PCT: float = 5.0
BATTERY_MAX_SOC_PCT: float = 95.0
IMPORT_CAPACITY_MW: float = 180.0
EXPORT_CAPACITY_MW: float = 60.0


def evaluate_scenarios(scenarios: list[dict]) -> list[dict]:
    """Evaluate multiple scenarios and rank them deterministically.
    
    Feasible scenarios always rank above infeasible scenarios.
    """
    # 1. Fetch 72-h demand forecast (288 points)
    forecast_data = get_demand_forecast(horizon_hours=72)
    demand_points = forecast_data["points"]
    steps = len(demand_points)
    
    # 2. Fetch history for renewable forecast & initial state
    history = get_latest_rows(n=672)  # 1 week lookback
    if history.empty:
        raise ValueError("Insufficient dataset for simulation.")
    
    initial_soc = float(history.iloc[-1]["battery_soc_pct"])
    
    results = []
    
    for idx, scen in enumerate(scenarios):
        res = _simulate_scenario(
            scenario_id=f"SCEN-{idx+1}",
            action=scen["action"],
            amount_mw=scen["amount_mw"],
            duration_hours=scen.get("duration_hours", 1.0),
            demand_points=demand_points,
            history=history,
            initial_soc=initial_soc,
            steps=steps,
        )
        results.append(res)
        
    # Rank: feasible ALWAYS beats infeasible, then highest score
    results.sort(key=lambda x: (x["is_feasible"], x["score"]), reverse=True)
    return results


def _simulate_scenario(
    scenario_id: str,
    action: str,
    amount_mw: float,
    duration_hours: float,
    demand_points: list[dict],
    history: pd.DataFrame,
    initial_soc: float,
    steps: int,
) -> dict:
    dt_h = 0.25  # 15 minutes per timestep
    action_steps = int(round(duration_hours / dt_h))
    if action_steps <= 0:
        action_steps = 1
        
    # Aggregates tracked over the ACTION window
    agg = {
        "orig_demand": 0.0,
        "adj_demand": 0.0,
        "orig_import": 0.0,
        "adj_import": 0.0,
        "orig_export": 0.0,
        "adj_export": 0.0,
        "ren_gen": 0.0,
        "curtailed": 0.0,
    }
    
    # 72-hour state tracking
    soc = initial_soc
    soc_after_action = initial_soc
    violations = set()
    total_cost = 0.0
    total_ren = 0.0
    total_curtailed = 0.0
    
    total_applied = 0.0
    total_unmet = 0.0
    
    history_len = len(history)
    week_rows = 672
    
    for i in range(steps):
        # 1. Base forecast values
        orig_dem = float(demand_points[i]["predicted_demand_mw"])
        
        # Renewable seasonal naive lookup (1 week prior)
        if history_len >= week_rows:
            hist_idx = history_len - week_rows + (i % week_rows)
        else:
            hist_idx = history_len - 1
            
        orig_sol = float(history.iloc[hist_idx]["solar_actual_mw"])
        orig_win = float(history.iloc[hist_idx]["wind_actual_mw"])
        ren_avail = orig_sol + orig_win
        
        # 2. Apply Action modifiers if within action duration
        adj_dem = orig_dem
        adj_ren = ren_avail
        forced_import = 0.0
        forced_batt_mw = 0.0
        curtailed = 0.0
        
        in_action = (i < action_steps)
        
        if in_action:
            if action == "LOAD_SHIFT":
                adj_dem = max(0.0, orig_dem - amount_mw)
                applied = orig_dem - adj_dem
                unmet = amount_mw - applied
                total_applied += applied
                total_unmet += unmet
                
            elif action == "RENEWABLE_CURTAILMENT":
                applied = min(max(0.0, amount_mw), ren_avail)
                unmet = amount_mw - applied
                adj_ren = ren_avail - applied
                total_applied += applied
                total_unmet += unmet
                curtailed += applied
                total_curtailed += applied
                
            elif action == "GRID_IMPORT":
                applied = min(amount_mw, IMPORT_CAPACITY_MW)
                unmet = amount_mw - applied
                if amount_mw > IMPORT_CAPACITY_MW:
                    violations.add("IMPORT_LIMIT_EXCEEDED")
                forced_import = applied
                total_applied += applied
                total_unmet += unmet
                
            elif action == "BATTERY_DISPATCH":
                current_energy_mwh = (soc / 100.0) * BATTERY_CAPACITY_MWH
                if amount_mw >= 0:
                    # Discharge: maintain >= 5% reserve
                    avail_energy_mwh = max(0.0, current_energy_mwh - (BATTERY_MIN_SOC_PCT / 100.0 * BATTERY_CAPACITY_MWH))
                    max_power = min(BATTERY_MAX_MW, avail_energy_mwh / dt_h)
                    applied = min(amount_mw, max_power)
                    unmet = amount_mw - applied
                else:
                    # Charge: maintain <= 95% reserve
                    space_energy_mwh = max(0.0, (BATTERY_MAX_SOC_PCT / 100.0 * BATTERY_CAPACITY_MWH) - current_energy_mwh)
                    max_power = min(BATTERY_MAX_MW, space_energy_mwh / dt_h)
                    applied = max(amount_mw, -max_power)
                    unmet = abs(amount_mw) - abs(applied)
                    
                forced_batt_mw = applied
                total_applied += abs(applied)
                total_unmet += abs(unmet)
                
        # 3. Grid Balance
        net_load = adj_dem - adj_ren - forced_import - forced_batt_mw
        
        batt_dispatch = forced_batt_mw
        grid_imp = forced_import
        grid_exp = 0.0
        
        # Grid balancing
        if net_load > 0:
            # First, draw from grid import up to capacity
            imp_need = min(net_load, IMPORT_CAPACITY_MW - grid_imp)
            if imp_need > 0:
                grid_imp += imp_need
                net_load -= imp_need
                
            # Next, if not already performing a forced BATTERY_DISPATCH action, use battery for peaking
            if not (in_action and action == "BATTERY_DISPATCH"):
                batt_need = min(net_load, BATTERY_MAX_MW - batt_dispatch)
                if batt_need > 0:
                    current_energy = (soc / 100.0) * BATTERY_CAPACITY_MWH
                    avail_mwh = max(0.0, current_energy - (BATTERY_MIN_SOC_PCT / 100.0 * BATTERY_CAPACITY_MWH))
                    actual_batt_mw = min(batt_need, avail_mwh / dt_h)
                    if actual_batt_mw > 0:
                        batt_dispatch += actual_batt_mw
                        net_load -= actual_batt_mw
            
            if net_load > 0.1:
                violations.add("LOAD_SHED_REQUIRED")
                total_cost += net_load * dt_h * 1000.0  # Costly outage penalty
                
        elif net_load < 0:
            excess = -net_load
            
            # If not in BATTERY_DISPATCH, store excess in battery up to 95% reserve
            if not (in_action and action == "BATTERY_DISPATCH"):
                batt_room = max(0.0, BATTERY_MAX_MW + batt_dispatch)
                if batt_room > 0:
                    current_energy = (soc / 100.0) * BATTERY_CAPACITY_MWH
                    space_mwh = max(0.0, (BATTERY_MAX_SOC_PCT / 100.0 * BATTERY_CAPACITY_MWH) - current_energy)
                    actual_charge_mw = min(excess, space_mwh / dt_h, batt_room)
                    if actual_charge_mw > 0:
                        batt_dispatch -= actual_charge_mw
                        excess -= actual_charge_mw
            
            # Export remaining excess to grid
            exp_room = max(0.0, EXPORT_CAPACITY_MW - grid_exp)
            actual_exp = min(excess, exp_room)
            grid_exp += actual_exp
            excess -= actual_exp
            
            if excess > 0.1:
                curtailed += excess
                total_curtailed += excess
                total_cost += excess * dt_h * 20.0  # Curtailment loss penalty

        # 4. Update Battery Energy & SOC
        energy_change_mwh = batt_dispatch * dt_h
        current_energy_mwh = (soc / 100.0) * BATTERY_CAPACITY_MWH
        new_energy_mwh = max(0.0, min(BATTERY_CAPACITY_MWH, current_energy_mwh - energy_change_mwh))
        soc = (new_energy_mwh / BATTERY_CAPACITY_MWH) * 100.0
        
        # 5. Constraints check
        if grid_imp > IMPORT_CAPACITY_MW + 0.01:
            violations.add("IMPORT_LIMIT_EXCEEDED")
        if soc < BATTERY_MIN_SOC_PCT - 0.01:
            violations.add("BATTERY_CRITICAL_LOW")
        elif soc > BATTERY_MAX_SOC_PCT + 0.01:
            violations.add("BATTERY_CRITICAL_HIGH")
            
        # Costs & Aggregates
        total_cost += (grid_imp * dt_h * 50.0)
        total_cost -= (grid_exp * dt_h * 20.0)
        total_cost += (abs(batt_dispatch) * dt_h * 5.0)
        total_ren += ren_avail
        
        if in_action:
            agg["orig_demand"] += orig_dem
            agg["adj_demand"] += adj_dem
            agg["orig_import"] += max(0.0, orig_dem - ren_avail)
            agg["adj_import"] += grid_imp
            agg["orig_export"] += max(0.0, ren_avail - orig_dem)
            agg["adj_export"] += grid_exp
            agg["ren_gen"] += ren_avail
            agg["curtailed"] += curtailed
            
        if i == action_steps - 1:
            soc_after_action = soc
            
    # Feasibility check
    is_feasible = True
    if total_unmet > 0.01:
        is_feasible = False
    if "IMPORT_LIMIT_EXCEEDED" in violations or "LOAD_SHED_REQUIRED" in violations:
        is_feasible = False
    if "BATTERY_CRITICAL_LOW" in violations or "BATTERY_CRITICAL_HIGH" in violations:
        is_feasible = False

    # Calculate Scoring (0-100)
    score = 100.0
    
    # Grid/stability impact (35%)
    if "IMPORT_LIMIT_EXCEEDED" in violations or "LOAD_SHED_REQUIRED" in violations:
        score -= 35.0
        
    # Renewable Utilisation (30%)
    if total_ren > 0:
        util_pct = 1.0 - (total_curtailed / total_ren)
        score -= (1.0 - util_pct) * 30.0
        
    # Operational Cost (20%) — baseline cost approx $30k over 72h
    norm_cost = min(1.0, max(0.0, total_cost / 30000.0))
    score -= (norm_cost * 20.0)
    
    # Operational Risk (15%)
    if "BATTERY_CRITICAL_LOW" in violations or "BATTERY_CRITICAL_HIGH" in violations:
        score -= 15.0
        
    score = max(0.0, round(score, 1))
    
    risk_sev = "LOW"
    if score < 50:
        risk_sev = "CRITICAL"
    elif score < 70:
        risk_sev = "HIGH"
    elif score < 85:
        risk_sev = "MEDIUM"
    
    explanation = "Scenario evaluated successfully."
    if not is_feasible:
        explanation = "Scenario is infeasible (violates operational bounds, physical limits, or load shedding required)."

    return {
        "scenario_id": scenario_id,
        "action": action,
        "amount_mw": amount_mw,
        "duration_hours": duration_hours,
        "is_feasible": is_feasible,
        "explanation": explanation,
        
        "applied_action_mw": round(total_applied / action_steps, 2),
        "unmet_action_mw": round(total_unmet / action_steps, 2),
        
        # Averages over action duration
        "original_demand_mw": round(agg["orig_demand"] / action_steps, 2),
        "adjusted_demand_mw": round(agg["adj_demand"] / action_steps, 2),
        "battery_soc_before_pct": round(initial_soc, 2),
        "battery_soc_after_pct": round(soc_after_action, 2),
        "original_grid_import_mw": round(agg["orig_import"] / action_steps, 2),
        "adjusted_grid_import_mw": round(agg["adj_import"] / action_steps, 2),
        "original_grid_export_mw": round(agg["orig_export"] / action_steps, 2),
        "adjusted_grid_export_mw": round(agg["adj_export"] / action_steps, 2),
        "renewable_generation_mw": round(agg["ren_gen"] / action_steps, 2),
        "renewable_utilisation_pct": round(100.0 - (agg["curtailed"] / max(0.1, agg["ren_gen"]) * 100.0), 1),
        "curtailed_mw": round(agg["curtailed"] / action_steps, 2),
        
        # 72h
        "estimated_cost": round(total_cost, 2),
        "constraint_violations": sorted(list(violations)),
        "risk_severity": risk_sev,
        "score": score,
    }
