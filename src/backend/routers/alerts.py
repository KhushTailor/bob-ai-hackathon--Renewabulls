"""Alerts router — GET /api/alerts.

Returns the currently active anomaly alerts derived from the latest
simulated grid state.  All alerts are rule-based and deterministic.
This is a simulated decision-support prototype only.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import AlertResponse, AlertsResponse
from backend.services.anomaly_engine import get_active_alerts

router = APIRouter()


@router.get("/alerts", response_model=AlertsResponse, tags=["grid"])
def get_alerts() -> AlertsResponse:
    """Return active anomaly alerts for the current grid state.

    Evaluates all 12 rule-based detectors against the latest dataset
    row and returns any triggered alerts sorted by severity
    (CRITICAL first, then WARNING, then INFO).
    """
    alerts = get_active_alerts(window_rows=1)

    alert_responses = [
        AlertResponse(
            alert_id=a.alert_id,
            rule_id=a.rule_id,
            severity=a.severity,
            category=a.category,
            title=a.title,
            message=a.message,
            metric_name=a.metric_name,
            metric_value=a.metric_value,
            threshold=a.threshold,
            timestamp=a.timestamp,
        )
        for a in alerts
    ]

    return AlertsResponse(
        alert_count=len(alert_responses),
        critical_count=sum(1 for a in alert_responses if a.severity == "CRITICAL"),
        warning_count=sum(1 for a in alert_responses if a.severity == "WARNING"),
        info_count=sum(1 for a in alert_responses if a.severity == "INFO"),
        alerts=alert_responses,
    )
