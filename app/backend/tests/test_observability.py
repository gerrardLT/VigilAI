"""Tests for observability: request ID propagation and Prometheus metrics endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, CollectorRegistry

from middleware.request_id import RequestIdMiddleware
from middleware.metrics import MetricsMiddleware


@pytest.fixture
def app_with_middleware():
    """Create a FastAPI app with RequestId and Metrics middleware for testing."""
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/metrics")
    async def metrics_endpoint():
        from prometheus_client import generate_latest
        from fastapi.responses import Response

        return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")

    return app


def test_response_has_request_id(app_with_middleware):
    """Verify that every response includes an X-Request-ID header."""
    client = TestClient(app_with_middleware)
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # Verify it looks like a UUID
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36
    assert request_id.count("-") == 4


def test_request_id_is_unique_per_request(app_with_middleware):
    """Verify that each request gets a unique request ID."""
    client = TestClient(app_with_middleware)
    ids = set()
    for _ in range(5):
        response = client.get("/test")
        ids.add(response.headers["X-Request-ID"])
    assert len(ids) == 5


def test_metrics_endpoint_returns_prometheus_format(app_with_middleware):
    """Test that /metrics returns text/plain with Prometheus data."""
    client = TestClient(app_with_middleware)
    # Make a request first to generate some metrics
    client.get("/test")
    # Now check the metrics endpoint
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    # Prometheus output should contain standard metric names
    body = response.text
    assert "http_requests_total" in body or "http_request_duration_seconds" in body


def test_metrics_records_request_count(app_with_middleware):
    """Test that the metrics middleware increments request counters."""
    client = TestClient(app_with_middleware)
    # Make several requests
    for _ in range(3):
        client.get("/test")
    response = client.get("/metrics")
    body = response.text
    # Should see the /test path in metrics output
    assert "/test" in body
