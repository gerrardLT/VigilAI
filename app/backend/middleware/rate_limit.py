"""Rate limiting middleware using slowapi.

Provides configurable rate limits for standard and agent endpoints.
Limits are read from environment variables:
  - RATE_LIMIT_STANDARD: requests per minute for standard endpoints (default: 60)
  - RATE_LIMIT_AGENT: requests per minute for agent endpoints (default: 10)
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Read limits from environment variables with defaults
RATE_LIMIT_STANDARD = int(os.environ.get("RATE_LIMIT_STANDARD", "60"))
RATE_LIMIT_AGENT = int(os.environ.get("RATE_LIMIT_AGENT", "10"))

# Limit strings for use in route decorators
standard_limit = f"{RATE_LIMIT_STANDARD}/minute"
agent_limit = f"{RATE_LIMIT_AGENT}/minute"

# Module-level limiter instance
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom 429 handler returning JSON with Retry-After header."""
    response = JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": f"Rate limit exceeded: {exc.detail}",
        },
    )
    # Inject Retry-After and rate limit headers via slowapi
    try:
        response = request.app.state.limiter._inject_headers(
            response, request.state.view_rate_limit
        )
    except Exception:
        # Fallback: set a default Retry-After of 60 seconds
        response.headers["Retry-After"] = "60"
    # Ensure Retry-After is always present
    if "Retry-After" not in response.headers:
        response.headers["Retry-After"] = "60"
    return response


def setup_rate_limiter(app: FastAPI) -> None:
    """Add the rate limiter to app state and register the exceeded handler.

    Call this during application startup to enable rate limiting.

    Args:
        app: The FastAPI application instance.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
