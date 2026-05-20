"""Prometheus metrics middleware for request counting and latency tracking."""

import time
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records Prometheus metrics for every HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        path = request.url.path
        REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration)
        if duration > 5.0:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "Slow request request_id=%s path=%s method=%s duration=%.2fs",
                request_id,
                path,
                request.method,
                duration,
            )
        return response
