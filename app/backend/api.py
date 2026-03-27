"""
REST API for VigilAI.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import SOURCES_CONFIG

logger = logging.getLogger(__name__)

app = FastAPI(
    title="VigilAI API",
    description="Developer opportunity intelligence API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefreshResponse(BaseModel):
    success: bool
    message: str


class AnalysisRunResponse(BaseModel):
    success: bool
    processed: int


class AnalysisTemplatePreviewResponse(BaseModel):
    template_id: str
    total: int
    passed: int
    watch: int
    rejected: int


class AnalysisTemplatePreviewResultItemResponse(BaseModel):
    activity_id: str
    status: str
    failed_layer: Optional[str] = None
    summary_reasons: List[str] = []
    layer_results: List[dict] = []


class AnalysisTemplatePreviewResultsResponse(AnalysisTemplatePreviewResponse):
    items: List[AnalysisTemplatePreviewResultItemResponse] = []


class TrackingUpsertRequest(BaseModel):
    is_favorited: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    remind_at: Optional[str] = None


class DigestGenerateRequest(BaseModel):
    digest_date: Optional[str] = None


class DigestSendRequest(BaseModel):
    send_channel: str = "manual"


class DigestCandidateRequest(BaseModel):
    digest_date: Optional[str] = None


class AnalysisTemplateCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    is_default: bool = False
    preference_profile: Optional[Literal["money_first", "balanced", "safety_first"]] = None
    risk_tolerance: Optional[Literal["conservative", "balanced", "aggressive"]] = None
    research_mode: Optional[Literal["off", "shallow", "layered", "deep"]] = None
    tags: List[str] = []
    layers: List[dict] = []
    sort_fields: List[str] = []


class AnalysisTemplateDuplicateRequest(BaseModel):
    name: str


class AnalysisTemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    preference_profile: Optional[Literal["money_first", "balanced", "safety_first"]] = None
    risk_tolerance: Optional[Literal["conservative", "balanced", "aggressive"]] = None
    research_mode: Optional[Literal["off", "shallow", "layered", "deep"]] = None
    tags: Optional[List[str]] = None
    layers: Optional[List[dict]] = None
    sort_fields: Optional[List[str]] = None


class AnalysisTemplatePreviewRequest(BaseModel):
    id: Optional[str] = None
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    preference_profile: Optional[Literal["money_first", "balanced", "safety_first"]] = None
    risk_tolerance: Optional[Literal["conservative", "balanced", "aggressive"]] = None
    research_mode: Optional[Literal["off", "shallow", "layered", "deep"]] = None
    tags: List[str] = []
    layers: List[dict] = []
    sort_fields: List[str] = []
    activity_ids: List[str] = []


def _serialize_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _source_health_snapshot(source) -> dict:
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


@app.get("/api/activities")
async def list_activities(
    request: Request,
    category: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    analysis_status: Optional[str] = Query(None),
    deadline_level: Optional[str] = Query(None),
    trust_level: Optional[str] = Query(None),
    is_tracking: Optional[bool] = Query(None),
    is_favorited: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    filters = {}
    if category:
        filters["category"] = category
    if source_id:
        filters["source_id"] = source_id
    if status:
        filters["status"] = status
    if search:
        filters["search"] = search
    if analysis_status:
        filters["analysis_status"] = analysis_status
    if deadline_level:
        filters["deadline_level"] = deadline_level
    if trust_level:
        filters["trust_level"] = trust_level
    if is_tracking is not None:
        filters["is_tracking"] = is_tracking
    if is_favorited is not None:
        filters["is_favorited"] = is_favorited
    activities, total = request.app.state.data_manager.get_activities(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_model(activity) for activity in activities],
    }


@app.get("/api/activities/{activity_id}")
async def get_activity(request: Request, activity_id: str):
    detail = request.app.state.data_manager.get_activity_detail(activity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return detail


@app.get("/api/sources")
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


@app.post("/api/sources/{source_id}/refresh", response_model=RefreshResponse)
async def refresh_source(request: Request, source_id: str):
    success = await request.app.state.scheduler.refresh_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return RefreshResponse(success=True, message=f"Source {source_id} refresh started")


@app.post("/api/sources/refresh-all", response_model=RefreshResponse)
async def refresh_all_sources(request: Request):
    await request.app.state.scheduler.refresh_all()
    return RefreshResponse(success=True, message="All sources refresh started")


@app.get("/api/stats")
async def get_stats(request: Request):
    return request.app.state.data_manager.get_stats().model_dump(mode="json")


@app.get("/api/analysis/templates")
async def list_analysis_templates(request: Request):
    return request.app.state.data_manager.get_analysis_templates()


@app.get("/api/analysis/templates/default")
async def get_default_analysis_template(request: Request):
    template = request.app.state.data_manager.get_default_analysis_template()
    if template is None:
        raise HTTPException(status_code=404, detail="Default analysis template not found")
    return template


@app.post("/api/analysis/templates")
async def create_analysis_template(request: Request, payload: AnalysisTemplateCreateRequest):
    return request.app.state.data_manager.create_analysis_template(payload.model_dump(exclude_none=True))


@app.post("/api/analysis/templates/{template_id}/duplicate")
async def duplicate_analysis_template(
    request: Request,
    template_id: str,
    payload: AnalysisTemplateDuplicateRequest,
):
    try:
        return request.app.state.data_manager.duplicate_analysis_template(template_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/analysis/templates/{template_id}/activate")
async def activate_analysis_template(request: Request, template_id: str):
    try:
        return request.app.state.data_manager.set_default_analysis_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/analysis/templates/{template_id}")
async def update_analysis_template(
    request: Request,
    template_id: str,
    payload: AnalysisTemplateUpdateRequest,
):
    try:
        return request.app.state.data_manager.update_analysis_template(
            template_id,
            payload.model_dump(exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/analysis/templates/{template_id}")
async def delete_analysis_template(request: Request, template_id: str):
    try:
        request.app.state.data_manager.delete_analysis_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True}


@app.post("/api/analysis/templates/preview", response_model=AnalysisTemplatePreviewResponse)
async def preview_analysis_template_payload(
    request: Request,
    payload: AnalysisTemplatePreviewRequest,
):
    return request.app.state.data_manager.preview_analysis_template_payload(
        payload.model_dump(exclude_none=True)
    )


@app.post("/api/analysis/templates/preview/results", response_model=AnalysisTemplatePreviewResultsResponse)
async def preview_analysis_template_payload_results(
    request: Request,
    payload: AnalysisTemplatePreviewRequest,
):
    return request.app.state.data_manager.preview_analysis_template_payload_results(
        payload.model_dump(exclude_none=True)
    )


@app.get("/api/analysis/templates/{template_id}/preview", response_model=AnalysisTemplatePreviewResponse)
async def preview_analysis_template(request: Request, template_id: str):
    try:
        return request.app.state.data_manager.preview_analysis_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/analysis/run", response_model=AnalysisRunResponse)
async def run_analysis_for_all_activities(request: Request):
    processed = request.app.state.data_manager.rerun_analysis_for_all_activities()
    return AnalysisRunResponse(success=True, processed=processed)


@app.get("/api/analysis/results")
async def list_analysis_results(
    request: Request,
    analysis_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return request.app.state.data_manager.get_analysis_results(
        analysis_status=analysis_status,
        page=page,
        page_size=page_size,
    )


@app.get("/api/analysis/results/{activity_id}")
async def get_analysis_result_detail(request: Request, activity_id: str):
    detail = request.app.state.data_manager.get_activity_detail(activity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return detail


@app.get("/api/workspace")
async def get_workspace(request: Request):
    return request.app.state.data_manager.get_workspace()


@app.get("/api/tracking")
async def get_tracking(request: Request, status: Optional[str] = Query(None)):
    return request.app.state.data_manager.get_tracking_items(status=status)


@app.post("/api/tracking/{activity_id}")
async def create_tracking(request: Request, activity_id: str, payload: TrackingUpsertRequest):
    try:
        tracking = request.app.state.data_manager.upsert_tracking_item(activity_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return tracking.model_dump()


@app.patch("/api/tracking/{activity_id}")
async def update_tracking(request: Request, activity_id: str, payload: TrackingUpsertRequest):
    try:
        tracking = request.app.state.data_manager.upsert_tracking_item(activity_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return tracking.model_dump()


@app.delete("/api/tracking/{activity_id}")
async def delete_tracking(request: Request, activity_id: str):
    deleted = request.app.state.data_manager.delete_tracking_item(activity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tracking item not found")
    return {"success": True}


@app.get("/api/digests")
async def list_digests(request: Request):
    return [_serialize_model(digest) for digest in request.app.state.data_manager.get_digests()]


@app.get("/api/digests/candidates")
async def list_digest_candidates(request: Request, digest_date: Optional[str] = Query(None)):
    candidates = request.app.state.data_manager.get_digest_candidates(digest_date)
    return [_serialize_model(candidate) for candidate in candidates]


@app.post("/api/digests/candidates/{activity_id}")
async def add_digest_candidate(
    request: Request,
    activity_id: str,
    payload: Optional[DigestCandidateRequest] = None,
):
    try:
        success = request.app.state.data_manager.add_digest_candidate(
            activity_id,
            payload.digest_date if payload else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": success}


@app.delete("/api/digests/candidates/{activity_id}")
async def remove_digest_candidate(
    request: Request,
    activity_id: str,
    digest_date: Optional[str] = Query(None),
):
    deleted = request.app.state.data_manager.remove_digest_candidate(activity_id, digest_date)
    if not deleted:
        raise HTTPException(status_code=404, detail="Digest candidate not found")
    return {"success": True}


@app.get("/api/digests/{digest_id}")
async def get_digest(request: Request, digest_id: str):
    digest = request.app.state.data_manager.get_digest_by_id(digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest.model_dump()


@app.post("/api/digests/generate")
async def generate_digest(request: Request, payload: Optional[DigestGenerateRequest] = None):
    digest_date = payload.digest_date if payload else None
    digest = request.app.state.data_manager.generate_digest(digest_date)
    return digest.model_dump()


@app.post("/api/digests/{digest_id}/send")
async def send_digest(request: Request, digest_id: str, payload: DigestSendRequest):
    try:
        digest = request.app.state.data_manager.mark_digest_sent(digest_id, payload.send_channel)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return digest.model_dump()


@app.get("/api/categories")
async def list_categories():
    from models import Category

    return [{"value": category.value, "label": category.value.title()} for category in Category]


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
