"""
Tests for src/backend/services/simulator.py — Stage S8 Battery Energy & Simulation.
"""
from __future__ import annotations

import pytest

from backend.services.simulator import (
    evaluate_scenarios,
    BATTERY_CAPACITY_MWH,
    BATTERY_MIN_SOC_PCT,
    BATTERY_MAX_SOC_PCT,
)


class TestBatteryEnergyCalculation:
    """Explicit verification of battery energy and SOC calculations."""

    def test_battery_20mw_1hour_from_nominal(self):
        """20 MW for 1 hour from 50.2% => approximately 25.2%."""
        res = evaluate_scenarios([
            {"action": "BATTERY_DISPATCH", "amount_mw": 20.0, "duration_hours": 1.0}
        ])[0]

        assert res["is_feasible"] is True
        assert res["applied_action_mw"] == 20.0
        assert res["unmet_action_mw"] == 0.0
        assert res["battery_soc_before_pct"] == 50.2
        assert abs(res["battery_soc_after_pct"] - 25.2) < 0.1
        assert "BATTERY_CRITICAL_LOW" not in res["constraint_violations"]

    def test_battery_10mw_1hour_from_nominal(self):
        """10 MW for 1 hour from 50.2% => approximately 37.7%."""
        res = evaluate_scenarios([
            {"action": "BATTERY_DISPATCH", "amount_mw": 10.0, "duration_hours": 1.0}
        ])[0]

        assert res["is_feasible"] is True
        assert res["applied_action_mw"] == 10.0
        assert res["unmet_action_mw"] == 0.0
        assert res["battery_soc_before_pct"] == 50.2
        assert abs(res["battery_soc_after_pct"] - 37.7) < 0.1
        assert "BATTERY_CRITICAL_LOW" not in res["constraint_violations"]

    def test_battery_20mw_15minutes_from_nominal(self):
        """20 MW for 15 minutes (0.25h) => approximately 43.95%."""
        res = evaluate_scenarios([
            {"action": "BATTERY_DISPATCH", "amount_mw": 20.0, "duration_hours": 0.25}
        ])[0]

        assert res["is_feasible"] is True
        assert res["applied_action_mw"] == 20.0
        assert res["unmet_action_mw"] == 0.0
        assert abs(res["battery_soc_after_pct"] - 43.95) < 0.1

    def test_discharge_cannot_cross_5pct_reserve(self):
        """Discharge cannot cross 5% operational reserve; excess request is unmet."""
        # Starting from ~50.2% (40.16 MWh). Available above 5% (4 MWh) is 36.16 MWh.
        # Requesting 40 MW for 2 hours = 80 MWh.
        res = evaluate_scenarios([
            {"action": "BATTERY_DISPATCH", "amount_mw": 40.0, "duration_hours": 2.0}
        ])[0]

        assert res["is_feasible"] is False
        assert res["unmet_action_mw"] > 0.0
        # Battery SOC after action must not drop below 5.0%
        assert res["battery_soc_after_pct"] >= 5.0

    def test_charge_cannot_cross_95pct_reserve(self):
        """Charge cannot cross 95% operational reserve; excess request is unmet."""
        # Starting from ~50.2% (40.16 MWh). Available room below 95% (76 MWh) is 35.84 MWh.
        # Requesting -40 MW (charge) for 2 hours = 80 MWh charge.
        res = evaluate_scenarios([
            {"action": "BATTERY_DISPATCH", "amount_mw": -40.0, "duration_hours": 2.0}
        ])[0]

        assert res["is_feasible"] is False
        assert res["unmet_action_mw"] > 0.0
        # Battery SOC after action must not exceed 95.0%
        assert res["battery_soc_after_pct"] <= 95.0

    def test_duration_conversion_is_correct(self):
        """Duration conversion properly scales energy = MW * hours."""
        # 40 MW for 0.5 hours = 20 MWh => 50.2 - 25.0 = 25.2%
        res = evaluate_scenarios([
            {"action": "BATTERY_DISPATCH", "amount_mw": 40.0, "duration_hours": 0.5}
        ])[0]
        assert abs(res["battery_soc_after_pct"] - 25.2) < 0.1

    def test_feasible_scenario_ranks_above_infeasible(self):
        """Feasible scenarios must always rank above infeasible scenarios."""
        scenarios = [
            {"action": "GRID_IMPORT", "amount_mw": 400.0, "duration_hours": 2.0},  # Infeasible (>180 MW)
            {"action": "BATTERY_DISPATCH", "amount_mw": 10.0, "duration_hours": 1.0},  # Feasible
        ]
        results = evaluate_scenarios(scenarios)

        assert len(results) == 2
        assert results[0]["is_feasible"] is True
        assert results[0]["action"] == "BATTERY_DISPATCH"
        assert results[1]["is_feasible"] is False
        assert results[1]["action"] == "GRID_IMPORT"

    def test_load_shift_action(self):
        """Load shift reduces adjusted demand without negative values."""
        res = evaluate_scenarios([
            {"action": "LOAD_SHIFT", "amount_mw": 50.0, "duration_hours": 1.0}
        ])[0]
        assert res["is_feasible"] is True
        assert res["original_demand_mw"] > res["adjusted_demand_mw"]
        assert abs(res["original_demand_mw"] - res["adjusted_demand_mw"] - 50.0) < 1.0

    def test_renewable_curtailment_action(self):
        """Curtailment applies to renewable generation and impacts utilisation."""
        res = evaluate_scenarios([
            {"action": "RENEWABLE_CURTAILMENT", "amount_mw": 20.0, "duration_hours": 1.0}
        ])[0]
        assert res["curtailed_mw"] > 0.0
        assert res["renewable_utilisation_pct"] <= 100.0
