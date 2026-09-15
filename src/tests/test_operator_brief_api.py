"""
API integration tests for GET /api/operator-brief — Stage S9.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestOperatorBriefEndpoint:
    """Test suite for GET /api/operator-brief."""

    def test_get_operator_brief_returns_200(self):
        """GET /api/operator-brief returns HTTP 200."""
        response = client.get("/api/operator-brief")
        assert response.status_code == 200

    def test_get_operator_brief_content_type_json(self):
        """Response is valid JSON."""
        response = client.get("/api/operator-brief")
        assert "application/json" in response.headers["content-type"]

    def test_get_operator_brief_schema(self):
        """Response matches the required OperatorBriefResponse schema."""
        response = client.get("/api/operator-brief")
        data = response.json()

        # All six required narrative fields
        required_fields = [
            "timestamp",
            "situation",
            "likely_cause",
            "main_risk",
            "recommended_action",
            "rationale",
            "consequence_if_ignored",
            "severity",
            "generated_by",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            assert isinstance(data[field], str), f"Field {field} is not a string"
            assert len(data[field]) > 0, f"Field {field} is empty"

    def test_get_operator_brief_severity_enum(self):
        """Severity must be one of the known operational levels."""
        response = client.get("/api/operator-brief")
        data = response.json()
        assert data["severity"] in {"NOMINAL", "INFO", "WARNING", "CRITICAL"}

    def test_get_operator_brief_honest_generator(self):
        """generated_by must honestly report template-fallback in local environment."""
        response = client.get("/api/operator-brief")
        data = response.json()
        assert data["generated_by"] in {"template-fallback", "watsonx-granite"}
        # Without credentials, it must be template-fallback
        assert data["generated_by"] == "template-fallback"

    def test_get_brief_alias_returns_200(self):
        """The /api/brief alias returns HTTP 200 with matching schema."""
        response = client.get("/api/brief")
        assert response.status_code == 200
        data = response.json()
        assert "situation" in data
        assert "recommended_action" in data
