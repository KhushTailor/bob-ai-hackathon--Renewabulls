"""
GridPulse FastAPI application.

Start with:
    uvicorn backend.main:app --reload --port 8000

from the src/ directory.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import health, status, alerts, forecast, renewables, simulate, operator_brief

app = FastAPI(
    title="GridPulse",
    description=(
        "AI-assisted grid optimisation — demand forecasting, renewable monitoring, "
        "anomaly detection, 72-hour simulation, and AI operator briefs."
    ),
    version="0.1.0",
)

# CORS — allow all origins in development so the React frontend can connect.
# Restrict to the frontend origin in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(status.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(renewables.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(operator_brief.router, prefix="/api")
