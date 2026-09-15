"""Forecast router — GET /api/forecast.

Returns a 72-hour demand forecast using either watsonx Granite TTM
or a statistical fallback model.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import ForecastResponse, ForecastPoint
from backend.services.forecaster import get_demand_forecast

router = APIRouter()


@router.get("/forecast", response_model=ForecastResponse, tags=["forecast"])
def get_forecast(horizon_hours: int = 72) -> ForecastResponse:
    """Return a demand forecast."""
    result = get_demand_forecast(horizon_hours=horizon_hours)

    points = [
        ForecastPoint(
            timestamp=pt["timestamp"],
            predicted_demand_mw=pt["predicted_demand_mw"]
        )
        for pt in result["points"]
    ]

    return ForecastResponse(
        horizon_hours=horizon_hours,
        interval_minutes=15,
        points=points,
        model_used=result["model_used"]
    )
