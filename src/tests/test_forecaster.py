"""
Tests for src/backend/services/forecaster.py — Stage S6.
"""
from __future__ import annotations

import pandas as pd
import pytest
from datetime import datetime, timedelta

from backend.services.forecaster import get_demand_forecast, _fallback_forecast
from backend.services.data_loader import load_dataset


class TestForecaster:
    @pytest.fixture(scope="class")
    def dataset(self):
        load_dataset.cache_clear()
        return load_dataset()

    def test_forecast_returns_correct_structure(self, dataset):
        result = get_demand_forecast(horizon_hours=72)
        assert "points" in result
        assert "model_used" in result
        assert result["model_used"] == "seasonal-naive-fallback"
        assert isinstance(result["points"], list)

    def test_forecast_returns_correct_number_of_points(self, dataset):
        result = get_demand_forecast(horizon_hours=72)
        # 72 hours * 4 points/hour = 288 points
        assert len(result["points"]) == 288

    def test_forecast_timestamps_are_15_mins_apart(self, dataset):
        result = get_demand_forecast(horizon_hours=72)
        points = result["points"]
        for i in range(1, len(points)):
            ts1 = pd.to_datetime(points[i-1]["timestamp"])
            ts2 = pd.to_datetime(points[i]["timestamp"])
            diff = (ts2 - ts1).total_seconds()
            assert diff == 900.0  # 15 minutes = 900 seconds

    def test_forecast_values_are_valid(self, dataset):
        result = get_demand_forecast(horizon_hours=72)
        for pt in result["points"]:
            val = pt["predicted_demand_mw"]
            assert isinstance(val, float)
            assert val >= 0.0
            assert val < 1000.0  # sensible upper bound based on dataset

    def test_insufficient_data_fallback(self):
        # Create a tiny mock dataset
        mock_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01T00:00:00Z", periods=10, freq="15min", tz="UTC"),
            "demand_mw": [200.0 + i for i in range(10)]
        })
        # This will use the "last known value" fallback since we have < 1 day of data
        points = _fallback_forecast(mock_df, horizon_hours=2)
        assert len(points) == 8
        # Since < 1 day, it should fall back to last_demand which is 209.0
        for pt in points:
            assert pt["predicted_demand_mw"] == 209.0

    def test_one_day_fallback(self):
        # Create a mock dataset with > 1 day but < 1 week
        mock_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01T00:00:00Z", periods=100, freq="15min", tz="UTC"),
            "demand_mw": [100.0 + i for i in range(100)]
        })
        points = _fallback_forecast(mock_df, horizon_hours=2)
        assert len(points) == 8
        # Should look back 1 day (96 steps ago from the end)
        # End is index 99. 96 steps ago from end + offset
        # For i=1, it takes index 100 - 96 + 0 = 4. Value = 104.0
        assert points[0]["predicted_demand_mw"] == 104.0
        assert points[1]["predicted_demand_mw"] == 105.0

    def test_forecast_covers_exactly_72_hours(self, dataset):
        result = get_demand_forecast(horizon_hours=72)
        points = result["points"]
        ts_first = pd.to_datetime(points[0]["timestamp"])
        ts_last = pd.to_datetime(points[-1]["timestamp"])
        diff = (ts_last - ts_first).total_seconds()
        # 287 intervals between first and last point
        assert diff == 287 * 900.0
