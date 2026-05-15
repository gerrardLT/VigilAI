"""
REST API for VigilAI.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import List, Literal, Optional

from agent_platform.artifact_service import ArtifactService
from agent_platform.conversation_engine import ConversationEngine
from agent_platform.repository import AgentPlatformRepository
from agent_platform.tool_router import ToolRouter, build_default_registry
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    A2A_BASE_URL,
    SOURCES_CONFIG,
)
from product_selection.repository import ProductSelectionRepository
from product_selection.service import ProductSelectionService
from reward_opportunity.repository import RewardOpportunityRepository
from reward_opportunity.service import RewardOpportunityService
from reward_opportunity.a2a import build_a2a_task_response, build_reward_agent_cards, get_reward_agent_card

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


class RewardSourceImportRequest(BaseModel):
    name: str
    entry_url: str
    source_type: str = "web"
    source_platform: Optional[str] = None
    discovery_queries: List[str] = []


class RewardScoutSettingsRequest(BaseModel):
    query_templates: List[str] = []


class A2AMessageRequest(BaseModel):
    id: str = "reward-task"
    params: dict = {}


class RewardSourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    source_type: Optional[str] = None
    source_platform: Optional[str] = None
    entry_url: Optional[str] = None
    merge_group_key: Optional[str] = None
    preferred_entry_url: Optional[str] = None


class RewardSourceScheduleRequest(BaseModel):
    auto_sync_enabled: bool
    sync_interval_minutes: int


class RewardRecommendedActionRequest(BaseModel):
    action: str


class RewardDiscoveryIgnoreRequest(BaseModel):
    dedupe_key: str
    entry_url: str
    reason: Optional[str] = None


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


def _get_reward_opportunity_repository(request: Request) -> RewardOpportunityRepository:
    repository = getattr(request.app.state, "reward_opportunity_repository", None)
    data_manager = getattr(request.app.state, "data_manager", None)
    if data_manager is None:
        raise RuntimeError("Data manager is not initialized")

    if repository is None or getattr(repository, "db_path", None) != data_manager.db_path:
        repository = RewardOpportunityRepository(data_manager.db_path)
        request.app.state.reward_opportunity_repository = repository

    return repository


def _get_reward_opportunity_service(request: Request) -> RewardOpportunityService:
    repository = _get_reward_opportunity_repository(request)
    service = getattr(request.app.state, "reward_opportunity_service", None)
    if service is None or getattr(service, "repository", None) is not repository:
        service = RewardOpportunityService(repository=repository)
        request.app.state.reward_opportunity_service = service
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


@app.get("/api/reward-opportunities/overview")
async def get_reward_opportunity_overview(request: Request):
    return _get_reward_opportunity_service(request).get_overview()


@app.get("/api/reward-opportunities")
async def list_reward_opportunities(
    request: Request,
    classification: str | None = Query(None),
    source_platform: str | None = Query(None),
    opportunity_type: str | None = Query(None),
    reward_type: str | None = Query(None),
    evidence_status: str | None = Query(None),
    sort_by: str = Query("created_at"),
):
    return _get_reward_opportunity_service(request).list_opportunities(
        classification=classification,
        source_platform=source_platform,
        opportunity_type=opportunity_type,
        reward_type=reward_type,
        evidence_status=evidence_status,
        sort_by=sort_by,
    )


@app.get("/api/reward-opportunities/operations")
async def get_reward_opportunity_operations(request: Request):
    return _get_reward_opportunity_service(request).get_operations()


@app.get("/api/reward-opportunities/discovery")
async def get_reward_opportunity_source_discovery(request: Request):
    return _get_reward_opportunity_service(request).get_source_discovery()


@app.get("/api/reward-opportunities/discovery/settings")
async def get_reward_opportunity_scout_settings(request: Request):
    return _get_reward_opportunity_service(request).get_scout_settings()


@app.put("/api/reward-opportunities/discovery/settings")
async def update_reward_opportunity_scout_settings(request: Request, payload: RewardScoutSettingsRequest):
    return _get_reward_opportunity_service(request).update_scout_settings(payload.query_templates)


@app.post("/api/reward-opportunities/discovery/import")
async def import_reward_opportunity_source(request: Request, payload: RewardSourceImportRequest):
    try:
        return _get_reward_opportunity_service(request).import_discovered_source(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/reward-opportunities/discovery/ignore")
async def ignore_reward_opportunity_discovery_candidate(request: Request, payload: RewardDiscoveryIgnoreRequest):
    try:
        return _get_reward_opportunity_service(request).ignore_discovery_candidate(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/reward-opportunities/discovery/unignore")
async def unignore_reward_opportunity_discovery_candidate(request: Request, payload: RewardDiscoveryIgnoreRequest):
    try:
        return _get_reward_opportunity_service(request).unignore_discovery_candidate(payload.dedupe_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/reward-opportunities/sync")
async def sync_reward_opportunities(request: Request):
    return _get_reward_opportunity_service(request).sync_sources()


@app.post("/api/reward-opportunities/sync/{source_feed_id}")
async def sync_single_reward_opportunity_source(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).sync_single_source(source_feed_id, mode="manual_single")
    except ValueError as exc:
        status_code = 400 if str(exc) == "source feed is paused" else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.post("/api/reward-opportunities/sources/{source_feed_id}/pause")
async def pause_reward_opportunity_source(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).set_source_feed_paused(source_feed_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/reward-opportunities/sources/{source_feed_id}/resume")
async def resume_reward_opportunity_source(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).set_source_feed_paused(source_feed_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/reward-opportunities/sources/{source_feed_id}")
async def get_reward_opportunity_source_detail(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).get_source_detail(source_feed_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/reward-opportunities/sources/{source_feed_id}")
async def update_reward_opportunity_source(request: Request, source_feed_id: str, payload: RewardSourceUpdateRequest):
    try:
        return _get_reward_opportunity_service(request).update_source(source_feed_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/reward-opportunities/sources/{source_feed_id}/schedule")
async def update_reward_opportunity_source_schedule(
    request: Request, source_feed_id: str, payload: RewardSourceScheduleRequest
):
    try:
        return _get_reward_opportunity_service(request).update_source_schedule(source_feed_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/reward-opportunities/sources/{source_feed_id}/recommended-action")
async def execute_reward_opportunity_source_action(
    request: Request, source_feed_id: str, payload: RewardRecommendedActionRequest
):
    try:
        return _get_reward_opportunity_service(request).execute_recommended_action(source_feed_id, payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/a2a")
async def list_reward_a2a_agent_cards():
    return {"agents": build_reward_agent_cards(A2A_BASE_URL)}


@app.get("/a2a/{agent_name}/.well-known/agent-card.json")
async def get_reward_a2a_agent_card(agent_name: str):
    try:
        return get_reward_agent_card(A2A_BASE_URL, agent_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/a2a/{agent_name}")
async def send_reward_a2a_message(request: Request, agent_name: str, payload: A2AMessageRequest):
    from reward_opportunity.agent_loop import run_investigation_cycle
    from reward_opportunity.browser_collector import BrowserCollectConstraints, browser_collect

    data = payload.params.get("data") or payload.params
    try:
        if agent_name == "RewardScoutAgent":
            result = _get_reward_opportunity_service(request).get_source_discovery()
        elif agent_name == "RewardBrowserInvestigatorAgent":
            result = browser_collect(
                str(data["url"]),
                str(data.get("objective") or "Collect reward opportunity evidence"),
                constraints=BrowserCollectConstraints(allowed_domains=list(data.get("allowed_domains") or [])),
            )
        elif agent_name == "RewardVerdictAgent":
            result = run_investigation_cycle(
                candidate=dict(data.get("candidate") or {}),
                evidence_bundle=dict(data.get("evidence_bundle") or {}),
                max_rounds=int(data.get("max_rounds") or 0),
            )
        else:
            raise KeyError(f"Unknown reward agent: {agent_name}")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return build_a2a_task_response(payload.id, result)


@app.get("/api/reward-opportunities/{opportunity_id}")
async def get_reward_opportunity_detail(request: Request, opportunity_id: str):
    detail = _get_reward_opportunity_service(request).get_opportunity(opportunity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Reward opportunity not found")
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


