"""Global exception handler that sanitizes error responses.

Catches all unhandled exceptions, logs the full stack trace with request
context, and returns a generic 500 response that never exposes internals.
"""

from __future__ import annotations

import logging
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exception during request processing.

    - Retrieves request_id from request.state (falls back to a new UUID).
    - Logs the full stack trace at ERROR level with request_id, path, and method.
    - Returns a generic 500 JSON response with error_code, message, and request_id.
    - NEVER includes stack traces, file paths, or internal variable names in the body.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.error(
        "Unhandled exception request_id=%s path=%s method=%s\n%s",
        request_id,
        request.url.path,
        request.method,
        traceback.format_exc(),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An internal error occurred. Please try again later.",
            "request_id": request_id,
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register the global exception handler on the FastAPI application."""
    app.add_exception_handler(Exception, global_exception_handler)
