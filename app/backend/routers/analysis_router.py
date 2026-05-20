"""
Analysis router - handles /api/stats, /api/analysis/*, /api/agent-analysis/* endpoints.
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from analysis.run_manager import AnalysisRunManager
from analysis.review_service import ReviewService
from config import ANALYSIS_SCHEDULE_MAX_ITEMS, ANALYSIS_SCHEDULE_STALE_HOURS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


# --- Pydantic Models ---


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


# --- Endpoints ---


@router.get("/api/stats")
async def get_stats(request: Request):
    return request.app.state.data_manager.get_stats().model_dump(mode="json")


@router.get("/api/analysis/templates")
async def list_analysis_templates(request: Request):
    return request.app.state.data_manager.get_analysis_templates()


@router.get("/api/analysis/templates/default")
async def get_default_analysis_template(request: Request):
    template = request.app.state.data_manager.get_default_analysis_template()
    if template is None:
        raise HTTPException(status_code=404, detail="默认分析模板不存在")
    return template


@router.post("/api/analysis/templates")
async def create_analysis_template(request: Request, payload: AnalysisTemplateCreateRequest):
    return request.app.state.data_manager.create_analysis_template(payload.model_dump(exclude_none=True))


@router.post("/api/analysis/templates/{template_id}/duplicate")
async def duplicate_analysis_template(
    request: Request,
    template_id: str,
    payload: AnalysisTemplateDuplicateRequest,
):
    try:
        return request.app.state.data_manager.duplicate_analysis_template(template_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/analysis/templates/{template_id}/activate")
async def activate_analysis_template(request: Request, template_id: str):
    try:
        return request.app.state.data_manager.set_default_analysis_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/api/analysis/templates/{template_id}")
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


@router.delete("/api/analysis/templates/{template_id}")
async def delete_analysis_template(request: Request, template_id: str):
    try:
        request.app.state.data_manager.delete_analysis_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True}


@router.post("/api/analysis/templates/preview", response_model=AnalysisTemplatePreviewResponse)
async def preview_analysis_template_payload(
    request: Request,
    payload: AnalysisTemplatePreviewRequest,
):
    return request.app.state.data_manager.preview_analysis_template_payload(
        payload.model_dump(exclude_none=True)
    )


@router.post("/api/analysis/templates/preview/results", response_model=AnalysisTemplatePreviewResultsResponse)
async def preview_analysis_template_payload_results(
    request: Request,
    payload: AnalysisTemplatePreviewRequest,
):
    return request.app.state.data_manager.preview_analysis_template_payload_results(
        payload.model_dump(exclude_none=True)
    )


@router.get("/api/analysis/templates/{template_id}/preview", response_model=AnalysisTemplatePreviewResponse)
async def preview_analysis_template(request: Request, template_id: str):
    try:
        return request.app.state.data_manager.preview_analysis_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/analysis/run", response_model=AnalysisRunResponse)
async def run_analysis_for_all_activities(request: Request):
    processed = request.app.state.data_manager.rerun_analysis_for_all_activities()
    return AnalysisRunResponse(success=True, processed=processed)


@router.get("/api/analysis/results")
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


@router.get("/api/analysis/results/{activity_id}")
async def get_analysis_result_detail(request: Request, activity_id: str):
    detail = request.app.state.data_manager.get_activity_detail(activity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    return detail


@router.post("/api/agent-analysis/jobs")
async def create_agent_analysis_job(request: Request, payload: AgentAnalysisJobCreateRequest):
    run_manager = getattr(request.app.state, "analysis_run_manager", None)
    if run_manager is None or getattr(run_manager, "data_manager", None) is not request.app.state.data_manager:
        run_manager = AnalysisRunManager(data_manager=request.app.state.data_manager)
        request.app.state.analysis_run_manager = run_manager

    try:
        if payload.scope_type == "single" and payload.trigger_type == "manual":
            if len(payload.activity_ids) != 1:
                raise HTTPException(status_code=400, detail="手动单项任务必须且只能提供一个 activity id")
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
        raise HTTPException(status_code=400, detail="不支持的 Agent 分析任务模式")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/agent-analysis/jobs")
async def list_agent_analysis_jobs(request: Request):
    return request.app.state.data_manager.list_analysis_jobs()


@router.get("/api/agent-analysis/jobs/{job_id}")
async def get_agent_analysis_job(request: Request, job_id: str):
    detail = request.app.state.data_manager.get_analysis_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Agent 分析任务不存在")
    return detail


@router.get("/api/agent-analysis/items/{item_id}")
async def get_agent_analysis_item(request: Request, item_id: str):
    detail = request.app.state.data_manager.get_analysis_item_detail(item_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Agent 分析项不存在")
    return detail


@router.post("/api/agent-analysis/items/{item_id}/approve")
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


@router.post("/api/agent-analysis/items/{item_id}/reject")
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
