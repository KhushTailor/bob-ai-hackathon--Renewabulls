"""
Tests for src/backend/services/renewables.py — Stage S7.
"""
from __future__ import annotations

import pytest
import pandas as pd
from unittest import mock

from backend.services.renewables import get_renewable_metrics
from backend.services.anomaly_engine import (
    SOLAR_CAPACITY_MW,
    WIND_CAPACITY_MW,
)


@pytest.fixture
def mock_get_latest_rows(monkeypatch):
    def _mock_latest(n=1):
        df = pd.DataFrame([{
            "timestamp": "2024-04-01T12:00:00Z",
            "demand_mw": 200.0,
            "solar_actual_mw": 15.0,
            "wind_actual_mw": 30.0,
            "solar_irradiance_wm2": 600.0,
            "wind_speed_ms": 7.0,
            "grid_export_mw": 0.0,
        }])
        return df
    
    monkeypatch.setattr("backend.services.renewables.get_latest_rows", _mock_latest)


class TestRenewableMetrics:
    def test_solar_calculations_normal(self, mock_get_latest_rows):
        res = get_renewable_metrics()
        solar = res["solar"]
        
        assert solar["actual_generation_mw"] == 15.0
        assert solar["installed_capacity_mw"] == SOLAR_CAPACITY_MW
        assert solar["capacity_factor"] == round(15.0 / SOLAR_CAPACITY_MW, 4)
        assert solar["expected_generation_mw"] > 0
        assert not solar["underperforming"]
        assert solar["performance_ratio"] > 0

    def test_wind_calculations_normal(self, mock_get_latest_rows):
        res = get_renewable_metrics()
        wind = res["wind"]
        
        assert wind["actual_generation_mw"] == 30.0
        assert wind["installed_capacity_mw"] == WIND_CAPACITY_MW
        assert wind["capacity_factor"] == round(30.0 / WIND_CAPACITY_MW, 4)
        assert wind["expected_generation_mw"] > 0
        assert not wind["underperforming"]
        assert wind["performance_ratio"] > 0

    def test_combined_calculations_normal(self, mock_get_latest_rows):
        res = get_renewable_metrics()
        comb = res["combined"]
        
        assert comb["total_renewable_mw"] == 45.0
        assert comb["renewable_pct_of_demand"] == 22.5  # 45 / 200
        assert comb["renewable_utilisation"] > 0
        assert not comb["curtailment_active"]
        assert comb["status"] == "HEALTHY"

    def test_underperformance_detection(self, monkeypatch):
        # Provide a row where solar and wind PRs are terrible
        def _mock_latest(n=1):
            return pd.DataFrame([{
                "timestamp": "2024-04-01T12:00:00Z",
                "demand_mw": 200.0,
                "solar_actual_mw": 0.0, # Complete failure
                "wind_actual_mw": 0.0,  # Complete failure
                "solar_irradiance_wm2": 800.0, # Lots of sun
                "wind_speed_ms": 10.0,         # Lots of wind
                "grid_export_mw": 0.0,
            }])
        monkeypatch.setattr("backend.services.renewables.get_latest_rows", _mock_latest)
        
        res = get_renewable_metrics()
        assert res["solar"]["underperforming"] is True
        assert res["wind"]["underperforming"] is True
        assert res["combined"]["status"] == "CRITICAL"

    def test_curtailment_detection(self, monkeypatch):
        def _mock_latest(n=1):
            return pd.DataFrame([{
                "timestamp": "2024-04-01T12:00:00Z",
                "demand_mw": 100.0,
                "solar_actual_mw": 50.0,
                "wind_actual_mw": 60.0,
                "solar_irradiance_wm2": 800.0,
                "wind_speed_ms": 10.0,
                "grid_export_mw": 60.0, # High export -> curtailment
            }])
        monkeypatch.setattr("backend.services.renewables.get_latest_rows", _mock_latest)
        
        res = get_renewable_metrics()
        assert res["combined"]["curtailment_active"] is True
        assert res["combined"]["status"] in ["WARNING", "CRITICAL"]

    def test_zero_capacity_edge_case(self, monkeypatch):
        # Override constants to 0
        monkeypatch.setattr("backend.services.renewables.SOLAR_CAPACITY_MW", 0.0)
        monkeypatch.setattr("backend.services.renewables.WIND_CAPACITY_MW", 0.0)
        
        def _mock_latest(n=1):
            return pd.DataFrame([{
                "timestamp": "2024-04-01T12:00:00Z",
                "demand_mw": 200.0,
                "solar_actual_mw": 0.0,
                "wind_actual_mw": 0.0,
                "solar_irradiance_wm2": 0.0,
                "wind_speed_ms": 0.0,
                "grid_export_mw": 0.0,
            }])
        monkeypatch.setattr("backend.services.renewables.get_latest_rows", _mock_latest)
        
        res = get_renewable_metrics()
        assert res["solar"]["capacity_factor"] == 0.0
        assert res["wind"]["capacity_factor"] == 0.0
        assert res["solar"]["performance_ratio"] == 1.0
        assert res["wind"]["performance_ratio"] == 1.0
        assert res["combined"]["renewable_utilisation"] == 100.0

    def test_real_dataset_integration(self):
        # Actually uses the real dataset (no mock)
        res = get_renewable_metrics()
        assert res["timestamp"]
        assert isinstance(res["solar"]["actual_generation_mw"], float)
        assert isinstance(res["wind"]["actual_generation_mw"], float)
        assert isinstance(res["combined"]["total_renewable_mw"], float)
