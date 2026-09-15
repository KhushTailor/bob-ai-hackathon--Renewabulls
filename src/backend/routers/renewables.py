"""Renewables router — GET /api/renewables.

Returns deterministic renewable monitoring KPIs for the current grid state.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import RenewableMonitoringResponse
from backend.services.renewables import get_renewable_metrics

router = APIRouter()


@router.get("/renewables", response_model=RenewableMonitoringResponse, tags=["grid"])
def get_renewables() -> RenewableMonitoringResponse:
    """Return renewable performance metrics for the current grid state."""
    data = get_renewable_metrics()
    return RenewableMonitoringResponse(**data)
