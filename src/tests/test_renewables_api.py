"""
Tests for the Renewables API endpoint — Stage S7.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

class TestRenewablesEndpoint:
    def test_get_renewables_returns_200(self):
        response = client.get("/api/renewables")
        assert response.status_code == 200

    def test_get_renewables_schema(self):
        response = client.get("/api/renewables")
        data = response.json()
        
        assert "timestamp" in data
        assert "solar" in data
        assert "wind" in data
        assert "combined" in data
        
        solar = data["solar"]
        assert "actual_generation_mw" in solar
        assert "installed_capacity_mw" in solar
        assert "capacity_factor" in solar
        assert "expected_generation_mw" in solar
        assert "performance_ratio" in solar
        assert "underperforming" in solar
        
        wind = data["wind"]
        assert "actual_generation_mw" in wind
        assert "installed_capacity_mw" in wind
        
        comb = data["combined"]
        assert "total_renewable_mw" in comb
        assert "renewable_pct_of_demand" in comb
        assert "renewable_utilisation" in comb
        assert "curtailment_active" in comb
        assert "status" in comb
