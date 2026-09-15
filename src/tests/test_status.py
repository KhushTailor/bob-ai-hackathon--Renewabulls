"""
Tests for GET /api/status — Stage S4.

Run from the src/ directory:
    pytest tests/test_status.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.data_loader import load_dataset


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Known last-row values from grid_data.csv (used to verify correctness)
# These are deterministic because the dataset is generated with a fixed seed.
# ---------------------------------------------------------------------------
LAST_ROW_DEMAND = 204.5
LAST_ROW_SOLAR = 19.46
LAST_ROW_WIND = 27.72
LAST_ROW_SOC = 50.2
LAST_ROW_IMPORT = 176.07
LAST_ROW_EXPORT = 0.0
LAST_ROW_FREQ = 49.9667
LAST_ROW_VOLTAGE = 1.0089


class TestStatusEndpoint:
    def test_returns_200(self, client):
        """GET /api/status returns HTTP 200."""
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_content_type_json(self, client):
        """GET /api/status returns application/json."""
        resp = client.get("/api/status")
        assert "application/json" in resp.headers["content-type"]

    def test_required_fields_present(self, client):
        """Response contains all required fields."""
        resp = client.get("/api/status")
        data = resp.json()
        required = {
            "timestamp",
            "demand_mw",
            "solar_actual_mw",
            "wind_actual_mw",
            "total_renewable_mw",
            "renewable_pct",
            "battery_soc_pct",
            "grid_import_mw",
            "grid_export_mw",
            "frequency_hz",
            "voltage_pu",
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing fields: {missing}"

    def test_no_extra_unexpected_nulls(self, client):
        """No required field is None/null."""
        resp = client.get("/api/status")
        data = resp.json()
        for field in ["demand_mw", "solar_actual_mw", "wind_actual_mw",
                      "total_renewable_mw", "renewable_pct", "battery_soc_pct",
                      "grid_import_mw", "grid_export_mw", "frequency_hz", "voltage_pu"]:
            assert data[field] is not None, f"Field '{field}' is null"

    def test_demand_matches_last_row(self, client):
        """demand_mw matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["demand_mw"] - LAST_ROW_DEMAND) < 0.01

    def test_solar_matches_last_row(self, client):
        """solar_actual_mw matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["solar_actual_mw"] - LAST_ROW_SOLAR) < 0.01

    def test_wind_matches_last_row(self, client):
        """wind_actual_mw matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["wind_actual_mw"] - LAST_ROW_WIND) < 0.01

    def test_battery_soc_matches_last_row(self, client):
        """battery_soc_pct matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["battery_soc_pct"] - LAST_ROW_SOC) < 0.01

    def test_import_matches_last_row(self, client):
        """grid_import_mw matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["grid_import_mw"] - LAST_ROW_IMPORT) < 0.01

    def test_frequency_matches_last_row(self, client):
        """frequency_hz matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["frequency_hz"] - LAST_ROW_FREQ) < 0.001

    def test_voltage_matches_last_row(self, client):
        """voltage_pu matches the last row of the dataset."""
        resp = client.get("/api/status")
        data = resp.json()
        assert abs(data["voltage_pu"] - LAST_ROW_VOLTAGE) < 0.001


class TestDerivedValues:
    def test_total_renewable_is_solar_plus_wind(self, client):
        """total_renewable_mw equals solar + wind."""
        resp = client.get("/api/status")
        data = resp.json()
        expected = round(data["solar_actual_mw"] + data["wind_actual_mw"], 2)
        assert abs(data["total_renewable_mw"] - expected) < 0.01

    def test_renewable_pct_formula(self, client):
        """renewable_pct equals total_renewable / demand × 100."""
        resp = client.get("/api/status")
        data = resp.json()
        expected = round(data["total_renewable_mw"] / data["demand_mw"] * 100, 2)
        assert abs(data["renewable_pct"] - expected) < 0.1

    def test_renewable_pct_range(self, client):
        """renewable_pct is within [0, 100]."""
        resp = client.get("/api/status")
        data = resp.json()
        assert 0.0 <= data["renewable_pct"] <= 100.0

    def test_total_renewable_last_row(self, client):
        """total_renewable_mw matches the known last-row sum."""
        resp = client.get("/api/status")
        data = resp.json()
        expected = round(LAST_ROW_SOLAR + LAST_ROW_WIND, 2)
        assert abs(data["total_renewable_mw"] - expected) < 0.01

    def test_renewable_pct_last_row(self, client):
        """renewable_pct matches expected calculation from last row."""
        resp = client.get("/api/status")
        data = resp.json()
        expected = round((LAST_ROW_SOLAR + LAST_ROW_WIND) / LAST_ROW_DEMAND * 100, 2)
        assert abs(data["renewable_pct"] - expected) < 0.1


class TestNumericTypes:
    def test_all_numeric_fields_are_float(self, client):
        """All numeric fields are returned as float (not string)."""
        resp = client.get("/api/status")
        data = resp.json()
        float_fields = [
            "demand_mw", "solar_actual_mw", "wind_actual_mw",
            "total_renewable_mw", "renewable_pct", "battery_soc_pct",
            "grid_import_mw", "grid_export_mw", "frequency_hz", "voltage_pu",
        ]
        for field in float_fields:
            assert isinstance(data[field], (int, float)), (
                f"Field '{field}' is type {type(data[field])}, expected numeric"
            )

    def test_timestamp_is_string(self, client):
        """timestamp field is returned as a string."""
        resp = client.get("/api/status")
        data = resp.json()
        assert isinstance(data["timestamp"], str)
        assert len(data["timestamp"]) > 0


class TestDataConsistency:
    def test_status_matches_dataset_last_row(self, client):
        """Values returned by /api/status match the actual last row of grid_data.csv."""
        load_dataset.cache_clear()
        df = load_dataset()
        last = df.iloc[-1]

        resp = client.get("/api/status")
        data = resp.json()

        assert abs(data["demand_mw"] - float(last["demand_mw"])) < 0.01
        assert abs(data["solar_actual_mw"] - float(last["solar_actual_mw"])) < 0.01
        assert abs(data["wind_actual_mw"] - float(last["wind_actual_mw"])) < 0.01
        assert abs(data["battery_soc_pct"] - float(last["battery_soc_pct"])) < 0.01
        assert abs(data["frequency_hz"] - float(last["frequency_hz"])) < 0.001
        assert abs(data["voltage_pu"] - float(last["voltage_pu"])) < 0.001
