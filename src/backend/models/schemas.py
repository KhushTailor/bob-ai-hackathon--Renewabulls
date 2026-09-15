"""Pydantic response schemas for the GridPulse API.

Schemas are added here as each stage is implemented.
"""
from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Alert schema
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    """A single triggered anomaly alert."""

    alert_id: str
    rule_id: str
    severity: str          # "CRITICAL" | "WARNING" | "INFO"
    category: str
    title: str
    message: str
    metric_name: str
    metric_value: float
    threshold: float | None = None
    timestamp: str


class AlertsResponse(BaseModel):
    """Response schema for GET /api/alerts."""

    alert_count: int
    critical_count: int
    warning_count: int
    info_count: int
    alerts: list[AlertResponse]


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    status: str
    dataset_loaded: bool
    dataset_rows: int | None = None
    message: str | None = None


class GridStatusResponse(BaseModel):
    """Response schema for GET /api/status.

    Represents the latest simulated grid state derived from the most
    recent row in grid_data.csv.  All power values are in MW; voltage
    is expressed in per-unit (pu) as stored in the dataset.
    """

    # Timestamp of the most-recent data row
    timestamp: str

    # Demand
    demand_mw: float

    # Generation
    solar_actual_mw: float
    wind_actual_mw: float
    total_renewable_mw: float        # solar + wind
    renewable_pct: float             # total_renewable / demand × 100, clamped [0, 100]

    # Storage
    battery_soc_pct: float

    # Interconnection flows
    grid_import_mw: float
    grid_export_mw: float

    # Grid quality
    frequency_hz: float
    voltage_pu: float                # per-unit voltage (nominal 1.0)


# ---------------------------------------------------------------------------
# Forecast schema
# ---------------------------------------------------------------------------

class ForecastPoint(BaseModel):
    """A single forecasted point in time."""
    timestamp: str
    predicted_demand_mw: float


class ForecastResponse(BaseModel):
    """Response schema for GET /api/forecast."""
    horizon_hours: int
    interval_minutes: int
    points: list[ForecastPoint]
    model_used: str


# ---------------------------------------------------------------------------
# Renewable Monitoring schema
# ---------------------------------------------------------------------------

class SolarMetrics(BaseModel):
    actual_generation_mw: float
    installed_capacity_mw: float
    capacity_factor: float
    expected_generation_mw: float
    performance_ratio: float
    underperforming: bool

class WindMetrics(BaseModel):
    actual_generation_mw: float
    installed_capacity_mw: float
    capacity_factor: float
    expected_generation_mw: float
    performance_ratio: float
    underperforming: bool

class CombinedRenewableMetrics(BaseModel):
    total_renewable_mw: float
    renewable_pct_of_demand: float
    renewable_utilisation: float
    curtailment_active: bool
    status: str

class RenewableMonitoringResponse(BaseModel):
    """Response schema for GET /api/renewables."""
    timestamp: str
    solar: SolarMetrics
    wind: WindMetrics
    combined: CombinedRenewableMetrics


# ---------------------------------------------------------------------------
# Simulator schema
# ---------------------------------------------------------------------------

class ScenarioRequest(BaseModel):
    action: str  # "BATTERY_DISPATCH", "LOAD_SHIFT", "GRID_IMPORT", "RENEWABLE_CURTAILMENT"
    amount_mw: float  # Magnitude of action
    duration_hours: float = 1.0  # How long the action lasts

class ScenarioResult(BaseModel):
    scenario_id: str
    action: str
    amount_mw: float
    duration_hours: float
    is_feasible: bool
    explanation: str
    
    # Action application
    applied_action_mw: float
    unmet_action_mw: float
    
    # Averages over the action duration
    original_demand_mw: float
    adjusted_demand_mw: float
    battery_soc_before_pct: float
    battery_soc_after_pct: float
    original_grid_import_mw: float
    adjusted_grid_import_mw: float
    original_grid_export_mw: float
    adjusted_grid_export_mw: float
    renewable_generation_mw: float
    renewable_utilisation_pct: float
    curtailed_mw: float
    
    # 72-hour Scoring
    estimated_cost: float
    constraint_violations: list[str]
    risk_severity: str # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    score: float # 0 to 100

class CompareRequest(BaseModel):
    scenarios: list[ScenarioRequest]

class CompareResponse(BaseModel):
    results: list[ScenarioResult]


# ---------------------------------------------------------------------------
# Operator Brief schema
# ---------------------------------------------------------------------------

class OperatorBriefResponse(BaseModel):
    """Response schema for GET /api/operator-brief."""
    timestamp: str
    situation: str
    likely_cause: str
    main_risk: str
    recommended_action: str
    rationale: str
    consequence_if_ignored: str
    severity: str
    generated_by: str
