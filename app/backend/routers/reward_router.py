"""
Reward opportunity router - handles all /api/reward-opportunities/* and /a2a/* endpoints.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from config import A2A_BASE_URL
from reward_opportunity.repository import RewardOpportunityRepository
from reward_opportunity.service import RewardOpportunityService
from reward_opportunity.a2a import build_a2a_task_response, build_reward_agent_cards, get_reward_agent_card

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reward-opportunities", tags=["reward"])


# --- Pydantic Models ---


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


# --- Helper Functions ---


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


# --- Endpoints ---


@router.get("/overview")
async def get_reward_opportunity_overview(request: Request):
    return _get_reward_opportunity_service(request).get_overview()


@router.get("")
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


@router.get("/operations")
async def get_reward_opportunity_operations(request: Request):
    return _get_reward_opportunity_service(request).get_operations()


@router.get("/discovery")
async def get_reward_opportunity_source_discovery(request: Request):
    return _get_reward_opportunity_service(request).get_source_discovery()


@router.get("/discovery/settings")
async def get_reward_opportunity_scout_settings(request: Request):
    return _get_reward_opportunity_service(request).get_scout_settings()


@router.put("/discovery/settings")
async def update_reward_opportunity_scout_settings(request: Request, payload: RewardScoutSettingsRequest):
    return _get_reward_opportunity_service(request).update_scout_settings(payload.query_templates)


@router.post("/discovery/import")
async def import_reward_opportunity_source(request: Request, payload: RewardSourceImportRequest):
    try:
        return _get_reward_opportunity_service(request).import_discovered_source(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/discovery/ignore")
async def ignore_reward_opportunity_discovery_candidate(request: Request, payload: RewardDiscoveryIgnoreRequest):
    try:
        return _get_reward_opportunity_service(request).ignore_discovery_candidate(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/discovery/unignore")
async def unignore_reward_opportunity_discovery_candidate(request: Request, payload: RewardDiscoveryIgnoreRequest):
    try:
        return _get_reward_opportunity_service(request).unignore_discovery_candidate(payload.dedupe_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync")
async def sync_reward_opportunities(request: Request):
    return _get_reward_opportunity_service(request).sync_sources()


@router.post("/sync/{source_feed_id}")
async def sync_single_reward_opportunity_source(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).sync_single_source(source_feed_id, mode="manual_single")
    except ValueError as exc:
        status_code = 400 if str(exc) == "source feed is paused" else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/sources/{source_feed_id}/pause")
async def pause_reward_opportunity_source(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).set_source_feed_paused(source_feed_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sources/{source_feed_id}/resume")
async def resume_reward_opportunity_source(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).set_source_feed_paused(source_feed_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sources/{source_feed_id}")
async def get_reward_opportunity_source_detail(request: Request, source_feed_id: str):
    try:
        return _get_reward_opportunity_service(request).get_source_detail(source_feed_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/sources/{source_feed_id}")
async def update_reward_opportunity_source(request: Request, source_feed_id: str, payload: RewardSourceUpdateRequest):
    try:
        return _get_reward_opportunity_service(request).update_source(source_feed_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/sources/{source_feed_id}/schedule")
async def update_reward_opportunity_source_schedule(
    request: Request, source_feed_id: str, payload: RewardSourceScheduleRequest
):
    try:
        return _get_reward_opportunity_service(request).update_source_schedule(source_feed_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sources/{source_feed_id}/recommended-action")
async def execute_reward_opportunity_source_action(
    request: Request, source_feed_id: str, payload: RewardRecommendedActionRequest
):
    try:
        return _get_reward_opportunity_service(request).execute_recommended_action(source_feed_id, payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{opportunity_id}")
async def get_reward_opportunity_detail(request: Request, opportunity_id: str):
    detail = _get_reward_opportunity_service(request).get_opportunity(opportunity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Reward opportunity not found")
    return detail


# --- A2A Endpoints (separate router, no prefix) ---

a2a_router = APIRouter(tags=["reward-a2a"])


@a2a_router.get("/a2a")
async def list_reward_a2a_agent_cards():
    return {"agents": build_reward_agent_cards(A2A_BASE_URL)}


@a2a_router.get("/a2a/{agent_name}/.well-known/agent-card.json")
async def get_reward_a2a_agent_card(agent_name: str):
    try:
        return get_reward_agent_card(A2A_BASE_URL, agent_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@a2a_router.post("/a2a/{agent_name}")
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
            )
        else:
            raise KeyError(f"Unknown reward agent: {agent_name}")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return build_a2a_task_response(payload.id, result)
