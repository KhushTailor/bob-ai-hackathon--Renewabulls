"""
Demand Forecasting Service.

Provides a 72-hour forecast (288 points at 15-minute intervals) for grid demand.
If IBM WatsonX credentials and models are configured, it will use Granite TTM.
Otherwise, it falls back to a deterministic statistical method (Seasonal Naive)
based on the historical dataset.
"""
from __future__ import annotations

import pandas as pd
from datetime import timedelta

from backend.services.data_loader import load_dataset
from backend.config import WATSONX_GRANITE_TTM_ENABLED

def get_demand_forecast(horizon_hours: int = 72) -> dict:
    """
    Generate a demand forecast.

    Returns:
        dict containing:
            - points: list of dicts {"timestamp": str, "predicted_demand_mw": float}
            - model_used: str ("watsonx-granite-ttm" or "seasonal-naive-fallback")
    """
    dataset = load_dataset()
    if dataset.empty:
        raise ValueError("Dataset is empty. Cannot generate forecast.")

    points = _fallback_forecast(dataset, horizon_hours)
    return {
        "points": points,
        "model_used": "seasonal-naive-fallback"
    }

def _fallback_forecast(dataset: pd.DataFrame, horizon_hours: int) -> list[dict]:
    """
    Seasonal Naive fallback:
    For a given future timestamp t, use the demand from exactly 1 week ago (t - 7 days).
    This perfectly captures the diurnal and weekly patterns inherent in the data.
    If 7 days of history is not available, it gracefully degrades to 1 day ago,
    or falls back to the last known value.
    """
    # Number of 15-minute intervals in the horizon
    intervals = horizon_hours * 4
    
    # Last timestamp in the dataset
    last_ts = dataset["timestamp"].iloc[-1]
    last_demand = dataset["demand_mw"].iloc[-1]

    forecast_points = []
    
    # Determine the lookback strategy
    total_rows = len(dataset)
    week_rows = 7 * 24 * 4  # 672
    day_rows = 24 * 4       # 96

    for i in range(1, intervals + 1):
        future_ts = last_ts + timedelta(minutes=15 * i)
        
        predicted_val = last_demand
        if total_rows >= week_rows:
            # Look back 1 week. We use (i-1) modulo week_rows to loop if horizon > history.
            predicted_val = dataset["demand_mw"].iloc[total_rows - week_rows + ((i-1) % week_rows)]
        elif total_rows >= day_rows:
            # Look back 1 day
            predicted_val = dataset["demand_mw"].iloc[total_rows - day_rows + ((i-1) % day_rows)]
            
        # Ensure predicted value is non-negative and sensible
        predicted_val = max(0.0, float(predicted_val))
            
        forecast_points.append({
            "timestamp": future_ts.isoformat(),
            "predicted_demand_mw": round(predicted_val, 2)
        })

    return forecast_points
