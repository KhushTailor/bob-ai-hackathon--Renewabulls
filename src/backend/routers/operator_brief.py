"""
Operator Brief Router — Stage S9.

Exposes GET /api/operator-brief (and GET /api/brief alias).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import OperatorBriefResponse
from backend.services.operator_brief import generate_operator_brief

router = APIRouter()


@router.get("/operator-brief", response_model=OperatorBriefResponse, tags=["operator-brief"])
@router.get("/brief", response_model=OperatorBriefResponse, tags=["operator-brief"], include_in_schema=False)
def get_operator_brief() -> OperatorBriefResponse:
    """Return the current AI Operator Brief.

    Synthesizes status, alerts, renewables, forecasting, and simulation insights
    into a decision-support summary answering six core operational questions.
    """
    try:
        brief_data = generate_operator_brief()
        return OperatorBriefResponse(**brief_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate operator brief: {exc}")
