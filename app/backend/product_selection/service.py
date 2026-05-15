"""Application service for the product-selection bounded context."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from agent_platform.repository import AgentPlatformRepository
from config import (
    SELECTION_AUTOMATION_MAX_QUERIES,
    SELECTION_AUTOMATION_MAX_TRACKED_ITEMS,
    SELECTION_AUTOMATION_MIN_CONFIDENCE_SCORE,
    SELECTION_AUTOMATION_MIN_OPPORTUNITY_SCORE,
    SELECTION_OPERATIONS_MAX_ITEMS,
    SELECTION_OPERATIONS_REMIND_AFTER_HOURS,
    SELECTION_OPERATIONS_STALE_HOURS,
)

from .adapters import TaobaoAdapter, XianyuAdapter
from .ai_explainer import build_reason_blocks, recommend_action
from .models import (
    PlatformScope,
    ProductResearchQuery,
    ProductTrackingStatus,
    QueryType,
    ResearchJobStatus,
)
from .repository import ProductSelectionRepository
from .scoring import score_product_opportunity


class ProductSelectionService:
    def __init__(
        self,
        repository: ProductSelectionRepository,
        *,
        taobao_adapter: TaobaoAdapter | None = None,
        xianyu_adapter: XianyuAdapter | None = None,
        agent_repository: AgentPlatformRepository | None = None,
    ):
        self.repository = repository
        self.taobao_adapter = taobao_adapter or TaobaoAdapter()
        self.xianyu_adapter = xianyu_adapter or XianyuAdapter()
        self.agent_repository = agent_repository

    def start_research_job(
        self,
        *,
        query_type: str,
        query_text: str,
        platform_scope: str,
        rendered_snapshot_html: str | None = None,
        rendered_snapshot_path: str | None = None,
        detail_snapshot_htmls: list[str] | None = None,
        detail_snapshot_manifest_path: str | None = None,
    ) -> dict[str, Any]:
        query = self.repository.create_query(
            query_type=query_type,
            query_text=query_text,
            platform_scope=platform_scope,
            status=ResearchJobStatus.RUNNING.value,
        )
        adapters = self._select_adapters(platform_scope)
        raw_candidates: list[dict[str, Any]] = []
        for adapter in adapters:
            raw_candidates.extend(
                adapter.search_products(
                    query_text,
                    query_type=query_type,
                    rendered_snapshot_html=rendered_snapshot_html,
                    rendered_snapshot_path=rendered_snapshot_path,
                    detail_snapshot_htmls=detail_snapshot_htmls or [],
                    detail_snapshot_manifest_path=detail_snapshot_manifest_path,
                )
            )

        platform_count = len({item["platform"] for item in raw_candidates})
        base_cross_platform_score = 72.0 if platform_count > 1 else 45.0

        for candidate in raw_candidates:
            scored = score_product_opportunity(
                candidate,
                cross_platform_signal_score=base_cross_platform_score,
            )
            scored["reason_blocks"] = build_reason_blocks(scored)
            scored["recommended_action"] = recommend_action(scored)
            opportunity = self.repository.create_opportunity(
                query_id=query.id,
                platform=scored["platform"],
                platform_item_id=scored["platform_item_id"],
                title=scored["title"],
                image_url=scored.get("image_url"),
                category_path=scored.get("category_path"),
                price_low=scored.get("price_low"),
                price_mid=scored.get("price_mid"),
                price_high=scored.get("price_high"),
                demand_score=scored.get("demand_score") or 0,
                competition_score=scored.get("competition_score") or 0,
                price_fit_score=scored.get("price_fit_score") or 0,
                risk_score=scored.get("risk_score") or 0,
                cross_platform_signal_score=scored.get("cross_platform_signal_score") or 0,
                opportunity_score=scored.get("opportunity_score") or 0,
                confidence_score=scored.get("confidence_score") or 0,
                risk_tags=scored.get("risk_tags") or [],
                reason_blocks=scored.get("reason_blocks") or [],
                recommended_action=scored.get("recommended_action"),
                source_urls=scored.get("source_urls") or [],
            )
            self.repository.replace_signals(opportunity.id, scored.get("signals") or [])

        self.repository.update_query_status(query.id, ResearchJobStatus.COMPLETED.value)
        return self.get_research_job(query.id)

    def get_research_job(self, job_id: str) -> dict[str, Any]:
        query = self.repository.get_query(job_id)
        if query is None:
            raise ValueError(f"Selection query {job_id} not found")

        opportunities, total = self.repository.list_opportunities(query_id=query.id, page_size=50)
        return {
            "job": query.model_dump(mode="json"),
            "total": total,
            "items": [item.model_dump(mode="json") for item in opportunities],
        }

    def list_opportunities(
        self,
        *,
        query_id: str | None = None,
        platform: str | None = None,
        search: str | None = None,
        risk_tag: str | None = None,
        source_mode: str | None = None,
        fallback_reason: str | None = None,
        sort_by: str = "opportunity_score",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        items, total = self.repository.list_opportunities(
            query_id=query_id,
            platform=platform,
            search=search,
            risk_tag=risk_tag,
            source_mode=source_mode,
            fallback_reason=fallback_reason,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [item.model_dump(mode="json") for item in items],
        }

    def get_opportunity_detail(self, opportunity_id: str) -> dict[str, Any] | None:
        opportunity = self.repository.get_opportunity(opportunity_id)
        if opportunity is None:
            return None

        detail = opportunity.model_dump(mode="json")
        detail["signals"] = [
            signal.model_dump(mode="json") for signal in self.repository.list_signals(opportunity_id)
        ]
        tracking = self.repository.get_tracking(opportunity_id)
        detail["tracking"] = tracking.model_dump() if tracking else None
        query = self.repository.get_query(opportunity.query_id)
        detail["query"] = query.model_dump(mode="json") if query else None
        return detail

    def get_workspace(self) -> dict[str, Any]:
        recent_queries = self.repository.list_queries(limit=5)
        top_items, total_items = self.repository.list_opportunities(page=1, page_size=5)
        tracking_items = self.repository.list_tracking()
        platform_counter = Counter(item.platform for item in top_items)
        automation_runs = self.list_automation_runs(limit=3)
        due_tracking_items = self._collect_tracking_operation_candidates(
            tracking_items=tracking_items,
            stale_after_hours=SELECTION_OPERATIONS_STALE_HOURS,
            max_items=5,
        )
        operations_runs = self.list_operations_runs(limit=3)

        return {
            "overview": {
                "query_count": len(self.repository.list_queries(limit=100)),
                "opportunity_count": total_items,
                "tracked_count": len(tracking_items),
                "favorited_count": len([item for item in tracking_items if item["is_favorited"]]),
                "due_tracking_count": len(due_tracking_items),
            },
            "recent_queries": [query.model_dump(mode="json") for query in recent_queries],
            "top_opportunities": [item.model_dump(mode="json") for item in top_items],
            "tracking_queue": tracking_items[:5],
            "due_tracking_queue": due_tracking_items,
            "platform_breakdown": [
                {"platform": platform, "count": count} for platform, count in platform_counter.items()
            ],
            "automation_runs": automation_runs,
            "operations_runs": operations_runs,
        }

    def rerun_recent_queries(self, *, limit: int = 5) -> dict[str, Any]:
        recent_queries = self.repository.list_queries(limit=limit)
        rerun_jobs: list[dict[str, Any]] = []

        for query in reversed(recent_queries):
            result = self.start_research_job(
                query_type=query.query_type.value,
                query_text=query.query_text,
                platform_scope=query.platform_scope.value,
            )
            rerun_jobs.append(
                {
                    "query_text": query.query_text,
                    "platform_scope": query.platform_scope.value,
                    "job_id": result["job"]["id"],
                    "item_count": result["total"],
                }
            )

        return {"triggered": len(rerun_jobs), "jobs": rerun_jobs}

    def run_automation_cycle(
        self,
        *,
        query_limit: int = SELECTION_AUTOMATION_MAX_QUERIES,
        max_tracked_items: int = SELECTION_AUTOMATION_MAX_TRACKED_ITEMS,
        min_opportunity_score: float = SELECTION_AUTOMATION_MIN_OPPORTUNITY_SCORE,
        min_confidence_score: float = SELECTION_AUTOMATION_MIN_CONFIDENCE_SCORE,
        requested_by: str | None = "scheduler",
    ) -> dict[str, Any]:
        agent_repository = self._get_agent_repository()
        input_payload = {
            "query_limit": query_limit,
            "max_tracked_items": max_tracked_items,
            "min_opportunity_score": min_opportunity_score,
            "min_confidence_score": min_confidence_score,
        }
        job = agent_repository.create_job(
            domain_type="product_selection",
            job_type="selection_automation",
            status="running",
            requested_by=requested_by,
            input_payload=input_payload,
        )

        try:
            replay = self.rerun_recent_queries(limit=query_limit)
            candidates = self._collect_automation_candidates(
                replay["jobs"],
                min_opportunity_score=min_opportunity_score,
                min_confidence_score=min_confidence_score,
            )
            tracked_items = self._promote_automation_candidates(
                candidates,
                max_tracked_items=max_tracked_items,
            )
            result_payload = {
                "triggered_queries": replay["triggered"],
                "rerun_jobs": replay["jobs"],
                "candidate_count": len(candidates),
                "tracked_count": len(tracked_items),
                "tracked_items": tracked_items,
            }
            updated_job = agent_repository.update_job(
                job.id,
                status="completed",
                result_payload=result_payload,
            )
            return {
                "job": updated_job.model_dump(mode="json"),
                **result_payload,
            }
        except Exception as exc:
            failed_job = agent_repository.update_job(
                job.id,
                status="failed",
                result_payload={
                    **input_payload,
                    "error": str(exc),
                },
            )
            raise RuntimeError(
                f"Selection automation cycle failed for job {failed_job.id}: {exc}"
            ) from exc

    def list_automation_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        jobs = self._get_agent_repository().list_jobs(
            domain_type="product_selection",
            job_type="selection_automation",
            limit=limit,
        )
        return [job.model_dump(mode="json") for job in jobs]

    def get_automation_run(self, job_id: str) -> dict[str, Any]:
        job = self._get_agent_repository().get_job(job_id)
        if job is None or job.domain_type != "product_selection" or job.job_type != "selection_automation":
            raise ValueError(f"Selection automation job {job_id} not found")
        return job.model_dump(mode="json")

    def run_operations_cycle(
        self,
        *,
        max_items: int = SELECTION_OPERATIONS_MAX_ITEMS,
        stale_after_hours: int = SELECTION_OPERATIONS_STALE_HOURS,
        remind_after_hours: int = SELECTION_OPERATIONS_REMIND_AFTER_HOURS,
        requested_by: str | None = "scheduler",
    ) -> dict[str, Any]:
        agent_repository = self._get_agent_repository()
        input_payload = {
            "max_items": max_items,
            "stale_after_hours": stale_after_hours,
            "remind_after_hours": remind_after_hours,
        }
        job = agent_repository.create_job(
            domain_type="product_selection",
            job_type="selection_tracking_ops",
            status="running",
            requested_by=requested_by,
            input_payload=input_payload,
        )

        try:
            tracking_items = self.repository.list_tracking()
            due_items = self._collect_tracking_operation_candidates(
                tracking_items=tracking_items,
                stale_after_hours=stale_after_hours,
                max_items=max_items,
            )
            processed_items = self._apply_tracking_follow_ups(
                due_items,
                remind_after_hours=remind_after_hours,
            )
            result_payload = {
                "due_count": len(due_items),
                "processed_count": len(processed_items),
                "processed_items": processed_items,
            }
            updated_job = agent_repository.update_job(
                job.id,
                status="completed",
                result_payload=result_payload,
            )
            return {"job": updated_job.model_dump(mode="json"), **result_payload}
        except Exception as exc:
            failed_job = agent_repository.update_job(
                job.id,
                status="failed",
                result_payload={**input_payload, "error": str(exc)},
            )
            raise RuntimeError(
                f"Selection operations cycle failed for job {failed_job.id}: {exc}"
            ) from exc

    def list_operations_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        jobs = self._get_agent_repository().list_jobs(
            domain_type="product_selection",
            job_type="selection_tracking_ops",
            limit=limit,
        )
        return [job.model_dump(mode="json") for job in jobs]

    def get_operations_run(self, job_id: str) -> dict[str, Any]:
        job = self._get_agent_repository().get_job(job_id)
        if job is None or job.domain_type != "product_selection" or job.job_type != "selection_tracking_ops":
            raise ValueError(f"Selection operations job {job_id} not found")
        return job.model_dump(mode="json")

    @staticmethod
    def validate_query_payload(query_type: str, platform_scope: str, query_text: str) -> None:
        QueryType(query_type)
        PlatformScope(platform_scope)
        if not query_text.strip():
            raise ValueError("query_text is required")

    def _select_adapters(self, platform_scope: str) -> list[Any]:
        scope = PlatformScope(platform_scope)
        if scope == PlatformScope.TAOBAO:
            return [self.taobao_adapter]
        if scope == PlatformScope.XIANYU:
            return [self.xianyu_adapter]
        return [self.taobao_adapter, self.xianyu_adapter]

    def _get_agent_repository(self) -> AgentPlatformRepository:
        if self.agent_repository is None:
            self.agent_repository = AgentPlatformRepository(self.repository.db_path)
        return self.agent_repository

    def _collect_automation_candidates(
        self,
        rerun_jobs: list[dict[str, Any]],
        *,
        min_opportunity_score: float,
        min_confidence_score: float,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for rerun_job in rerun_jobs:
            result = self.get_research_job(rerun_job["job_id"])
            for item in result["items"]:
                if item["id"] in seen_ids:
                    continue
                if float(item.get("opportunity_score") or 0) < min_opportunity_score:
                    continue
                if float(item.get("confidence_score") or 0) < min_confidence_score:
                    continue
                seen_ids.add(item["id"])
                candidates.append(item)

        candidates.sort(
            key=lambda item: (
                float(item.get("opportunity_score") or 0),
                float(item.get("confidence_score") or 0),
            ),
            reverse=True,
        )
        return candidates

    def _promote_automation_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        max_tracked_items: int,
    ) -> list[dict[str, Any]]:
        tracked_items: list[dict[str, Any]] = []

        for item in candidates:
            if len(tracked_items) >= max_tracked_items:
                break

            existing_tracking = self.repository.get_tracking(item["id"])
            tracking = self.repository.upsert_tracking(
                item["id"],
                {
                    "status": ProductTrackingStatus.TRACKING.value,
                    "notes": (
                        "Automation promoted this candidate based on opportunity "
                        f"{item.get('opportunity_score')} and confidence {item.get('confidence_score')}."
                    ),
                    "next_action": item.get("recommended_action") or "Review the candidate and validate sourcing risk.",
                    "is_favorited": existing_tracking.is_favorited if existing_tracking else False,
                },
            )
            tracked_items.append(
                {
                    "opportunity_id": item["id"],
                    "title": item["title"],
                    "platform": item["platform"],
                    "opportunity_score": item.get("opportunity_score"),
                    "confidence_score": item.get("confidence_score"),
                    "tracking_status": tracking.status.value,
                    "next_action": tracking.next_action,
                }
            )

        return tracked_items

    def _collect_tracking_operation_candidates(
        self,
        *,
        tracking_items: list[dict[str, Any]],
        stale_after_hours: int,
        max_items: int,
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        stale_cutoff = now - timedelta(hours=stale_after_hours)
        due_items: list[dict[str, Any]] = []

        for item in tracking_items:
            if item["status"] in {ProductTrackingStatus.DONE.value, ProductTrackingStatus.ARCHIVED.value}:
                continue

            remind_at_raw = item.get("remind_at")
            updated_at_raw = item.get("updated_at")
            remind_at = self._parse_datetime(remind_at_raw)
            updated_at = self._parse_datetime(updated_at_raw)
            reason: str | None = None

            if remind_at is not None and remind_at <= now:
                reason = "reminder_due"
            elif remind_at is None and updated_at is not None and updated_at <= stale_cutoff:
                reason = "stale_tracking"

            if reason is None:
                continue

            due_items.append(
                {
                    **item,
                    "follow_up_reason": reason,
                }
            )

            if len(due_items) >= max_items:
                break

        return due_items

    def _apply_tracking_follow_ups(
        self,
        due_items: list[dict[str, Any]],
        *,
        remind_after_hours: int,
    ) -> list[dict[str, Any]]:
        remind_at = (datetime.now(UTC) + timedelta(hours=remind_after_hours)).isoformat()
        processed_items: list[dict[str, Any]] = []

        for item in due_items:
            reason = str(item["follow_up_reason"])
            existing_notes = item.get("notes")
            follow_up_note = (
                existing_notes
                or f"Operations cycle flagged this item for follow-up because {reason.replace('_', ' ')}."
            )
            next_action = item.get("next_action") or "Review sourcing status, competitor changes, and fulfillment risk."
            tracking = self.repository.upsert_tracking(
                item["opportunity_id"],
                {
                    "status": item["status"],
                    "is_favorited": item["is_favorited"],
                    "notes": follow_up_note,
                    "next_action": next_action,
                    "remind_at": remind_at,
                },
            )
            processed_items.append(
                {
                    "opportunity_id": item["opportunity_id"],
                    "title": item["opportunity"]["title"],
                    "platform": item["opportunity"]["platform"],
                    "follow_up_reason": reason,
                    "next_action": tracking.next_action,
                    "remind_at": tracking.remind_at,
                }
            )

        return processed_items

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
