"""
Application service for the product-selection bounded context.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
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
        rendered_snapshot_html: str | None = None,
        rendered_snapshot_path: str | None = None,
        detail_snapshot_htmls: list[str] | None = None,
        detail_snapshot_manifest_path: str | None = None,
    ) -> dict[str, Any]:
        resolved_rendered_snapshot_html = self._resolve_rendered_snapshot_html(
            rendered_snapshot_html=rendered_snapshot_html,
            rendered_snapshot_path=rendered_snapshot_path,
        )
        resolved_detail_snapshot_htmls = self._resolve_detail_snapshot_htmls(
            detail_snapshot_htmls=detail_snapshot_htmls,
            detail_snapshot_manifest_path=detail_snapshot_manifest_path,
        )
        query = self.repository.create_query(
            query_type=query_type,
            query_text=query_text,
            platform_scope=platform_scope,
            status=ResearchJobStatus.RUNNING.value,
        )
        adapters = self._select_adapters(platform_scope)
        raw_candidates: list[dict[str, Any]] = []
        adapter_runs: list[dict[str, Any]] = []
        for adapter in adapters:
            adapter_result = adapter.search_marketplace(
                query_text,
                query_type=query_type,
                rendered_snapshot_html=resolved_rendered_snapshot_html,
            )
            adapter_runs.append(
                {
                    "platform": adapter_result["platform"],
                    "mode": adapter_result["mode"],
                    "diagnostics": adapter_result["diagnostics"],
                    "item_count": len(adapter_result["items"]),
                }
            )
            adapter_items = adapter_result["items"]
            if resolved_detail_snapshot_htmls and adapter is self.xianyu_adapter:
                adapter_items = self._enrich_xianyu_candidates(adapter_items, resolved_detail_snapshot_htmls)
            raw_candidates.extend(adapter_items)

        if not raw_candidates:
            self.repository.update_query_status(query.id, ResearchJobStatus.FAILED.value)
            return self.get_research_job(query.id, adapter_runs=adapter_runs)

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
                sales_volume=scored.get("sales_volume"),
                seller_count=scored.get("seller_count"),
                seller_type=scored.get("seller_type"),
                seller_name=scored.get("seller_name"),
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
                source_mode=scored.get("source_mode") or "live",
                source_diagnostics=scored.get("source_diagnostics") or {},
            )
            self.repository.replace_signals(opportunity.id, scored.get("signals") or [])

        self.repository.update_query_status(query.id, ResearchJobStatus.COMPLETED.value)
        return self.get_research_job(query.id, adapter_runs=adapter_runs)

    def _enrich_xianyu_candidates(
        self,
        candidates: list[dict[str, Any]],
        detail_snapshot_htmls: list[str],
    ) -> list[dict[str, Any]]:
        enriched = list(candidates)
        for detail_html in detail_snapshot_htmls:
            enriched = [
                self.xianyu_adapter.enrich_candidate_with_detail_snapshot(candidate, detail_html)
                for candidate in enriched
            ]
        return enriched

    @staticmethod
    def _resolve_rendered_snapshot_html(
        *,
        rendered_snapshot_html: str | None,
        rendered_snapshot_path: str | None,
    ) -> str | None:
        if rendered_snapshot_html:
            return rendered_snapshot_html
        if not rendered_snapshot_path:
            return None
        snapshot_path = Path(rendered_snapshot_path)
        if not snapshot_path.exists():
            raise ValueError(f"rendered snapshot not found: {rendered_snapshot_path}")
        return snapshot_path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _resolve_detail_snapshot_htmls(
        *,
        detail_snapshot_htmls: list[str] | None,
        detail_snapshot_manifest_path: str | None,
    ) -> list[str]:
        resolved = list(detail_snapshot_htmls or [])
        if not detail_snapshot_manifest_path:
            return resolved

        manifest_path = Path(detail_snapshot_manifest_path)
        if not manifest_path.exists():
            raise ValueError(f"detail snapshot manifest not found: {detail_snapshot_manifest_path}")

        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"failed to parse detail snapshot manifest: {detail_snapshot_manifest_path}") from exc

        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise ValueError("detail snapshot manifest must contain an 'items' list")

        for item in items:
            if not isinstance(item, dict):
                continue
            html_path = str(item.get("path") or "").strip()
            if not html_path:
                continue
            detail_path = Path(html_path)
            if not detail_path.exists():
                continue
            resolved.append(detail_path.read_text(encoding="utf-8", errors="ignore"))

        return resolved

    def get_research_job(self, job_id: str, adapter_runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        query = self.repository.get_query(job_id)
        if query is None:
            raise ValueError(f"Selection query {job_id} not found")

        opportunities, total = self.repository.list_opportunities(query_id=query.id, page_size=50)
        source_summary = self._build_source_summary(opportunities, adapter_runs=adapter_runs)
        return {
            "job": query.model_dump(mode="json"),
            "total": total,
            "items": [item.model_dump(mode="json") for item in opportunities],
            "source_summary": source_summary,
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
        source_summary = self._build_source_summary(items)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [item.model_dump(mode="json") for item in items],
            "source_summary": source_summary,
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
        detail["source_summary"] = self._build_source_summary([opportunity])
        return detail

    def get_workspace(self) -> dict[str, Any]:
        recent_queries = self.repository.list_queries(limit=5)
        top_items, total_items = self.repository.list_opportunities(page=1, page_size=5)
        tracking_items = self.repository.list_tracking()
        platform_counter = Counter(item.platform for item in top_items)
        tracking_queue = tracking_items[:5]
        tracking_opportunities = [item["opportunity"] for item in tracking_queue]

        return {
            "overview": {
                "query_count": len(self.repository.list_queries(limit=100)),
                "opportunity_count": total_items,
                "tracked_count": len(tracking_items),
                "favorited_count": len([item for item in tracking_items if item["is_favorited"]]),
            },
            "recent_queries": [query.model_dump(mode="json") for query in recent_queries],
            "top_opportunities": [item.model_dump(mode="json") for item in top_items],
            "tracking_queue": tracking_queue,
            "platform_breakdown": [
                {"platform": platform, "count": count} for platform, count in platform_counter.items()
            ],
            "source_summary": self._build_source_summary(top_items),
            "top_opportunities_source_summary": self._build_source_summary(top_items),
            "tracking_queue_source_summary": self._build_source_summary(tracking_opportunities),
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

    @staticmethod
    def _build_source_summary(
        opportunities: list[Any],
        *,
        adapter_runs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        def read_field(item: Any, field: str, default: Any = None) -> Any:
            if hasattr(item, field):
                return getattr(item, field)
            if isinstance(item, dict):
                return item.get(field, default)
            return default

        mode_counts = Counter(read_field(item, "source_mode", "live") or "live" for item in opportunities)
        if mode_counts.get("live") and mode_counts.get("fallback"):
            overall_mode = "mixed"
        elif mode_counts.get("live"):
            overall_mode = "live"
        elif adapter_runs and any((run.get("mode") or "") == "failed" for run in adapter_runs):
            overall_mode = "failed"
        else:
            overall_mode = "fallback"

        fallback_reasons = []
        extraction_stats_summary = {
            "http_candidates_seen": 0,
            "platform_candidates_seen": 0,
            "accepted_candidates": 0,
            "accepted_with_price": 0,
            "accepted_without_price": 0,
            "rejected_non_listing_url": 0,
            "rejected_noise_title": 0,
            "rejected_query_miss": 0,
            "rejected_duplicate_url": 0,
        }
        seller_mix = {
            "enterprise": 0,
            "personal": 0,
            "unknown": 0,
            "with_sales_volume": 0,
            "with_seller_count": 0,
        }
        for item in opportunities:
            diagnostics = read_field(item, "source_diagnostics", {}) or {}
            reason = diagnostics.get("fallback_reason")
            if reason:
                fallback_reasons.append(reason)
            seller_type = str(read_field(item, "seller_type", "") or "").lower()
            if seller_type == "enterprise":
                seller_mix["enterprise"] += 1
            elif seller_type == "personal":
                seller_mix["personal"] += 1
            else:
                seller_mix["unknown"] += 1
            sales_volume = read_field(item, "sales_volume")
            seller_count = read_field(item, "seller_count")
            if sales_volume is not None:
                seller_mix["with_sales_volume"] += 1
            if seller_count is not None:
                seller_mix["with_seller_count"] += 1

        for run in adapter_runs or []:
            diagnostics = run.get("diagnostics", {}) or {}
            reason = diagnostics.get("fallback_reason")
            if reason:
                fallback_reasons.append(str(reason))
            stats = run.get("diagnostics", {}).get("extraction_stats", {}) or {}
            for key in extraction_stats_summary:
                extraction_stats_summary[key] += int(stats.get(key) or 0)

        return {
            "overall_mode": overall_mode,
            "mode_counts": {
                "live": mode_counts.get("live", 0),
                "fallback": mode_counts.get("fallback", 0),
            },
            "fallback_used": bool(mode_counts.get("fallback", 0)),
            "fallback_reasons": sorted(set(fallback_reasons)),
            "adapter_runs": adapter_runs or [],
            "extraction_stats_summary": extraction_stats_summary,
            "seller_mix": seller_mix,
        }
