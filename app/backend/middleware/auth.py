"""Authentication middleware that validates API keys using constant-time comparison."""

from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

EXEMPT_PATHS = {"/api/health", "/metrics", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header against a list of allowed API keys.

    Uses hmac.compare_digest for constant-time comparison to prevent timing attacks.
    Exempt paths (health check, metrics, docs) bypass authentication.
    When no API keys are configured, authentication is disabled (pass-through).
    """

    def __init__(self, app, api_keys: list[str]):
        super().__init__(app)
        self.api_keys = api_keys

    async def dispatch(self, request: Request, call_next) -> Response:
        # Auth disabled when no keys configured
        if not self.api_keys:
            return await call_next(request)

        # Exempt paths bypass authentication
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if not any(hmac.compare_digest(key, valid) for valid in self.api_keys):
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "INVALID_API_KEY",
                    "message": "Valid API key required in X-API-Key header",
                },
            )

        return await call_next(request)
