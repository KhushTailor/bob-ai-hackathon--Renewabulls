"""
Unit tests for src/backend/services/operator_brief.py — Stage S9.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from backend.services.anomaly_engine import Alert
from backend.services.operator_brief import generate_operator_brief


@pytest.fixture
def nominal_row():
    return {
        "timestamp": "2024-07-01 12:00:00+00:00",
        "demand_mw": 200.0,
        "solar_actual_mw": 35.0,
        "wind_actual_mw": 45.0,
        "solar_capacity_mw": 150.0,
        "wind_capacity_mw": 80.0,
        "battery_soc_pct": 65.0,
        "grid_import_mw": 120.0,
        "grid_export_mw": 0.0,
        "frequency_hz": 50.005,
        "voltage_pu": 1.002,
    }


@pytest.fixture
def healthy_renewables():
    return {
        "solar": {
            "actual_generation_mw": 35.0,
            "installed_capacity_mw": 150.0,
            "expected_generation_mw": 35.0,
            "performance_ratio": 1.0,
            "underperforming": False,
        },
        "wind": {
            "actual_generation_mw": 45.0,
            "installed_capacity_mw": 80.0,
            "expected_generation_mw": 45.0,
            "performance_ratio": 1.0,
            "underperforming": False,
        },
        "combined": {
            "total_renewable_mw": 80.0,
            "renewable_pct_of_demand": 40.0,
            "status": "HEALTHY",
        },
    }


@pytest.fixture
def mock_forecast():
    return {
        "horizon_hours": 72,
        "total_points": 288,
        "points": [
            {"timestamp": "2024-07-01 12:00:00+00:00", "predicted_demand_mw": 210.0},
            {"timestamp": "2024-07-01 16:00:00+00:00", "predicted_demand_mw": 235.0},
        ],
    }


class TestOperatorBriefService:
    """Comprehensive unit testing of the AI Operator Brief generator."""

    def test_current_live_dataset_brief(self):
        """Brief generated from the current dataset state contains all required fields."""
        brief = generate_operator_brief()

        # All six questions answered
        assert "situation" in brief
        assert "likely_cause" in brief
        assert "main_risk" in brief
        assert "recommended_action" in brief
        assert "rationale" in brief
        assert "consequence_if_ignored" in brief

        # Metadata
        assert "timestamp" in brief
        assert "severity" in brief
        assert brief["generated_by"] == "template-fallback"

        # Content is non-empty
        for field in ["situation", "likely_cause", "main_risk", "recommended_action", "rationale", "consequence_if_ignored"]:
            assert isinstance(brief[field], str)
            assert len(brief[field]) > 20

    def test_normal_healthy_state(self, nominal_row, healthy_renewables, mock_forecast):
        """When grid has no active alerts, brief reflects nominal conditions."""
        brief = generate_operator_brief(
            row=nominal_row,
            alerts=[],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "NOMINAL"
        assert "nominal" in brief["situation"].lower() or "stable" in brief["situation"].lower()
        assert "200.0" in brief["situation"]
        assert "65.0" in brief["situation"]
        assert "economic dispatch" in brief["recommended_action"].lower()

    def test_high_grid_import_warning_state(self, nominal_row, healthy_renewables, mock_forecast):
        """High import alert triggers specific import brief with exact numbers."""
        import_row = dict(nominal_row)
        import_row["grid_import_mw"] = 175.4
        import_alert = Alert(
            rule_id="ANO-011",
            severity="WARNING",
            category="import",
            title="Near import limit",
            message="Grid import is 175.4 MW",
            metric_name="grid_import_mw",
            metric_value=175.4,
            threshold=162.0,
            timestamp=import_row["timestamp"],
        )

        brief = generate_operator_brief(
            row=import_row,
            alerts=[import_alert],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "WARNING"
        assert "175.4" in brief["situation"]
        assert "180.0" in brief["situation"]  # Capacity
        assert "interconnection" in brief["main_risk"].lower()

    def test_critical_import_state(self, nominal_row, healthy_renewables, mock_forecast):
        """Critical import risk triggers critical severity and dominant warning."""
        crit_row = dict(nominal_row)
        crit_row["grid_import_mw"] = 178.5
        crit_alert = Alert(
            rule_id="ANO-016",
            severity="CRITICAL",
            category="import",
            title="Import capacity critical",
            message="Grid import is 178.5 MW",
            metric_name="grid_import_mw",
            metric_value=178.5,
            threshold=176.4,
            timestamp=crit_row["timestamp"],
        )

        brief = generate_operator_brief(
            row=crit_row,
            alerts=[crit_alert],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "CRITICAL"
        assert "178.5" in brief["situation"]
        assert "breaker trip" in brief["consequence_if_ignored"].lower() or "load shedding" in brief["consequence_if_ignored"].lower()

    def test_battery_low_warning(self, nominal_row, healthy_renewables, mock_forecast):
        """Low battery triggers battery storage preservation recommendations."""
        batt_row = dict(nominal_row)
        batt_row["battery_soc_pct"] = 12.0
        batt_alert = Alert(
            rule_id="ANO-007",
            severity="WARNING",
            category="battery",
            title="Battery low",
            message="SOC is 12.0%",
            metric_name="battery_soc_pct",
            metric_value=12.0,
            threshold=15.0,
            timestamp=batt_row["timestamp"],
        )

        brief = generate_operator_brief(
            row=batt_row,
            alerts=[batt_alert],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "WARNING"
        assert "12.0%" in brief["situation"]
        assert "battery" in brief["recommended_action"].lower()

    def test_battery_critical_alert(self, nominal_row, healthy_renewables, mock_forecast):
        """Critical battery alert sets severity to CRITICAL and warns of lockout."""
        crit_batt_row = dict(nominal_row)
        crit_batt_row["battery_soc_pct"] = 4.2
        crit_batt_alert = Alert(
            rule_id="ANO-008",
            severity="CRITICAL",
            category="battery",
            title="Battery critical",
            message="SOC is 4.2%",
            metric_name="battery_soc_pct",
            metric_value=4.2,
            threshold=5.0,
            timestamp=crit_batt_row["timestamp"],
        )

        brief = generate_operator_brief(
            row=crit_batt_row,
            alerts=[crit_batt_alert],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "CRITICAL"
        assert "4.2%" in brief["situation"]
        assert "lockout" in brief["consequence_if_ignored"].lower() or "exhaust" in brief["consequence_if_ignored"].lower()

    def test_renewable_underperformance(self, nominal_row, mock_forecast):
        """Underperforming solar/wind appears in the brief with PR values."""
        under_renewables = {
            "solar": {
                "actual_generation_mw": 15.0,
                "installed_capacity_mw": 150.0,
                "expected_generation_mw": 45.0,
                "performance_ratio": 0.333,
                "underperforming": True,
            },
            "wind": {
                "actual_generation_mw": 10.0,
                "installed_capacity_mw": 80.0,
                "expected_generation_mw": 30.0,
                "performance_ratio": 0.333,
                "underperforming": True,
            },
            "combined": {
                "total_renewable_mw": 25.0,
                "renewable_pct_of_demand": 12.5,
                "status": "UNDERPERFORMING",
            },
        }
        ren_row = dict(nominal_row)
        ren_row["solar_actual_mw"] = 15.0
        ren_row["wind_actual_mw"] = 10.0

        brief = generate_operator_brief(
            row=ren_row,
            alerts=[],
            renewables=under_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "WARNING"
        assert "underperforming" in brief["situation"].lower()
        assert "15.0" in brief["situation"]
        assert "45.0" in brief["situation"]
        assert "33.3%" in brief["situation"]

    def test_frequency_deviation_critical(self, nominal_row, healthy_renewables, mock_forecast):
        """Critical frequency excursion triggers rapid battery frequency response."""
        freq_row = dict(nominal_row)
        freq_row["frequency_hz"] = 49.38
        freq_alert = Alert(
            rule_id="ANO-001",
            severity="CRITICAL",
            category="frequency",
            title="Frequency critical low",
            message="Frequency is 49.38 Hz",
            metric_name="frequency_hz",
            metric_value=49.38,
            threshold=49.5,
            timestamp=freq_row["timestamp"],
        )

        brief = generate_operator_brief(
            row=freq_row,
            alerts=[freq_alert],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "CRITICAL"
        assert "49.38" in brief["situation"]
        assert "frequency" in brief["main_risk"].lower()

    def test_voltage_excursion_warning(self, nominal_row, healthy_renewables, mock_forecast):
        """Voltage excursion triggers volt-var support recommendation."""
        volt_row = dict(nominal_row)
        volt_row["voltage_pu"] = 0.935
        volt_alert = Alert(
            rule_id="ANO-003",
            severity="WARNING",
            category="voltage",
            title="Voltage low",
            message="Voltage is 0.935 pu",
            metric_name="voltage_pu",
            metric_value=0.935,
            threshold=0.95,
            timestamp=volt_row["timestamp"],
        )

        brief = generate_operator_brief(
            row=volt_row,
            alerts=[volt_alert],
            renewables=healthy_renewables,
            forecast=mock_forecast,
        )

        assert brief["severity"] == "WARNING"
        assert "0.935" in brief["situation"]
        assert "var" in brief["recommended_action"].lower() or "voltage" in brief["recommended_action"].lower()

    def test_fallback_works_offline_without_credentials(self):
        """Service executes without any environment variables or network calls."""
        with patch("backend.config.WATSONX_BRIEF_ENABLED", False):
            brief = generate_operator_brief()
            assert brief["generated_by"] == "template-fallback"

    def test_watsonx_failure_falls_back_gracefully(self):
        """If watsonx raises an error, service falls back to template-fallback."""
        with patch("backend.config.WATSONX_BRIEF_ENABLED", True), \
             patch("backend.config.WATSONX_API_KEY", "fake-key"), \
             patch("backend.config.WATSONX_PROJECT_ID", "fake-project"), \
             patch("backend.services.operator_brief._try_watsonx_generation", return_value=None):
            brief = generate_operator_brief()
            assert brief["generated_by"] == "template-fallback"
            assert "situation" in brief
