"""
API tests for GET /api/alerts — Stage S5.

Run from the src/ directory:
    pytest tests/test_alerts.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestAlertsEndpoint:
    def test_returns_200(self, client):
        """GET /api/alerts returns HTTP 200."""
        resp = client.get("/api/alerts")
        assert resp.status_code == 200

    def test_content_type_json(self, client):
        resp = client.get("/api/alerts")
        assert "application/json" in resp.headers["content-type"]

    def test_response_has_required_top_level_fields(self, client):
        data = client.get("/api/alerts").json()
        for field in ("alert_count", "critical_count", "warning_count", "info_count", "alerts"):
            assert field in data, f"Missing top-level field: {field}"

    def test_alert_count_matches_list_length(self, client):
        data = client.get("/api/alerts").json()
        assert data["alert_count"] == len(data["alerts"])

    def test_count_totals_add_up(self, client):
        data = client.get("/api/alerts").json()
        total = data["critical_count"] + data["warning_count"] + data["info_count"]
        assert total == data["alert_count"]

    def test_each_alert_has_required_fields(self, client):
        data = client.get("/api/alerts").json()
        required = {
            "alert_id", "rule_id", "severity", "category",
            "title", "message", "metric_name", "metric_value", "timestamp",
        }
        for alert in data["alerts"]:
            missing = required - set(alert.keys())
            assert not missing, f"Alert {alert.get('rule_id')} missing: {missing}"

    def test_severity_values_are_valid(self, client):
        data = client.get("/api/alerts").json()
        valid = {"CRITICAL", "WARNING", "INFO"}
        for alert in data["alerts"]:
            assert alert["severity"] in valid, (
                f"Invalid severity '{alert['severity']}' in {alert['rule_id']}"
            )

    def test_alerts_sorted_critical_first(self, client):
        data = client.get("/api/alerts").json()
        alerts = data["alerts"]
        if len(alerts) < 2:
            return  # nothing to sort
        order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        severities = [order[a["severity"]] for a in alerts]
        assert severities == sorted(severities), "Alerts are not sorted by severity"

    def test_alert_ids_are_unique(self, client):
        data = client.get("/api/alerts").json()
        ids = [a["alert_id"] for a in data["alerts"]]
        assert len(ids) == len(set(ids)), "Duplicate alert IDs in response"

    def test_metric_values_are_numeric(self, client):
        data = client.get("/api/alerts").json()
        for alert in data["alerts"]:
            assert isinstance(alert["metric_value"], (int, float)), (
                f"metric_value is not numeric in {alert['rule_id']}"
            )

    def test_rule_ids_match_expected_format(self, client):
        """All rule_ids follow the ANO-NNN format."""
        import re
        data = client.get("/api/alerts").json()
        pattern = re.compile(r"^ANO-\d{3}$")
        for alert in data["alerts"]:
            assert pattern.match(alert["rule_id"]), (
                f"rule_id '{alert['rule_id']}' does not match ANO-NNN format"
            )


class TestLatestRowAlerts:
    """Verify alerts are consistent with the known latest dataset row."""

    def test_high_import_alert_present(self, client):
        """Latest row has import ~176 MW (>90% of 180 MW cap) → ANO-011 should fire."""
        data = client.get("/api/alerts").json()
        rule_ids = {a["rule_id"] for a in data["alerts"]}
        assert "ANO-011" in rule_ids, (
            f"ANO-011 expected (high import) but not found. Active rules: {rule_ids}"
        )

    def test_no_false_critical_frequency_alert(self, client):
        """Latest row has nominal frequency (~50 Hz) — ANO-001 should NOT fire."""
        data = client.get("/api/alerts").json()
        rule_ids = {a["rule_id"] for a in data["alerts"]}
        assert "ANO-001" not in rule_ids, "False CRITICAL frequency alert on nominal row"

    def test_no_false_critical_voltage_alert(self, client):
        """Latest row has nominal voltage (~1.009 pu) — ANO-004 should NOT fire."""
        data = client.get("/api/alerts").json()
        rule_ids = {a["rule_id"] for a in data["alerts"]}
        assert "ANO-004" not in rule_ids, "False CRITICAL voltage alert on nominal row"

    def test_no_false_critical_battery_alert(self, client):
        """Latest row has SOC ~50% — ANO-008 should NOT fire."""
        data = client.get("/api/alerts").json()
        rule_ids = {a["rule_id"] for a in data["alerts"]}
        assert "ANO-008" not in rule_ids, "False CRITICAL battery alert on normal SOC"
