"""
Application service for the product-selection bounded context.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .adapters import TaobaoAdapter, XianyuAdapter
from .ai_explainer import build_reason_blocks, recommend_action
from .models import PlatformScope, ProductResearchQuery, QueryType, ResearchJobStatus
from .repository import ProductSelectionRepository
from .scoring import score_product_opportunity


class ProductSelectionService:
    def __init__(self, repository: ProductSelectionRepository):
        self.repository = repository
        self.taobao_adapter = TaobaoAdapter()
        self.xianyu_adapter = XianyuAdapter()

    def start_research_job(
        self,
        *,
        query_type: str,
        query_text: str,
        platform_scope: str,
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
            raw_candidates.extend(adapter.search_products(query_text, query_type=query_type))

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

        return {
            "overview": {
                "query_count": len(self.repository.list_queries(limit=100)),
                "opportunity_count": total_items,
                "tracked_count": len(tracking_items),
                "favorited_count": len([item for item in tracking_items if item["is_favorited"]]),
            },
            "recent_queries": [query.model_dump(mode="json") for query in recent_queries],
            "top_opportunities": [item.model_dump(mode="json") for item in top_items],
            "tracking_queue": tracking_items[:5],
            "platform_breakdown": [
                {"platform": platform, "count": count} for platform, count in platform_counter.items()
            ],
        }

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
