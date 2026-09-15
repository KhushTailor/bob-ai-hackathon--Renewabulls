"""
Tests for the Forecast API endpoint — Stage S6.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

class TestForecastEndpoint:
    def test_get_forecast_returns_200(self):
        response = client.get("/api/forecast")
        assert response.status_code == 200

    def test_get_forecast_schema(self):
        response = client.get("/api/forecast")
        data = response.json()
        
        assert "horizon_hours" in data
        assert data["horizon_hours"] == 72
        assert "interval_minutes" in data
        assert data["interval_minutes"] == 15
        assert "model_used" in data
        assert "points" in data
        assert len(data["points"]) == 288
        
        point = data["points"][0]
        assert "timestamp" in point
        assert "predicted_demand_mw" in point
        assert isinstance(point["predicted_demand_mw"], (float, int))
