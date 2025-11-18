import pytest
from fastapi.testclient import TestClient


def test_health_check_liveness(client: TestClient):
    """Test basic liveness health check"""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "reflective-api"


def test_health_check_readiness_success(client: TestClient):
    """Test readiness check with healthy dependencies"""
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"] == "healthy"
    assert data["checks"]["tenseal"] == "healthy"


def test_health_endpoints_no_auth_required(client: TestClient):
    """Test that health endpoints don't require authentication"""
    response_liveness = client.get("/api/health")
    response_readiness = client.get("/api/health/ready")

    assert response_liveness.status_code == 200
    assert response_readiness.status_code == 200
