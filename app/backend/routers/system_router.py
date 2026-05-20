"""
System router - handles /api/health, /api/sources/*, /api/categories, /metrics endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import SOURCES_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


# --- Pydantic Models ---


class RefreshResponse(BaseModel):
    success: bool
    message: str


# --- Helper Functions ---


def _source_health_snapshot(source) -> dict:
    """Calculate health metrics for a single source."""
    now = datetime.now()
    status = source.status.value if hasattr(source.status, "value") else str(source.status)
    last_success_age_hours = None
    freshness_level = "never"

    if source.last_success:
        last_success_age_hours = round((now - source.last_success).total_seconds() / 3600, 1)
        if last_success_age_hours <= 24:
            freshness_level = "fresh"
        elif last_success_age_hours <= 72:
            freshness_level = "aging"
        else:
            freshness_level = "stale"

    if status == "error":
        freshness_level = "critical" if source.last_success else "never"

    score = 40
    score += {"success": 35, "running": 25, "idle": 10, "error": -20}.get(status, 0)
    score += {"fresh": 20, "aging": 8, "stale": -10, "critical": -25, "never": -15}[freshness_level]
    if source.activity_count >= 10:
        score += 10
    elif source.activity_count > 0:
        score += 5

    health_score = max(0, min(100, int(score)))
    needs_attention = status == "error" or freshness_level in {"stale", "critical", "never"}

    return {
        "health_score": health_score,
        "freshness_level": freshness_level,
        "last_success_age_hours": last_success_age_hours,
        "needs_attention": needs_attention,
    }


# --- Endpoints ---


@router.get("/api/health")
async def health_check():
    return {"status": "正常", "timestamp": datetime.now().isoformat()}


@router.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics in text format."""
    from prometheus_client import generate_latest
    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@router.get("/api/sources")
async def list_sources(request: Request):
    sources = request.app.state.data_manager.get_sources_status()
    return [
        {
            "id": source.id,
            "name": source.name,
            "type": source.type.value if hasattr(source.type, "value") else source.type,
            "category": SOURCES_CONFIG.get(source.id, {}).get("category", "dev_event"),
            "status": source.status.value if hasattr(source.status, "value") else source.status,
            "last_run": source.last_run.isoformat() if source.last_run else None,
            "last_success": source.last_success.isoformat() if source.last_success else None,
            "activity_count": source.activity_count,
            "error_message": source.error_message,
            **_source_health_snapshot(source),
        }
        for source in sources
    ]


@router.post("/api/sources/{source_id}/refresh", response_model=RefreshResponse)
async def refresh_source(request: Request, source_id: str):
    success = await request.app.state.scheduler.refresh_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"来源 {source_id} 不存在")
    return RefreshResponse(success=True, message=f"来源 {source_id} 已开始刷新")


@router.post("/api/sources/refresh-all", response_model=RefreshResponse)
async def refresh_all_sources(request: Request):
    await request.app.state.scheduler.refresh_all()
    return RefreshResponse(success=True, message="全部来源已开始刷新")


@router.get("/api/categories")
async def list_categories():
    from models import Category

    return [{"value": category.value, "label": category.value.title()} for category in Category]


@router.get("/api/duplicates")
async def list_duplicates(request: Request):
    """List all detected cross-domain duplicates."""
    from services.deduplicator import CrossDomainDeduplicator

    pool = request.app.state.data_manager._pool
    dedup = CrossDomainDeduplicator(pool)
    return await dedup.list_duplicates()


@router.post("/api/duplicates/{link_id}/override")
async def override_duplicate(request: Request, link_id: str):
    """Override a deduplication decision (mark as not duplicate)."""
    from services.deduplicator import CrossDomainDeduplicator

    pool = request.app.state.data_manager._pool
    dedup = CrossDomainDeduplicator(pool)
    success = await dedup.override_duplicate(link_id)
    if not success:
        raise HTTPException(status_code=404, detail="重复链接不存在")
    return {"success": True}
