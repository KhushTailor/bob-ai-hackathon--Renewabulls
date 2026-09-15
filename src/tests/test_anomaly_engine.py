"""
Tests for src/backend/services/anomaly_engine.py — Stage S5.

Each of the 12 rules is verified to:
  - fire on crafted inputs that breach its threshold
  - NOT fire on nominal (healthy) grid values
  - produce the correct severity and rule_id

Run from the src/ directory:
    pytest tests/test_anomaly_engine.py -v
"""
from __future__ import annotations

import pandas as pd
import pytest

from backend.services.anomaly_engine import (
    Alert,
    evaluate_row,
    get_active_alerts,
    FREQ_NOMINAL_HZ,
    FREQ_CRIT_BAND_HZ,
    FREQ_WARN_BAND_HZ,
    VOLT_WARN_LO,
    VOLT_WARN_HI,
    VOLT_CRIT_LO,
    VOLT_CRIT_HI,
    DEMAND_SURGE_WARN_MW,
    DEMAND_SURGE_CRIT_MW,
    BATT_WARN_LO_PCT,
    BATT_CRIT_LO_PCT,
    BATT_HIGH_PCT,
    SOLAR_UNDERPERF_PR,
    SOLAR_UNDERPERF_MIN_IRR,
    SOLAR_EFFICIENCY,
    SOLAR_CAPACITY_MW,
    IMPORT_WARN_PCT,
    IMPORT_CAPACITY_MW,
    RE_LOW_WARN_PCT,
    WIND_UNDERPERF_PR,
    WIND_UNDERPERF_MIN_SPEED,
    WIND_CAPACITY_MW,
    CURTAILMENT_EXPORT_MW,
    TEMP_WARN_HI,
    TEMP_WARN_LO,
    IMPORT_CRIT_PCT,
)
from backend.services.data_loader import load_dataset


# ---------------------------------------------------------------------------
# Helper: build a nominal (healthy) grid row
# ---------------------------------------------------------------------------
def _nominal_row(**overrides) -> pd.Series:
    """Return a Series representing a healthy grid state.

    Keyword arguments override individual fields so tests can push
    specific metrics outside nominal bounds.
    """
    base = {
        "timestamp": pd.Timestamp("2024-04-01 12:00:00", tz="UTC"),
        "demand_mw": 200.0,
        "solar_actual_mw": 15.0,
        "wind_actual_mw": 30.0,
        "solar_capacity_mw": 150.0,
        "wind_capacity_mw": 80.0,
        "solar_irradiance_wm2": 600.0,
        "wind_speed_ms": 7.0,
        "temperature_c": 18.0,
        "battery_soc_pct": 60.0,
        "grid_import_mw": 100.0,
        "grid_export_mw": 0.0,
        "frequency_hz": 50.00,
        "voltage_pu": 1.00,
        "hour_of_day": 12,
        "day_of_week": 0,
        "month": 4,
        "is_weekend": 0,
    }
    base.update(overrides)
    return pd.Series(base)


# ---------------------------------------------------------------------------
# ANO-001 Frequency deviation — CRITICAL
# ---------------------------------------------------------------------------
class TestANO001:
    def test_fires_on_critical_freq_low(self):
        row = _nominal_row(frequency_hz=FREQ_NOMINAL_HZ - FREQ_CRIT_BAND_HZ - 0.1)
        alerts = evaluate_row(row)
        ids = [a.rule_id for a in alerts]
        assert "ANO-001" in ids

    def test_fires_on_critical_freq_high(self):
        row = _nominal_row(frequency_hz=FREQ_NOMINAL_HZ + FREQ_CRIT_BAND_HZ + 0.1)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-001" for a in alerts)

    def test_severity_is_critical(self):
        row = _nominal_row(frequency_hz=49.2)
        alerts = evaluate_row(row)
        a = next(a for a in alerts if a.rule_id == "ANO-001")
        assert a.severity == "CRITICAL"

    def test_not_fired_on_nominal(self):
        row = _nominal_row(frequency_hz=50.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-001" for a in alerts)

    def test_not_fired_just_below_critical_threshold(self):
        row = _nominal_row(frequency_hz=FREQ_NOMINAL_HZ - FREQ_CRIT_BAND_HZ + 0.01)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-001" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-002 Frequency drift — WARNING
# ---------------------------------------------------------------------------
class TestANO002:
    def test_fires_in_warning_band(self):
        row = _nominal_row(frequency_hz=FREQ_NOMINAL_HZ - FREQ_WARN_BAND_HZ - 0.05)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-002" for a in alerts)

    def test_severity_is_warning(self):
        row = _nominal_row(frequency_hz=49.75)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-002"), None)
        assert a is not None and a.severity == "WARNING"

    def test_not_fired_when_critical(self):
        """At critical level, ANO-001 fires, not ANO-002."""
        row = _nominal_row(frequency_hz=49.2)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-002" for a in alerts)
        assert any(a.rule_id == "ANO-001" for a in alerts)

    def test_not_fired_on_nominal(self):
        row = _nominal_row(frequency_hz=50.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-002" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-003 Voltage excursion — WARNING
# ---------------------------------------------------------------------------
class TestANO003:
    def test_fires_on_low_voltage(self):
        row = _nominal_row(voltage_pu=VOLT_WARN_LO - 0.02)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-003" for a in alerts)

    def test_fires_on_high_voltage(self):
        row = _nominal_row(voltage_pu=VOLT_WARN_HI + 0.02)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-003" for a in alerts)

    def test_severity_is_warning(self):
        row = _nominal_row(voltage_pu=0.93)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-003"), None)
        assert a is not None and a.severity == "WARNING"

    def test_not_fired_on_nominal(self):
        row = _nominal_row(voltage_pu=1.00)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-003" for a in alerts)

    def test_not_fired_when_critical(self):
        row = _nominal_row(voltage_pu=VOLT_CRIT_LO - 0.01)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-003" for a in alerts)
        assert any(a.rule_id == "ANO-004" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-004 Severe voltage excursion — CRITICAL
# ---------------------------------------------------------------------------
class TestANO004:
    def test_fires_on_critical_low(self):
        row = _nominal_row(voltage_pu=VOLT_CRIT_LO - 0.01)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-004" for a in alerts)

    def test_fires_on_critical_high(self):
        row = _nominal_row(voltage_pu=VOLT_CRIT_HI + 0.01)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-004" for a in alerts)

    def test_severity_is_critical(self):
        row = _nominal_row(voltage_pu=0.88)
        alerts = evaluate_row(row)
        a = next(a for a in alerts if a.rule_id == "ANO-004")
        assert a.severity == "CRITICAL"

    def test_not_fired_on_nominal(self):
        row = _nominal_row(voltage_pu=1.00)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-004" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-005 Demand surge — WARNING
# ---------------------------------------------------------------------------
class TestANO005:
    def test_fires_in_warning_band(self):
        row = _nominal_row(demand_mw=DEMAND_SURGE_WARN_MW + 1.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-005" for a in alerts)

    def test_severity_is_warning(self):
        row = _nominal_row(demand_mw=DEMAND_SURGE_WARN_MW + 5.0)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-005"), None)
        assert a is not None and a.severity == "WARNING"

    def test_not_fired_below_threshold(self):
        row = _nominal_row(demand_mw=DEMAND_SURGE_WARN_MW - 10.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-005" for a in alerts)

    def test_not_fired_at_critical_level(self):
        row = _nominal_row(demand_mw=DEMAND_SURGE_CRIT_MW + 1.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-005" for a in alerts)
        assert any(a.rule_id == "ANO-006" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-006 Extreme demand surge — CRITICAL
# ---------------------------------------------------------------------------
class TestANO006:
    def test_fires_at_critical(self):
        row = _nominal_row(demand_mw=DEMAND_SURGE_CRIT_MW + 5.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-006" for a in alerts)

    def test_severity_is_critical(self):
        row = _nominal_row(demand_mw=DEMAND_SURGE_CRIT_MW + 5.0)
        alerts = evaluate_row(row)
        a = next(a for a in alerts if a.rule_id == "ANO-006")
        assert a.severity == "CRITICAL"

    def test_not_fired_below_threshold(self):
        row = _nominal_row(demand_mw=200.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-006" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-007 Battery low — WARNING
# ---------------------------------------------------------------------------
class TestANO007:
    def test_fires_in_warning_band(self):
        row = _nominal_row(battery_soc_pct=BATT_CRIT_LO_PCT + 1.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-007" for a in alerts)

    def test_severity_is_warning(self):
        row = _nominal_row(battery_soc_pct=10.0)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-007"), None)
        assert a is not None and a.severity == "WARNING"

    def test_not_fired_above_threshold(self):
        row = _nominal_row(battery_soc_pct=60.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-007" for a in alerts)

    def test_not_fired_at_critical_level(self):
        row = _nominal_row(battery_soc_pct=BATT_CRIT_LO_PCT - 1.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-007" for a in alerts)
        assert any(a.rule_id == "ANO-008" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-008 Battery critical — CRITICAL
# ---------------------------------------------------------------------------
class TestANO008:
    def test_fires_below_critical(self):
        row = _nominal_row(battery_soc_pct=BATT_CRIT_LO_PCT - 1.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-008" for a in alerts)

    def test_severity_is_critical(self):
        row = _nominal_row(battery_soc_pct=3.0)
        alerts = evaluate_row(row)
        a = next(a for a in alerts if a.rule_id == "ANO-008")
        assert a.severity == "CRITICAL"

    def test_not_fired_above_threshold(self):
        row = _nominal_row(battery_soc_pct=60.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-008" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-009 Battery high — INFO
# ---------------------------------------------------------------------------
class TestANO009:
    def test_fires_above_high_threshold(self):
        row = _nominal_row(battery_soc_pct=BATT_HIGH_PCT + 1.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-009" for a in alerts)

    def test_severity_is_info(self):
        row = _nominal_row(battery_soc_pct=95.0)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-009"), None)
        assert a is not None and a.severity == "INFO"

    def test_not_fired_at_normal_soc(self):
        row = _nominal_row(battery_soc_pct=60.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-009" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-010 Solar underperformance — WARNING
# ---------------------------------------------------------------------------
class TestANO010:
    def _expected_solar(self, irr: float) -> float:
        return (irr / 1000.0) * SOLAR_EFFICIENCY * SOLAR_CAPACITY_MW

    def test_fires_when_solar_low_in_daylight(self):
        irr = 700.0
        expected = self._expected_solar(irr)
        actual = expected * (SOLAR_UNDERPERF_PR - 0.1)  # below threshold
        row = _nominal_row(solar_irradiance_wm2=irr, solar_actual_mw=actual)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-010" for a in alerts)

    def test_severity_is_warning(self):
        irr = 700.0
        actual = self._expected_solar(irr) * 0.3
        row = _nominal_row(solar_irradiance_wm2=irr, solar_actual_mw=actual)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-010"), None)
        assert a is not None and a.severity == "WARNING"

    def test_not_fired_below_irr_threshold(self):
        """Rule is silent at night / low irradiance."""
        row = _nominal_row(solar_irradiance_wm2=SOLAR_UNDERPERF_MIN_IRR - 1, solar_actual_mw=0.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-010" for a in alerts)

    def test_not_fired_when_performance_is_good(self):
        irr = 700.0
        actual = self._expected_solar(irr) * 0.9  # PR = 0.9 > threshold
        row = _nominal_row(solar_irradiance_wm2=irr, solar_actual_mw=actual)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-010" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-011 High import — WARNING
# ---------------------------------------------------------------------------
class TestANO011:
    def test_fires_at_high_import(self):
        row = _nominal_row(grid_import_mw=IMPORT_CAPACITY_MW * IMPORT_WARN_PCT + 1.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-011" for a in alerts)

    def test_severity_is_warning(self):
        row = _nominal_row(grid_import_mw=170.0)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-011"), None)
        assert a is not None and a.severity == "WARNING"

    def test_not_fired_below_threshold(self):
        row = _nominal_row(grid_import_mw=100.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-011" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-012 Low renewable contribution — INFO
# ---------------------------------------------------------------------------
class TestANO012:
    def test_fires_when_re_low(self):
        row = _nominal_row(solar_actual_mw=2.0, wind_actual_mw=5.0, demand_mw=200.0)
        re_pct = (2.0 + 5.0) / 200.0 * 100
        assert re_pct < RE_LOW_WARN_PCT
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-012" for a in alerts)

    def test_severity_is_info(self):
        row = _nominal_row(solar_actual_mw=2.0, wind_actual_mw=5.0, demand_mw=200.0)
        alerts = evaluate_row(row)
        a = next((a for a in alerts if a.rule_id == "ANO-012"), None)
        assert a is not None and a.severity == "INFO"

    def test_not_fired_above_threshold(self):
        # 40 MW out of 200 = 20% > 15% threshold
        row = _nominal_row(solar_actual_mw=10.0, wind_actual_mw=30.0, demand_mw=200.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-012" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-013 Wind underperformance — WARNING
# ---------------------------------------------------------------------------
class TestANO013:
    def test_fires_when_wind_low(self):
        # 10 m/s wind speed -> fraction is (10-3)/9 = 7/9
        ws = 10.0
        frac = (ws - 3.0) / (12.0 - 3.0)
        expected = frac * WIND_CAPACITY_MW
        actual = expected * (WIND_UNDERPERF_PR - 0.1)  # below threshold
        row = _nominal_row(wind_speed_ms=ws, wind_actual_mw=actual)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-013" for a in alerts)

    def test_not_fired_at_low_speed(self):
        row = _nominal_row(wind_speed_ms=WIND_UNDERPERF_MIN_SPEED - 1, wind_actual_mw=0.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-013" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-014 Renewable curtailment — INFO
# ---------------------------------------------------------------------------
class TestANO014:
    def test_fires_on_high_export(self):
        row = _nominal_row(grid_export_mw=CURTAILMENT_EXPORT_MW + 0.1)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-014" for a in alerts)

    def test_not_fired_on_normal_export(self):
        row = _nominal_row(grid_export_mw=CURTAILMENT_EXPORT_MW - 10.0)
        alerts = evaluate_row(row)
        assert not any(a.rule_id == "ANO-014" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-015 Temperature extreme — WARNING
# ---------------------------------------------------------------------------
class TestANO015:
    def test_fires_on_high_temp(self):
        row = _nominal_row(temperature_c=TEMP_WARN_HI + 2.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-015" for a in alerts)

    def test_fires_on_low_temp(self):
        row = _nominal_row(temperature_c=TEMP_WARN_LO - 2.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-015" for a in alerts)


# ---------------------------------------------------------------------------
# ANO-016 Grid import capacity risk — CRITICAL
# ---------------------------------------------------------------------------
class TestANO016:
    def test_fires_on_critical_import(self):
        row = _nominal_row(grid_import_mw=IMPORT_CAPACITY_MW * IMPORT_CRIT_PCT + 1.0)
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-016" for a in alerts)
        # Verify ANO-011 did NOT fire
        assert not any(a.rule_id == "ANO-011" for a in alerts)


# ---------------------------------------------------------------------------
# Normal grid conditions — no critical alerts
# ---------------------------------------------------------------------------
class TestNominalConditions:
    def test_no_critical_alerts_on_healthy_row(self):
        """A perfectly nominal row should produce zero CRITICAL alerts."""
        row = _nominal_row()
        alerts = evaluate_row(row)
        criticals = [a for a in alerts if a.severity == "CRITICAL"]
        assert not criticals, f"Unexpected CRITICAL alerts: {[a.rule_id for a in criticals]}"

    def test_nominal_row_may_have_info_alerts(self):
        """INFO alerts (e.g. low RE) are acceptable on a valid healthy row."""
        row = _nominal_row()
        alerts = evaluate_row(row)
        # Only INFO allowed; no CRITICAL or WARNING
        for a in alerts:
            assert a.severity in ("INFO",), (
                f"Unexpected {a.severity} alert {a.rule_id} on nominal row"
            )


# ---------------------------------------------------------------------------
# Injected anomaly detection using actual dataset rows
# ---------------------------------------------------------------------------
class TestInjectedAnomalies:
    """Verify that the deliberately injected anomaly periods in grid_data.csv
    are detected by the correct rules."""

    @pytest.fixture(scope="class")
    def dataset(self):
        load_dataset.cache_clear()
        return load_dataset()

    def test_frequency_anomaly_detected_in_dataset(self, dataset):
        """Injected frequency dips (rows 2240-2242) trigger ANO-001."""
        # Find rows with injected frequency dip
        dip_rows = dataset[dataset["frequency_hz"] < 49.4]
        assert len(dip_rows) >= 1, "No frequency dip rows found in dataset"
        row = dip_rows.iloc[0]
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-001" for a in alerts), (
            f"ANO-001 did not fire on freq={row['frequency_hz']}"
        )

    def test_voltage_anomaly_detected_in_dataset(self, dataset):
        """Injected voltage sag (row 4760) triggers ANO-004."""
        sag_rows = dataset[dataset["voltage_pu"] < 0.90]
        assert len(sag_rows) >= 1, "No voltage sag rows found in dataset"
        row = sag_rows.iloc[0]
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-004" for a in alerts), (
            f"ANO-004 did not fire on voltage={row['voltage_pu']}"
        )

    def test_battery_critical_detected_in_dataset(self, dataset):
        """Injected battery critical rows trigger ANO-008."""
        crit_rows = dataset[dataset["battery_soc_pct"] < 5.0]
        assert len(crit_rows) >= 1, "No battery critical rows found in dataset"
        row = crit_rows.iloc[0]
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-008" for a in alerts), (
            f"ANO-008 did not fire on SOC={row['battery_soc_pct']}"
        )

    def test_solar_underperformance_detected_in_dataset(self, dataset):
        """Injected solar underperformance rows (rows 15792-15795) trigger ANO-010."""
        irr_threshold = SOLAR_UNDERPERF_MIN_IRR
        high_irr = dataset[dataset["solar_irradiance_wm2"] > irr_threshold].copy()
        high_irr["expected_solar"] = (
            (high_irr["solar_irradiance_wm2"] / 1000.0)
            * SOLAR_EFFICIENCY
            * SOLAR_CAPACITY_MW
        )
        high_irr["pr"] = high_irr["solar_actual_mw"] / high_irr["expected_solar"]
        underperf = high_irr[high_irr["pr"] < SOLAR_UNDERPERF_PR]
        assert len(underperf) >= 1, "No solar underperformance rows found in dataset"
        row = underperf.iloc[0]
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-010" for a in alerts), (
            f"ANO-010 did not fire on PR={row['pr']:.3f}"
        )

    def test_high_import_detected_in_dataset(self, dataset):
        """Most rows have high import; ANO-011 should fire on them."""
        high_imp = dataset[
            dataset["grid_import_mw"] >= IMPORT_CAPACITY_MW * IMPORT_WARN_PCT
        ]
        assert len(high_imp) > 0, "No high-import rows in dataset"
        row = high_imp.iloc[0]
        alerts = evaluate_row(row)
        assert any(a.rule_id == "ANO-011" for a in alerts)


# ---------------------------------------------------------------------------
# Sorting and structure
# ---------------------------------------------------------------------------
class TestAlertStructure:
    def test_evaluate_row_returns_list(self):
        row = _nominal_row()
        result = evaluate_row(row)
        assert isinstance(result, list)

    def test_all_items_are_alert_instances(self):
        row = _nominal_row(frequency_hz=49.2, voltage_pu=0.88, battery_soc_pct=3.0)
        alerts = evaluate_row(row)
        for a in alerts:
            assert isinstance(a, Alert)

    def test_critical_comes_before_warning(self):
        row = _nominal_row(
            frequency_hz=49.2,  # CRITICAL
            battery_soc_pct=10.0,  # WARNING
        )
        alerts = evaluate_row(row)
        severities = [a.severity for a in alerts]
        crit_idx = next((i for i, s in enumerate(severities) if s == "CRITICAL"), None)
        warn_idx = next((i for i, s in enumerate(severities) if s == "WARNING"), None)
        if crit_idx is not None and warn_idx is not None:
            assert crit_idx < warn_idx

    def test_alert_has_required_fields(self):
        row = _nominal_row(frequency_hz=49.2)
        alerts = evaluate_row(row)
        a = next(a for a in alerts if a.rule_id == "ANO-001")
        assert a.alert_id
        assert a.severity == "CRITICAL"
        assert a.category
        assert a.title
        assert a.message
        assert a.metric_name
        assert a.metric_value is not None
        assert a.timestamp

    def test_get_active_alerts_returns_list(self):
        load_dataset.cache_clear()
        result = get_active_alerts()
        assert isinstance(result, list)
