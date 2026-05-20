"""
Opportunity router - handles /api/activities/*, /api/workspace, /api/tracking/*, /api/digests/* endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from analysis.opportunity_ai_filter import OpportunityAiFilterError, filter_opportunities_with_ai
from config import AI_FILTER_MAX_CANDIDATES

logger = logging.getLogger(__name__)

router = APIRouter(tags=["opportunity"])


# --- Pydantic Models ---


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


class OpportunityAiFilterRequest(BaseModel):
    base_filters: Dict[str, Any] = {}
    query: str


# --- Helper ---


def _serialize_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


# --- Endpoints ---


@router.get("/api/workspace")
async def get_workspace(request: Request):
    return request.app.state.data_manager.get_workspace()


@router.get("/api/activities")
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


@router.get("/api/activities/{activity_id}")
async def get_activity(request: Request, activity_id: str):
    detail = request.app.state.data_manager.get_activity_detail(activity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return detail


@router.post("/api/activities/ai-filter")
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


@router.get("/api/tracking")
async def get_tracking(request: Request, status: Optional[str] = Query(None)):
    return request.app.state.data_manager.get_tracking_items(status=status)


@router.post("/api/tracking/{activity_id}")
async def create_tracking(request: Request, activity_id: str, payload: TrackingUpsertRequest):
    try:
        tracking = request.app.state.data_manager.upsert_tracking_item(activity_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return tracking.model_dump()


@router.patch("/api/tracking/{activity_id}")
async def update_tracking(request: Request, activity_id: str, payload: TrackingUpsertRequest):
    try:
        tracking = request.app.state.data_manager.upsert_tracking_item(activity_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return tracking.model_dump()


@router.delete("/api/tracking/{activity_id}")
async def delete_tracking(request: Request, activity_id: str):
    deleted = request.app.state.data_manager.delete_tracking_item(activity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="跟进项不存在")
    return {"success": True}


@router.get("/api/digests")
async def list_digests(request: Request):
    return [_serialize_model(digest) for digest in request.app.state.data_manager.get_digests()]


@router.get("/api/digests/candidates")
async def list_digest_candidates(request: Request, digest_date: Optional[str] = Query(None)):
    candidates = request.app.state.data_manager.get_digest_candidates(digest_date)
    return [_serialize_model(candidate) for candidate in candidates]


@router.post("/api/digests/candidates/{activity_id}")
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


@router.delete("/api/digests/candidates/{activity_id}")
async def remove_digest_candidate(
    request: Request,
    activity_id: str,
    digest_date: Optional[str] = Query(None),
):
    deleted = request.app.state.data_manager.remove_digest_candidate(activity_id, digest_date)
    if not deleted:
        raise HTTPException(status_code=404, detail="日报候选项不存在")
    return {"success": True}


@router.get("/api/digests/{digest_id}")
async def get_digest(request: Request, digest_id: str):
    digest = request.app.state.data_manager.get_digest_by_id(digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="日报不存在")
    return digest.model_dump()


@router.post("/api/digests/generate")
async def generate_digest(request: Request, payload: Optional[DigestGenerateRequest] = None):
    digest_date = payload.digest_date if payload else None
    digest = request.app.state.data_manager.generate_digest(digest_date)
    return digest.model_dump()


@router.post("/api/digests/{digest_id}/send")
async def send_digest(request: Request, digest_id: str, payload: DigestSendRequest):
    try:
        digest = request.app.state.data_manager.mark_digest_sent(digest_id, payload.send_channel)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return digest.model_dump()


# --- Action Automation Endpoints ---


@router.get("/api/opportunities/{activity_id}/actions")
async def get_opportunity_actions(request: Request, activity_id: str):
    """Get recommended actions for an opportunity."""
    activity = request.app.state.data_manager.get_activity_detail(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="活动不存在")

    from services.action_automator import ActionAutomator

    pool = request.app.state.data_manager._pool
    automator = ActionAutomator(pool)

    # Get both generated recommendations and executed history
    generated = await automator.generate_actions(
        activity if isinstance(activity, dict) else activity.model_dump() if hasattr(activity, "model_dump") else {}
    )
    executed = await automator.list_actions(activity_id)

    return {"generated": generated, "executed": executed}


@router.post("/api/opportunities/{activity_id}/actions/{action_type}")
async def execute_opportunity_action(request: Request, activity_id: str, action_type: str):
    """Execute a recommended action for an opportunity."""
    activity = request.app.state.data_manager.get_activity_detail(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="活动不存在")

    from services.action_automator import ActionAutomator, ActionType

    # Validate action type
    valid_types = [t.value for t in ActionType]
    if action_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的操作类型: {action_type}")

    pool = request.app.state.data_manager._pool
    automator = ActionAutomator(pool)
    result = await automator.execute_action(activity_id, action_type)
    return result
