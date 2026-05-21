"""
Product selection router - handles all /api/product-selection/* endpoints.
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from product_selection.repository import ProductSelectionRepository
from product_selection.service import ProductSelectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/product-selection", tags=["product-selection"])


# --- Pydantic Models ---


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


class ProductSelectionAutomationRunRequest(BaseModel):
    query_limit: int = 5
    max_tracked_items: int = 3
    min_opportunity_score: float = 70
    min_confidence_score: float = 60
    requested_by: Optional[str] = "manual"


class ProductSelectionOperationsRunRequest(BaseModel):
    max_items: int = 5
    stale_after_hours: int = 48
    remind_after_hours: int = 24
    requested_by: Optional[str] = "manual"


# --- Helper Functions ---


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


# --- Endpoints ---


@router.post("/research-jobs")
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


@router.get("/research-jobs/{job_id}")
async def get_product_selection_research_job(request: Request, job_id: str):
    try:
        return _get_product_selection_service(request).get_research_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities")
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


@router.get("/opportunities/{opportunity_id}")
async def get_product_selection_opportunity(request: Request, opportunity_id: str):
    detail = _get_product_selection_service(request).get_opportunity_detail(opportunity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="选品机会不存在")
    return detail


@router.get("/tracking")
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


@router.post("/tracking/{opportunity_id}")
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


@router.patch("/tracking/{opportunity_id}")
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


@router.delete("/tracking/{opportunity_id}")
async def delete_product_selection_tracking(request: Request, opportunity_id: str):
    deleted = _get_product_selection_repository(request).delete_tracking(opportunity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="选品跟进项不存在")
    return {"success": True}


@router.get("/workspace")
async def get_product_selection_workspace(request: Request):
    return _get_product_selection_service(request).get_workspace()


@router.post("/automation/runs")
async def create_product_selection_automation_run(
    request: Request,
    payload: ProductSelectionAutomationRunRequest,
):
    return _get_product_selection_service(request).run_automation_cycle(
        query_limit=payload.query_limit,
        max_tracked_items=payload.max_tracked_items,
        min_opportunity_score=payload.min_opportunity_score,
        min_confidence_score=payload.min_confidence_score,
        requested_by=payload.requested_by or "manual",
    )


@router.get("/automation/runs")
async def list_product_selection_automation_runs(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
):
    return _get_product_selection_service(request).list_automation_runs(limit=limit)


@router.get("/automation/runs/{job_id}")
async def get_product_selection_automation_run(request: Request, job_id: str):
    try:
        return _get_product_selection_service(request).get_automation_run(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/operations/runs")
async def create_product_selection_operations_run(
    request: Request,
    payload: ProductSelectionOperationsRunRequest,
):
    return _get_product_selection_service(request).run_operations_cycle(
        max_items=payload.max_items,
        stale_after_hours=payload.stale_after_hours,
        remind_after_hours=payload.remind_after_hours,
        requested_by=payload.requested_by or "manual",
    )


@router.get("/operations/runs")
async def list_product_selection_operations_runs(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
):
    return _get_product_selection_service(request).list_operations_runs(limit=limit)


@router.get("/operations/runs/{job_id}")
async def get_product_selection_operations_run(request: Request, job_id: str):
    try:
        return _get_product_selection_service(request).get_operations_run(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
