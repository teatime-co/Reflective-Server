import pytest
from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_prometheus_format(client: TestClient):
    """Test that metrics endpoint returns data in Prometheus text format"""
    response = client.get("/api/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    content = response.text
    assert "reflective_" in content


def test_metrics_endpoint_no_auth_required(client: TestClient):
    """Test that metrics endpoint doesn't require authentication"""
    response = client.get("/api/metrics")

    assert response.status_code == 200


def test_metrics_contains_expected_metrics(client: TestClient):
    """Test that metrics endpoint exposes expected metric types"""
    response = client.get("/api/metrics")
    content = response.text

    expected_metrics = [
        "reflective_auth_failed_logins_total",
        "reflective_auth_jwt_errors_total",
        "reflective_db_pool_size",
        "reflective_db_pool_checked_out",
        "reflective_he_operation_duration_seconds",
        "reflective_he_context_creation_duration_seconds",
    ]

    for metric_name in expected_metrics:
        assert metric_name in content, f"Expected metric '{metric_name}' not found in output"
