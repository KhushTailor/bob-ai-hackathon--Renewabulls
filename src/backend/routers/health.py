"""Health check router — GET /health."""
from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import HealthResponse
from backend.services.data_loader import load_dataset

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Return the health status of the GridPulse backend.

    Verifies that the grid dataset is accessible and returns its row count.
    Returns HTTP 200 whether or not the dataset is loaded successfully —
    the ``dataset_loaded`` field indicates dataset availability.
    """
    try:
        df = load_dataset()
        return HealthResponse(
            status="ok",
            dataset_loaded=True,
            dataset_rows=len(df),
        )
    except FileNotFoundError as exc:
        return HealthResponse(
            status="ok",
            dataset_loaded=False,
            message=str(exc),
        )
