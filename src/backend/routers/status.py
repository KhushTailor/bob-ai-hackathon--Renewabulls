"""Grid status router — GET /api/status.

Returns the latest row from the synthetic grid dataset as the
'current' grid state.  This is a simulated decision-support
prototype and does not connect to real SCADA or hardware.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import GridStatusResponse
from backend.services.data_loader import get_latest_rows

router = APIRouter()


@router.get("/status", response_model=GridStatusResponse, tags=["grid"])
def get_grid_status() -> GridStatusResponse:
    """Return the current (latest simulated) grid state.

    Reads the most recent row from grid_data.csv and returns the core
    KPIs needed by the GridPulse dashboard: demand, generation, battery
    state, grid flows, and power-quality metrics.

    Derived values
    --------------
    total_renewable_mw  = solar_actual_mw + wind_actual_mw
    renewable_pct       = total_renewable_mw / demand_mw × 100,
                          clamped to [0, 100]
    """
    rows = get_latest_rows(n=1)

    if rows.empty:
        raise HTTPException(status_code=503, detail="Grid dataset is empty.")

    row = rows.iloc[0]

    solar = float(row["solar_actual_mw"])
    wind = float(row["wind_actual_mw"])
    demand = float(row["demand_mw"])

    total_renewable = round(solar + wind, 2)
    renewable_pct = round(
        min(100.0, max(0.0, (total_renewable / demand * 100) if demand > 0 else 0.0)),
        2,
    )

    return GridStatusResponse(
        timestamp=str(row["timestamp"]),
        demand_mw=round(demand, 2),
        solar_actual_mw=round(solar, 2),
        wind_actual_mw=round(wind, 2),
        total_renewable_mw=total_renewable,
        renewable_pct=renewable_pct,
        battery_soc_pct=round(float(row["battery_soc_pct"]), 2),
        grid_import_mw=round(float(row["grid_import_mw"]), 2),
        grid_export_mw=round(float(row["grid_export_mw"]), 2),
        frequency_hz=round(float(row["frequency_hz"]), 4),
        voltage_pu=round(float(row["voltage_pu"]), 4),
    )
