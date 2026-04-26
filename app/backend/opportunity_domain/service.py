"""
Opportunity-domain service helpers for shared agent workflows.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from analysis.run_manager import AnalysisRunManager
    from data_manager import DataManager


_CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "grant": {"grant", "grants", "funding", "fund", "资助", "补贴", "基金"},
    "bounty": {"bounty", "bug bounty", "赏金", "悬赏"},
    "hackathon": {"hackathon", "黑客松"},
    "data_competition": {"data competition", "kaggle", "数据比赛", "数据竞赛"},
    "coding_competition": {"coding competition", "算法赛", "编程比赛", "编程竞赛"},
    "other_competition": {"competition", "比赛", "竞赛"},
    "airdrop": {"airdrop", "空投"},
    "dev_event": {"meetup", "event", "活动", "路演", "workshop"},
}

_SEARCH_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+._-]*|[\u4e00-\u9fff]{2,}", re.IGNORECASE)
_ACTIVITY_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

_STOP_PHRASES = (
    "帮我找一下",
    "帮我找",
    "帮我看一下",
    "帮我看",
    "帮我分析一下",
    "帮我分析",
    "帮我解释一下",
    "帮我解释",
    "帮我",
    "找一下",
    "看一下",
    "值得跟进的",
    "值不值得跟进",
    "值不值得做",
    "怎么跟进",
    "下一步",
    "怎么做",
    "怎么办",
    "机会",
    "活动",
    "项目",
    "explain",
    "explanation",
    "find",
    "search",
    "show me",
    "worth following",
    "worth doing",
    "next action",
    "follow up",
    "follow-up",
    "opportunity",
    "opportunities",
)

_STOP_TOKENS = {
    "帮我",
    "看看",
    "找找",
    "搜索",
    "查询",
    "分析",
    "解释",
    "为什么",
    "如何",
    "怎么",
    "一下",
    "这个",
    "那个",
    "值得",
    "跟进",
    "活动",
    "机会",
    "项目",
    "worth",
    "doing",
    "follow",
    "following",
    "next",
    "action",
    "search",
    "find",
    "show",
    "tell",
    "about",
}


class OpportunityDomainService:
    def __init__(
        self,
        data_manager: DataManager,
        run_manager: AnalysisRunManager | None = None,
    ) -> None:
        self.data_manager = data_manager
        self.run_manager = run_manager

    def search_opportunities(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        merged_filters = dict(filters or {})
        category = self._infer_category(query)
        if category and not merged_filters.get("category"):
            merged_filters["category"] = category

        search_terms = self._extract_search_terms(query, category=category)
        if search_terms and not merged_filters.get("search"):
            merged_filters["search"] = search_terms

        items, total = self.data_manager.get_activities(
            filters=merged_filters,
            sort_by="score",
            sort_order="desc",
            page=1,
            page_size=max(limit, 1),
        )
        if total == 0 and "search" in merged_filters:
            fallback_filters = dict(merged_filters)
            fallback_filters.pop("search", None)
            items, total = self.data_manager.get_activities(
                filters=fallback_filters,
                sort_by="score",
                sort_order="desc",
                page=1,
                page_size=max(limit, 1),
            )
            merged_filters = fallback_filters

        return {
            "query": query,
            "applied_filters": merged_filters,
            "total": total,
            "items": [self._serialize_activity(activity) for activity in items[:limit]],
        }

    def explain_opportunity(
        self,
        activity_id: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_activity(activity_id=activity_id, query=query)
        if resolved is None:
            return {
                "matched": False,
                "activity_id": activity_id,
                "query": query,
            }

        detail, matched_by = resolved
        reasons = detail.get("analysis_summary_reasons") or detail.get("analysis_reasons") or []
        return {
            "matched": True,
            "matched_by": matched_by,
            "query": query,
            "activity_id": detail["id"],
            "activity": self._serialize_activity_detail(detail),
            "analysis": {
                "status": detail.get("analysis_status"),
                "summary": detail.get("analysis_summary") or detail.get("summary") or detail.get("description"),
                "reasons": reasons,
                "risk_flags": detail.get("analysis_risk_flags") or [],
                "recommended_action": detail.get("analysis_recommended_action"),
            },
            "tracking": detail.get("tracking"),
        }

    def suggest_next_action(
        self,
        activity_id: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_activity(activity_id=activity_id, query=query)
        if resolved is None:
            return {
                "matched": False,
                "activity_id": activity_id,
                "query": query,
            }

        detail, matched_by = resolved
        tracking = detail.get("tracking") or {}
        suggested_action = tracking.get("next_action")
        action_source = "tracking"

        if not suggested_action:
            suggested_action = detail.get("analysis_recommended_action")
            action_source = "analysis"

        if not suggested_action:
            suggested_action = self._default_next_action(detail)
            action_source = "generated"

        return {
            "matched": True,
            "matched_by": matched_by,
            "query": query,
            "activity_id": detail["id"],
            "activity_title": detail["title"],
            "analysis_status": detail.get("analysis_status"),
            "tracking_status": tracking.get("status") or "saved",
            "next_action": suggested_action,
            "action_source": action_source,
            "urgency": self._derive_urgency(detail),
            "deadline": self._extract_deadline(detail),
            "notes": tracking.get("notes"),
            "analysis_reasons": detail.get("analysis_summary_reasons") or detail.get("analysis_reasons") or [],
        }

    def _resolve_activity(
        self,
        *,
        activity_id: str | None = None,
        query: str | None = None,
    ) -> tuple[dict[str, Any], str] | None:
        if activity_id:
            detail = self.data_manager.get_activity_detail(activity_id)
            return (detail, "id") if detail else None

        normalized_query = (query or "").strip()
        if normalized_query and _ACTIVITY_ID_PATTERN.match(normalized_query):
            detail = self.data_manager.get_activity_detail(normalized_query)
            return (detail, "id") if detail else None

        if not normalized_query:
            return None

        search_result = self.search_opportunities(normalized_query, limit=1)
        if not search_result["items"]:
            return None

        matched_id = search_result["items"][0]["id"]
        detail = self.data_manager.get_activity_detail(matched_id)
        return (detail, "query") if detail else None

    def _infer_category(self, query: str) -> str | None:
        normalized = f" {(query or '').lower()} "
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return category
        return None

    def _extract_search_terms(self, query: str, *, category: str | None = None) -> str | None:
        cleaned = f" {(query or '').lower()} "
        for phrase in _STOP_PHRASES:
            cleaned = cleaned.replace(phrase, " ")

        category_keywords = _CATEGORY_KEYWORDS.get(category or "", set())
        tokens = []
        for token in _SEARCH_TOKEN_PATTERN.findall(cleaned):
            stripped = token.strip().lower()
            if not stripped or stripped in _STOP_TOKENS or stripped in category_keywords:
                continue
            if any(marker in stripped for marker in ("帮", "跟进", "值得", "机会", "活动")):
                continue
            tokens.append(stripped)

        if not tokens:
            return None

        return " ".join(tokens[:4])

    @staticmethod
    def _serialize_activity(activity: Any) -> dict[str, Any]:
        deadline = None
        if getattr(activity, "dates", None) and getattr(activity.dates, "deadline", None):
            deadline = activity.dates.deadline.isoformat()

        prize = None
        if getattr(activity, "prize", None):
            prize = {
                "amount": activity.prize.amount,
                "currency": activity.prize.currency,
                "description": activity.prize.description,
            }

        category = activity.category.value if hasattr(activity.category, "value") else activity.category
        return {
            "id": activity.id,
            "title": activity.title,
            "category": category,
            "summary": activity.summary or activity.description,
            "score": activity.score,
            "trust_level": activity.trust_level,
            "analysis_status": activity.analysis_status,
            "deadline": deadline,
            "prize": prize,
            "url": activity.url,
            "is_tracking": activity.is_tracking,
            "is_favorited": activity.is_favorited,
        }

    def _serialize_activity_detail(self, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": detail["id"],
            "title": detail["title"],
            "category": detail.get("category"),
            "summary": detail.get("summary") or detail.get("description"),
            "analysis_status": detail.get("analysis_status"),
            "deadline": self._extract_deadline(detail),
            "prize": detail.get("prize"),
            "url": detail.get("url"),
            "score": detail.get("score"),
            "trust_level": detail.get("trust_level"),
        }

    @staticmethod
    def _extract_deadline(detail: dict[str, Any]) -> str | None:
        dates = detail.get("dates") or {}
        return dates.get("deadline")

    def _derive_urgency(self, detail: dict[str, Any]) -> str:
        deadline_raw = self._extract_deadline(detail)
        if not deadline_raw:
            return "medium"

        deadline = datetime.fromisoformat(deadline_raw)
        now = datetime.now(deadline.tzinfo) if deadline.tzinfo else datetime.now()
        days_remaining = (deadline - now).total_seconds() / 86400
        if days_remaining <= 3:
            return "high"
        if days_remaining <= 10:
            return "medium"
        return "low"

    @staticmethod
    def _default_next_action(detail: dict[str, Any]) -> str:
        category = detail.get("category")
        if category == "grant":
            return "核对申请资格，整理材料清单，并预留一轮提交前校验。"
        if category == "bounty":
            return "先确认任务范围和奖励规则，再拆出一个最小可交付版本。"
        if category == "hackathon":
            return "确认报名截止时间，先收敛题目方向，再补齐组队或独立参赛方案。"
        return "先核对资格和截止时间，再整理一版最小执行计划。"
