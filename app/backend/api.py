"""
REST API for VigilAI.

This module creates the FastAPI app, mounts middleware, and includes all routers.
All endpoint logic lives in the router modules under `routers/`.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from middleware import (
    AuthMiddleware,
    InputValidationMiddleware,
    RequestIdMiddleware,
    setup_exception_handlers,
    setup_rate_limiter,
)
from routers.agent_router import router as agent_router
from routers.analysis_router import router as analysis_router
from routers.opportunity_router import router as opportunity_router
from routers.reward_router import a2a_router, router as reward_router
from routers.selection_router import router as selection_router
from routers.system_router import router as system_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security configuration from environment
# ---------------------------------------------------------------------------
_cors_origins_raw = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000"
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

_api_keys_raw = os.environ.get("API_KEYS", "")
API_KEYS = [k.strip() for k in _api_keys_raw.split(",") if k.strip()]

# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VigilAI API",
    description="开发者机会与选品智能工作台 API",
    version="3.0.0",
)

# ---------------------------------------------------------------------------
# Middleware stack (Starlette processes in reverse order of addition)
# Desired execution order: RequestID → Auth → RateLimit → CORS → InputValidation
# ---------------------------------------------------------------------------
app.add_middleware(InputValidationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
setup_rate_limiter(app)
app.add_middleware(AuthMiddleware, api_keys=API_KEYS)
app.add_middleware(RequestIdMiddleware)
setup_exception_handlers(app)

# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------
app.include_router(agent_router)
app.include_router(analysis_router)
app.include_router(opportunity_router)
app.include_router(selection_router)
app.include_router(reward_router)
app.include_router(a2a_router)
app.include_router(system_router)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(
        "%s %s status=%s duration=%.3fs",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response
