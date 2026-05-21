"""
Security middleware tests covering auth, rate limiting, exception sanitization,
input validation, and request ID injection.

Validates: Requirements 2.2, 3.3, 4.4, 5.1
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from middleware.auth import AuthMiddleware  # noqa: E402
from middleware.exception_handler import setup_exception_handlers  # noqa: E402
from middleware.input_validation import InputValidationMiddleware  # noqa: E402
from middleware.rate_limit import setup_rate_limiter, limiter  # noqa: E402
from middleware.request_id import RequestIdMiddleware  # noqa: E402


def create_test_app(api_keys: list[str] | None = None) -> FastAPI:
    """Create a minimal FastAPI app with all security middleware mounted."""
    app = FastAPI()

    # Mount middleware in reverse order (Starlette processes in reverse)
    # Desired order: RequestID → Auth → RateLimit → InputValidation
    app.add_middleware(InputValidationMiddleware)
    setup_rate_limiter(app)
    if api_keys is not None:
        app.add_middleware(AuthMiddleware, api_keys=api_keys)
    else:
        app.add_middleware(AuthMiddleware, api_keys=[])
    app.add_middleware(RequestIdMiddleware)

    # Global exception handler
    setup_exception_handlers(app)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"message": "success"}

    @app.get("/api/error")
    async def error_endpoint():
        raise RuntimeError("Something went terribly wrong in internal code")

    @app.post("/api/agent/sessions/123/turns")
    async def agent_turn(request: Request):
        body = await request.body()
        data = json.loads(body)
        return {"content": data.get("content", "")}

    @app.post("/api/upload")
    async def upload(request: Request):
        body = await request.body()
        return {"size": len(body)}

    return app


# ---------------------------------------------------------------------------
# Auth Tests (Validates: Requirement 2.2)
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    """Tests for API key authentication middleware."""

    def test_request_without_api_key_returns_401(self):
        """When API_KEYS configured, requests without X-API-Key get 401."""
        app = create_test_app(api_keys=["valid-key-123"])
        client = TestClient(app)

        response = client.get("/api/test")

        assert response.status_code == 401
        body = response.json()
        assert body["error_code"] == "INVALID_API_KEY"
        assert "message" in body

    def test_request_with_valid_api_key_passes(self):
        """Requests with a valid API key should pass through."""
        app = create_test_app(api_keys=["valid-key-123"])
        client = TestClient(app)

        response = client.get("/api/test", headers={"X-API-Key": "valid-key-123"})

        assert response.status_code == 200
        assert response.json()["message"] == "success"

    def test_request_with_invalid_api_key_returns_401(self):
        """Requests with an invalid API key get 401."""
        app = create_test_app(api_keys=["valid-key-123"])
        client = TestClient(app)

        response = client.get("/api/test", headers={"X-API-Key": "wrong-key"})

        assert response.status_code == 401
        body = response.json()
        assert body["error_code"] == "INVALID_API_KEY"

    def test_exempt_path_bypasses_auth(self):
        """Health check endpoint should bypass authentication."""
        app = create_test_app(api_keys=["valid-key-123"])
        client = TestClient(app)

        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_empty_api_keys_disables_auth(self):
        """When no API keys configured, auth is disabled (pass-through)."""
        app = create_test_app(api_keys=[])
        client = TestClient(app)

        response = client.get("/api/test")

        assert response.status_code == 200
        assert response.json()["message"] == "success"


# ---------------------------------------------------------------------------
# Rate Limit Tests (Validates: Requirement 3.3)
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Tests for rate limiting middleware."""

    def test_rate_limit_exceeded_returns_429(self):
        """When rate limit is exceeded, response should be 429."""
        app = create_test_app(api_keys=[])

        # Add a rate-limited endpoint
        @app.get("/api/limited")
        @limiter.limit("2/minute")
        async def limited_endpoint(request: Request):
            return {"ok": True}

        client = TestClient(app)

        # First two requests should pass
        assert client.get("/api/limited").status_code == 200
        assert client.get("/api/limited").status_code == 200

        # Third request should be rate limited
        response = client.get("/api/limited")
        assert response.status_code == 429
        body = response.json()
        assert body["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_response_has_retry_after_header(self):
        """429 responses should include a Retry-After header."""
        app = create_test_app(api_keys=[])

        @app.get("/api/limited2")
        @limiter.limit("1/minute")
        async def limited_endpoint2(request: Request):
            return {"ok": True}

        client = TestClient(app)

        # Exhaust the limit
        client.get("/api/limited2")

        # Next request triggers 429
        response = client.get("/api/limited2")
        assert response.status_code == 429
        assert "Retry-After" in response.headers


# ---------------------------------------------------------------------------
# Exception Handler Tests (Validates: Requirement 4.4)
# ---------------------------------------------------------------------------


class TestExceptionHandler:
    """Tests for global exception handler sanitization."""

    def test_unhandled_exception_returns_500_with_request_id(self):
        """Unhandled exceptions should return 500 with a request_id."""
        app = create_test_app(api_keys=[])
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/error")

        assert response.status_code == 500
        body = response.json()
        assert "request_id" in body
        assert body["error_code"] == "INTERNAL_ERROR"

    def test_error_response_never_contains_stack_trace(self):
        """Error responses must never expose stack traces."""
        app = create_test_app(api_keys=[])
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/error")

        assert response.status_code == 500
        body_text = response.text
        # Should not contain Python traceback indicators
        assert "Traceback" not in body_text
        assert "File " not in body_text
        assert "RuntimeError" not in body_text
        assert "terribly wrong" not in body_text

    def test_error_response_has_generic_message(self):
        """Error response should have a generic, safe message."""
        app = create_test_app(api_keys=[])
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/error")

        assert response.status_code == 500
        body = response.json()
        assert body["message"] == "An internal error occurred. Please try again later."


# ---------------------------------------------------------------------------
# Input Validation Tests (Validates: Requirement 5.1)
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Tests for input validation middleware."""

    def test_agent_message_exceeding_limit_returns_422(self):
        """Agent messages exceeding MAX_INPUT_LENGTH should get 422."""
        app = create_test_app(api_keys=[])
        client = TestClient(app)

        # Create content exceeding 10000 chars
        long_content = "x" * 10001
        response = client.post(
            "/api/agent/sessions/123/turns",
            json={"content": long_content},
        )

        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "INPUT_TOO_LONG"
        assert "content" in body["field"]

    def test_oversized_body_returns_413(self):
        """Request bodies exceeding MAX_BODY_SIZE should get 413."""
        app = create_test_app(api_keys=[])
        client = TestClient(app)

        # Create a body exceeding 1MB (1048576 bytes)
        oversized_body = "a" * (1048576 + 1)
        response = client.post(
            "/api/upload",
            content=oversized_body,
            headers={"Content-Type": "application/octet-stream", "Content-Length": str(len(oversized_body))},
        )

        assert response.status_code == 413
        body = response.json()
        assert body["error_code"] == "BODY_TOO_LARGE"

    def test_normal_request_passes_validation(self):
        """Normal-sized requests should pass through validation."""
        app = create_test_app(api_keys=[])
        client = TestClient(app)

        response = client.post(
            "/api/agent/sessions/123/turns",
            json={"content": "Hello, this is a normal message."},
        )

        assert response.status_code == 200
        assert response.json()["content"] == "Hello, this is a normal message."


# ---------------------------------------------------------------------------
# Request ID Tests (Validates: Requirements 4.2, 24.1)
# ---------------------------------------------------------------------------


class TestRequestId:
    """Tests for request ID middleware."""

    def test_response_has_x_request_id_header(self):
        """Every response should include an X-Request-ID header."""
        app = create_test_app(api_keys=[])
        client = TestClient(app)

        response = client.get("/api/test")

        assert "X-Request-ID" in response.headers

    def test_request_id_is_valid_uuid(self):
        """The X-Request-ID header value should be a valid UUID v4."""
        app = create_test_app(api_keys=[])
        client = TestClient(app)

        response = client.get("/api/test")

        request_id = response.headers["X-Request-ID"]
        # Should not raise ValueError if it's a valid UUID
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4
