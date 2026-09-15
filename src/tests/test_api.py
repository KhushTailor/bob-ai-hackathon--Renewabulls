"""
API integration tests — S3 scope.

Tests only the endpoints implemented in Stage S3 (/health).
Additional endpoint tests will be added in later stages.

Run from the src/ directory:
    pytest tests/test_api.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Reusable test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_health_returns_200(self, client):
        """GET /health returns HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_schema(self, client):
        """GET /health response contains required fields."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "dataset_loaded" in data

    def test_health_status_ok(self, client):
        """GET /health reports status 'ok'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_dataset_loaded(self, client):
        """GET /health reports the dataset is loaded with the correct row count."""
        response = client.get("/health")
        data = response.json()
        assert data["dataset_loaded"] is True
        assert data["dataset_rows"] == 17_520

    def test_health_content_type_json(self, client):
        """GET /health response content-type is application/json."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestUnknownRoute:
    def test_unknown_route_returns_404(self, client):
        """Requests to undefined routes return HTTP 404."""
        response = client.get("/does-not-exist")
        assert response.status_code == 404

    def test_api_docs_available(self, client):
        """OpenAPI docs are available at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200
