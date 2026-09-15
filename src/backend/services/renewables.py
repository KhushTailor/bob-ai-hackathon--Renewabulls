"""
Renewable Performance Monitoring Service.

Evaluates the latest grid state and calculates meaningful renewable KPIs for:
- Solar (expected vs actual, performance ratio, underperformance)
- Wind (expected vs actual, performance ratio, underperformance)
- Combined (total renewables, % of demand, curtailment)
"""
from __future__ import annotations

import pandas as pd

from backend.services.data_loader import get_latest_rows
from backend.services.anomaly_engine import (
    SOLAR_CAPACITY_MW,
    SOLAR_EFFICIENCY,
    SOLAR_UNDERPERF_MIN_IRR,
    SOLAR_UNDERPERF_PR,
    WIND_CAPACITY_MW,
    WIND_UNDERPERF_MIN_SPEED,
    WIND_UNDERPERF_PR,
    CURTAILMENT_EXPORT_MW,
)


def get_renewable_metrics() -> dict:
    """Calculate renewable performance metrics for the current grid state."""
    # Get the latest row
    df = get_latest_rows(n=1)
    if df.empty:
        raise ValueError("Dataset is empty.")
    
    row = df.iloc[0]
    
    # Extract raw data
    demand_mw = float(row["demand_mw"])
    solar_actual_mw = float(row["solar_actual_mw"])
    wind_actual_mw = float(row["wind_actual_mw"])
    irr = float(row["solar_irradiance_wm2"])
    ws = float(row["wind_speed_ms"])
    export = float(row["grid_export_mw"])
    
    # ---------------------------------------------------------
    # Solar Metrics
    # ---------------------------------------------------------
    solar_expected_mw = (irr / 1000.0) * SOLAR_EFFICIENCY * SOLAR_CAPACITY_MW
    
    if solar_expected_mw > 0:
        solar_pr = solar_actual_mw / solar_expected_mw
    else:
        solar_pr = 1.0  # At night, PR is 1.0 (or undefined, we use 1.0 as healthy)
        
    solar_underperforming = False
    if irr > SOLAR_UNDERPERF_MIN_IRR and solar_pr < SOLAR_UNDERPERF_PR:
        solar_underperforming = True
        
    solar_metrics = {
        "actual_generation_mw": round(solar_actual_mw, 2),
        "installed_capacity_mw": SOLAR_CAPACITY_MW,
        "capacity_factor": round(solar_actual_mw / SOLAR_CAPACITY_MW, 4) if SOLAR_CAPACITY_MW > 0 else 0.0,
        "expected_generation_mw": round(solar_expected_mw, 2),
        "performance_ratio": round(solar_pr, 4),
        "underperforming": solar_underperforming,
    }
    
    # ---------------------------------------------------------
    # Wind Metrics
    # ---------------------------------------------------------
    if ws < 3.0 or ws >= 25.0:
        wind_frac = 0.0
    elif ws >= 12.0:
        wind_frac = 1.0
    else:
        wind_frac = (ws - 3.0) / (12.0 - 3.0)
        
    wind_expected_mw = wind_frac * WIND_CAPACITY_MW
    
    if wind_expected_mw > 0:
        wind_pr = wind_actual_mw / wind_expected_mw
    else:
        wind_pr = 1.0
        
    wind_underperforming = False
    if ws >= WIND_UNDERPERF_MIN_SPEED and wind_pr < WIND_UNDERPERF_PR:
        wind_underperforming = True

    wind_metrics = {
        "actual_generation_mw": round(wind_actual_mw, 2),
        "installed_capacity_mw": WIND_CAPACITY_MW,
        "capacity_factor": round(wind_actual_mw / WIND_CAPACITY_MW, 4) if WIND_CAPACITY_MW > 0 else 0.0,
        "expected_generation_mw": round(wind_expected_mw, 2),
        "performance_ratio": round(wind_pr, 4),
        "underperforming": wind_underperforming,
    }
    
    # ---------------------------------------------------------
    # Combined Metrics
    # ---------------------------------------------------------
    total_actual = solar_actual_mw + wind_actual_mw
    total_expected = solar_expected_mw + wind_expected_mw
    
    pct_of_demand = (total_actual / demand_mw) * 100.0 if demand_mw > 0 else 0.0
    
    if total_expected > 0:
        utilisation = (total_actual / total_expected) * 100.0
    else:
        utilisation = 100.0
        
    curtailment_active = export >= CURTAILMENT_EXPORT_MW
    
    if solar_underperforming and wind_underperforming:
        status = "CRITICAL"
    elif solar_underperforming or wind_underperforming or curtailment_active:
        status = "WARNING"
    else:
        status = "HEALTHY"
        
    combined_metrics = {
        "total_renewable_mw": round(total_actual, 2),
        "renewable_pct_of_demand": round(pct_of_demand, 2),
        "renewable_utilisation": round(utilisation, 2),
        "curtailment_active": curtailment_active,
        "status": status,
    }
    
    return {
        "timestamp": str(row["timestamp"]),
        "solar": solar_metrics,
        "wind": wind_metrics,
        "combined": combined_metrics,
    }
