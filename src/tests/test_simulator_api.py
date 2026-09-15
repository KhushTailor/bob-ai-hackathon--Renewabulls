"""
Tests for the Simulator API endpoint — Stage S8.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestSimulatorEndpoint:
    def test_post_simulate_returns_200(self):
        payload = {
            "action": "BATTERY_DISPATCH",
            "amount_mw": 20.0,
            "duration_hours": 1.0
        }
        response = client.post("/api/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["action"] == "BATTERY_DISPATCH"
        assert "score" in data
        assert "is_feasible" in data
        assert data["duration_hours"] == 1.0

    def test_post_simulate_compare(self):
        payload = {
            "scenarios": [
                {"action": "BATTERY_DISPATCH", "amount_mw": 20.0, "duration_hours": 1.0},
                {"action": "LOAD_SHIFT", "amount_mw": 30.0, "duration_hours": 2.0}
            ]
        }
        response = client.post("/api/simulate/compare", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert len(data["results"]) == 2
        
        res1 = data["results"][0]
        res2 = data["results"][1]
        
        # Results should be ranked by score
        assert res1["score"] >= res2["score"]
