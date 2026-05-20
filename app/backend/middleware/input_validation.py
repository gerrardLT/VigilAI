"""Input validation middleware that enforces payload size limits.

Rejects oversized request bodies (>1MB → 413) and agent conversation messages
exceeding the character limit (>10000 chars → 422). Validation occurs before
any business logic processing.
"""

from __future__ import annotations

import json
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Configurable limits via environment variables
MAX_INPUT_LENGTH = int(os.environ.get("MAX_INPUT_LENGTH", "10000"))
MAX_BODY_SIZE = int(os.environ.get("MAX_BODY_SIZE", "1048576"))  # 1MB


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validates request body size and agent message content length.

    - Checks Content-Length header against MAX_BODY_SIZE (default 1MB).
      Returns 413 if exceeded.
    - For POST requests to agent turn endpoints (path contains "/turns"):
      parses the JSON body and checks the "content" field length against
      MAX_INPUT_LENGTH (default 10000 chars). Returns 422 if exceeded.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check Content-Length against max body size
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except (ValueError, TypeError):
                length = 0

            if length > MAX_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error_code": "BODY_TOO_LARGE",
                        "message": f"Request body exceeds maximum allowed size of {MAX_BODY_SIZE} bytes",
                        "field": "body",
                        "constraint": f"max_size={MAX_BODY_SIZE}",
                        "actual_length": length,
                    },
                )

        # For POST to agent turn endpoints, validate content field length
        if request.method == "POST" and "/turns" in request.url.path:
            try:
                body = await request.body()

                # Also reject if actual body size exceeds limit (no Content-Length header case)
                if len(body) > MAX_BODY_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error_code": "BODY_TOO_LARGE",
                            "message": f"Request body exceeds maximum allowed size of {MAX_BODY_SIZE} bytes",
                            "field": "body",
                            "constraint": f"max_size={MAX_BODY_SIZE}",
                            "actual_length": len(body),
                        },
                    )

                parsed = json.loads(body)
                content = parsed.get("content", "")

                if isinstance(content, str) and len(content) > MAX_INPUT_LENGTH:
                    return JSONResponse(
                        status_code=422,
                        content={
                            "error_code": "INPUT_TOO_LONG",
                            "message": f"Agent message content exceeds maximum allowed length of {MAX_INPUT_LENGTH} characters",
                            "field": "content",
                            "constraint": f"max_length={MAX_INPUT_LENGTH}",
                            "actual_length": len(content),
                        },
                    )
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If body isn't valid JSON, let downstream handlers deal with it
                pass

        return await call_next(request)
