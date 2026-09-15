"""Simulator router — POST /api/simulate and /api/simulate/compare.

Provides 72-hour what-if deterministic simulations.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import (
    ScenarioRequest,
    ScenarioResult,
    CompareRequest,
    CompareResponse
)
from backend.services.simulator import evaluate_scenarios

router = APIRouter()


@router.post("/simulate", response_model=ScenarioResult, tags=["simulator"])
def simulate_action(request: ScenarioRequest) -> ScenarioResult:
    """Evaluate a single action scenario."""
    try:
        results = evaluate_scenarios([request.model_dump()])
        return ScenarioResult(**results[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate/compare", response_model=CompareResponse, tags=["simulator"])
def simulate_compare(request: CompareRequest) -> CompareResponse:
    """Evaluate multiple scenarios and rank them by score."""
    try:
        reqs = [r.model_dump() for r in request.scenarios]
        results = evaluate_scenarios(reqs)
        return CompareResponse(results=[ScenarioResult(**r) for r in results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
