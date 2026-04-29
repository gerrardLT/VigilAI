"""
REST API for VigilAI.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, List, Literal, Optional

from agent_platform.artifact_service import ArtifactService
from agent_platform.conversation_engine import ConversationEngine
from agent_platform.repository import AgentPlatformRepository
from agent_platform.tool_router import ToolRouter, build_default_registry
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analysis.run_manager import AnalysisRunManager
from analysis.review_service import ReviewService
from analysis.opportunity_ai_filter import OpportunityAiFilterError, filter_opportunities_with_ai
from config import (
    AI_FILTER_MAX_CANDIDATES,
    ANALYSIS_SCHEDULE_MAX_ITEMS,
    ANALYSIS_SCHEDULE_STALE_HOURS,
    SOURCES_CONFIG,
)
from product_selection.repository import ProductSelectionRepository
from product_selection.service import ProductSelectionService

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
    stage: Optional[str] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    remind_at: Optional[str] = None
    block_reason: Optional[str] = None
    abandon_reason: Optional[str] = None


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


class AgentAnalysisJobCreateRequest(BaseModel):
    scope_type: Literal["single", "batch"]
    trigger_type: Literal["manual", "scheduled"]
    activity_ids: List[str] = []
    template_id: Optional[str] = None
    requested_by: Optional[str] = None


class AgentAnalysisReviewRequest(BaseModel):
    review_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    edited_snapshot: Optional[dict] = None


class OpportunityAiFilterRequest(BaseModel):
    base_filters: Dict[str, Any] = {}
    query: str


class AgentSessionCreateRequest(BaseModel):
    domain_type: str
    entry_mode: str = "chat"
    title: Optional[str] = None


class AgentTurnCreateRequest(BaseModel):
    content: str


class ProductSelectionResearchJobCreateRequest(BaseModel):
    query_type: Literal["keyword", "category", "listing_url"] = "keyword"
    query_text: str
    platform_scope: Literal["taobao", "xianyu", "both"] = "both"
    rendered_snapshot_html: Optional[str] = None
    rendered_snapshot_path: Optional[str] = None
    detail_snapshot_htmls: List[str] = []
    detail_snapshot_manifest_path: Optional[str] = None


class ProductSelectionTrackingUpsertRequest(BaseModel):
    is_favorited: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    remind_at: Optional[str] = None


def _serialize_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _get_agent_repository(request: Request) -> AgentPlatformRepository:
    repository = getattr(request.app.state, "agent_platform_repository", None)
    data_manager = getattr(request.app.state, "data_manager", None)
    if data_manager is None:
        raise RuntimeError("Data manager is not initialized")

    if repository is None or getattr(repository, "db_path", None) != data_manager.db_path:
        repository = AgentPlatformRepository(data_manager.db_path)
        request.app.state.agent_platform_repository = repository

    return repository


def _get_tool_router(request: Request) -> ToolRouter:
    tool_router = getattr(request.app.state, "agent_tool_router", None)
    data_manager = getattr(request.app.state, "data_manager", None)
    if data_manager is None:
        raise RuntimeError("Data manager is not initialized")

    registry_key = getattr(data_manager, "db_path", None)
    if tool_router is None or getattr(tool_router, "registry_key", None) != registry_key:
        tool_router = ToolRouter(
            tool_registry=build_default_registry(data_manager=data_manager),
            registry_key=registry_key,
        )
        request.app.state.agent_tool_router = tool_router
    return tool_router


def _get_conversation_engine(request: Request) -> ConversationEngine:
    tool_router = _get_tool_router(request)
    engine = getattr(request.app.state, "agent_conversation_engine", None)
    if engine is None or getattr(engine, "tool_router", None) is not tool_router:
        engine = ConversationEngine(tool_router=tool_router)
        request.app.state.agent_conversation_engine = engine
    return engine


def _get_artifact_service(request: Request) -> ArtifactService:
    artifact_service = getattr(request.app.state, "agent_artifact_service", None)
    repository = _get_agent_repository(request)
    if artifact_service is None or getattr(artifact_service, "repository", None) is not repository:
        artifact_service = ArtifactService(repository=repository)
        request.app.state.agent_artifact_service = artifact_service
    return artifact_service


def _get_product_selection_repository(request: Request) -> ProductSelectionRepository:
    repository = getattr(request.app.state, "product_selection_repository", None)
    data_manager = getattr(request.app.state, "data_manager", None)
    if data_manager is None:
        raise RuntimeError("Data manager is not initialized")

    if repository is None or getattr(repository, "db_path", None) != data_manager.db_path:
        repository = ProductSelectionRepository(data_manager.db_path)
        request.app.state.product_selection_repository = repository

    return repository


def _get_product_selection_service(request: Request) -> ProductSelectionService:
    repository = _get_product_selection_repository(request)
    service = getattr(request.app.state, "product_selection_service", None)
    if service is None or getattr(service, "repository", None) is not repository:
        service = ProductSelectionService(repository=repository)
        request.app.state.product_selection_service = service
    return service


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


@app.post("/api/agent/sessions")
async def create_agent_session(request: Request, payload: AgentSessionCreateRequest):
    repository = _get_agent_repository(request)
    session = repository.create_session(
        domain_type=payload.domain_type,
        entry_mode=payload.entry_mode,
        title=payload.title,
    )
    return _serialize_model(session)


@app.get("/api/agent/sessions")
async def list_agent_sessions(
    request: Request,
    domain_type: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    return repository.list_sessions(domain_type=domain_type, limit=limit)


@app.get("/api/agent/sessions/{session_id}")
async def get_agent_session(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return _serialize_model(session)


@app.post("/api/agent/sessions/{session_id}/turns")
async def post_agent_turn(request: Request, session_id: str, payload: AgentTurnCreateRequest):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")

    user_turn = repository.append_turn(session_id, role="user", content=payload.content)
    reply = _get_conversation_engine(request).reply(session=session, user_turn=user_turn)
    assistant_turn = repository.append_turn(session_id, role="assistant", content=reply.assistant_turn)
    artifacts = _get_artifact_service(request).persist(session_id, reply.artifacts)

    if reply.next_state != session.status:
        session = repository.update_session_status(session_id, status=reply.next_state)
    else:
        session = repository.get_session(session_id) or session

    turns = repository.list_turns(session_id)
    return {
        "session": _serialize_model(session),
        "user_turn": _serialize_model(user_turn),
        "assistant_turn": _serialize_model(assistant_turn),
        "artifacts": [_serialize_model(artifact) for artifact in artifacts],
        "tool_calls": reply.tool_calls,
        "turns": [_serialize_model(turn) for turn in turns],
    }


@app.get("/api/agent/sessions/{session_id}/turns")
async def list_agent_turns(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [_serialize_model(turn) for turn in repository.list_turns(session_id)]


@app.get("/api/agent/sessions/{session_id}/artifacts")
async def list_agent_artifacts(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [
        _serialize_model(artifact)
        for artifact in _get_artifact_service(request).list_for_session(session_id)
    ]


@app.post("/api/product-selection/research-jobs")
async def create_product_selection_research_job(
    request: Request,
    payload: ProductSelectionResearchJobCreateRequest,
):
    service = _get_product_selection_service(request)
    try:
        service.validate_query_payload(payload.query_type, payload.platform_scope, payload.query_text)
        return service.start_research_job(
            query_type=payload.query_type,
            query_text=payload.query_text,
            platform_scope=payload.platform_scope,
            rendered_snapshot_html=payload.rendered_snapshot_html,
            rendered_snapshot_path=payload.rendered_snapshot_path,
            detail_snapshot_htmls=payload.detail_snapshot_htmls,
            detail_snapshot_manifest_path=payload.detail_snapshot_manifest_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/product-selection/research-jobs/{job_id}")
async def get_product_selection_research_job(request: Request, job_id: str):
    try:
        return _get_product_selection_service(request).get_research_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/product-selection/opportunities")
async def list_product_selection_opportunities(
    request: Request,
    query_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    risk_tag: Optional[str] = Query(None),
    source_mode: Optional[str] = Query(None),
    fallback_reason: Optional[str] = Query(None),
    sort_by: str = Query("opportunity_score"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return _get_product_selection_service(request).list_opportunities(
        query_id=query_id,
        platform=platform,
        search=search,
        risk_tag=risk_tag.lower() if risk_tag else None,
        source_mode=source_mode.lower() if source_mode else None,
        fallback_reason=fallback_reason.lower() if fallback_reason else None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@app.get("/api/product-selection/opportunities/{opportunity_id}")
async def get_product_selection_opportunity(request: Request, opportunity_id: str):
    detail = _get_product_selection_service(request).get_opportunity_detail(opportunity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Product selection opportunity not found")
    return detail


@app.get("/api/product-selection/tracking")
async def list_product_selection_tracking(
    request: Request,
    status: Optional[str] = Query(None),
    source_mode: Optional[str] = Query(None),
    fallback_reason: Optional[str] = Query(None),
):
    return _get_product_selection_repository(request).list_tracking(
        status=status,
        source_mode=source_mode.lower() if source_mode else None,
        fallback_reason=fallback_reason.lower() if fallback_reason else None,
    )


@app.post("/api/product-selection/tracking/{opportunity_id}")
async def create_product_selection_tracking(
    request: Request,
    opportunity_id: str,
    payload: ProductSelectionTrackingUpsertRequest,
):
    try:
        return _get_product_selection_repository(request).upsert_tracking(
            opportunity_id,
            payload.model_dump(exclude_none=True),
        ).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/product-selection/tracking/{opportunity_id}")
async def update_product_selection_tracking(
    request: Request,
    opportunity_id: str,
    payload: ProductSelectionTrackingUpsertRequest,
):
    try:
        return _get_product_selection_repository(request).upsert_tracking(
            opportunity_id,
            payload.model_dump(exclude_none=True),
        ).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/product-selection/tracking/{opportunity_id}")
async def delete_product_selection_tracking(request: Request, opportunity_id: str):
    deleted = _get_product_selection_repository(request).delete_tracking(opportunity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product selection tracking item not found")
    return {"success": True}


@app.get("/api/product-selection/workspace")
async def get_product_selection_workspace(request: Request):
    return _get_product_selection_service(request).get_workspace()


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
    prize_range: Optional[str] = Query(None),
    solo_friendliness: Optional[str] = Query(None),
    reward_clarity: Optional[str] = Query(None),
    effort_level: Optional[str] = Query(None),
    remote_mode: Optional[str] = Query(None),
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
    if prize_range:
        filters["prize_range"] = prize_range
    if solo_friendliness:
        filters["solo_friendliness"] = solo_friendliness
    if reward_clarity:
        filters["reward_clarity"] = reward_clarity
    if effort_level:
        filters["effort_level"] = effort_level
    if remote_mode:
        filters["remote_mode"] = remote_mode
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


@app.post("/api/activities/ai-filter")
async def ai_filter_activities(request: Request, payload: OpportunityAiFilterRequest):
    base_filters = dict(payload.base_filters or {})
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="请输入 AI 精筛条件。")

    sort_by = str(base_filters.pop("sort_by", "score"))
    sort_order = str(base_filters.pop("sort_order", "desc"))
    base_filters.pop("page", None)
    base_filters.pop("page_size", None)

    candidates, total = request.app.state.data_manager.get_activities(
        filters=base_filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=1,
        page_size=AI_FILTER_MAX_CANDIDATES + 1,
    )

    if total > AI_FILTER_MAX_CANDIDATES:
        raise HTTPException(
            status_code=400,
            detail="当前候选机会过多，请先通过分类、截止时间、奖金区间等条件缩小范围后再进行 AI 精筛。",
        )

    try:
        result = filter_opportunities_with_ai(candidates=candidates, query=query)
    except ValueError as exc:
        if "candidate limit" in str(exc):
            raise HTTPException(
                status_code=400,
                detail="当前候选机会过多，请先通过分类、截止时间、奖金区间等条件缩小范围后再进行 AI 精筛。",
            ) from exc
        raise
    except OpportunityAiFilterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    candidates_by_id = {activity.id: activity for activity in candidates}
    merged_items = []
    for item in result["items"]:
        activity = candidates_by_id.get(item["id"])
        if activity is None:
            continue
        merged_items.append(
            {
                **_serialize_model(activity),
                "ai_match_reason": item["ai_match_reason"],
                "ai_match_confidence": item["ai_match_confidence"],
                "uncertainties": item.get("uncertainties", []),
            }
        )

    return {
        **result,
        "items": merged_items,
        "matched_count": len(merged_items),
        "discarded_count": max(total - len(merged_items), 0),
        "candidate_count": total,
    }


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


@app.post("/api/agent-analysis/jobs")
async def create_agent_analysis_job(request: Request, payload: AgentAnalysisJobCreateRequest):
    run_manager = getattr(request.app.state, "analysis_run_manager", None)
    if run_manager is None or getattr(run_manager, "data_manager", None) is not request.app.state.data_manager:
        run_manager = AnalysisRunManager(data_manager=request.app.state.data_manager)
        request.app.state.analysis_run_manager = run_manager

    try:
        if payload.scope_type == "single" and payload.trigger_type == "manual":
            if len(payload.activity_ids) != 1:
                raise HTTPException(status_code=400, detail="Manual single-item jobs require exactly one activity id")
            return run_manager.run_single_job(
                activity_id=payload.activity_ids[0],
                template_id=payload.template_id,
                requested_by=payload.requested_by,
                trigger_type=payload.trigger_type,
            )
        if payload.scope_type == "batch":
            return run_manager.run_batch_job(
                template_id=payload.template_id,
                requested_by=payload.requested_by,
                trigger_type=payload.trigger_type,
                activity_ids=payload.activity_ids or None,
                max_items=ANALYSIS_SCHEDULE_MAX_ITEMS,
                stale_before_hours=ANALYSIS_SCHEDULE_STALE_HOURS,
            )
        raise HTTPException(status_code=400, detail="Unsupported agent-analysis job mode")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/agent-analysis/jobs")
async def list_agent_analysis_jobs(request: Request):
    return request.app.state.data_manager.list_analysis_jobs()


@app.get("/api/agent-analysis/jobs/{job_id}")
async def get_agent_analysis_job(request: Request, job_id: str):
    detail = request.app.state.data_manager.get_analysis_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Agent analysis job not found")
    return detail


@app.get("/api/agent-analysis/items/{item_id}")
async def get_agent_analysis_item(request: Request, item_id: str):
    detail = request.app.state.data_manager.get_analysis_item_detail(item_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Agent analysis item not found")
    return detail


@app.post("/api/agent-analysis/items/{item_id}/approve")
async def approve_agent_analysis_item(
    request: Request,
    item_id: str,
    payload: AgentAnalysisReviewRequest,
):
    review_service = getattr(request.app.state, "review_service", None)
    if review_service is None or getattr(review_service, "data_manager", None) is not request.app.state.data_manager:
        review_service = ReviewService(data_manager=request.app.state.data_manager)
        request.app.state.review_service = review_service

    try:
        result = review_service.approve_item(
            item_id,
            review_note=payload.review_note,
            reviewed_by=payload.reviewed_by,
            edited_snapshot=payload.edited_snapshot,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@app.post("/api/agent-analysis/items/{item_id}/reject")
async def reject_agent_analysis_item(
    request: Request,
    item_id: str,
    payload: AgentAnalysisReviewRequest,
):
    review_service = getattr(request.app.state, "review_service", None)
    if review_service is None or getattr(review_service, "data_manager", None) is not request.app.state.data_manager:
        review_service = ReviewService(data_manager=request.app.state.data_manager)
        request.app.state.review_service = review_service

    try:
        result = review_service.reject_item(
            item_id,
            review_note=payload.review_note,
            reviewed_by=payload.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.model_dump(mode="json")


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
