"""
Product-selection tool registry for the shared agent platform.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .service import ProductSelectionService

if TYPE_CHECKING:
    from agent_platform.models import AgentSession
    from data_manager import DataManager


_TAOBAO_TOKENS = ("taobao", "\u6dd8\u5b9d")
_XIANYU_TOKENS = ("xianyu", "\u95f2\u9c7c")
_NOISE_PATTERNS = (
    "\u5e2e\u6211",
    "\u770b\u4e00\u4e0b",
    "\u8fd8\u503c\u5f97\u505a\u5417",
    "\u503c\u5f97\u505a\u5417",
    "\u8fd8\u80fd\u505a\u5417",
    "\u503c\u4e0d\u503c\u5f97",
    "\u5e73\u53f0\u9009\u54c1",
    "\u9009\u54c1",
    "worth doing",
    "worth it",
    "compare",
    "comparison",
    "please",
    "help me",
)


def _infer_platform_scope(user_message: str) -> str:
    normalized = (user_message or "").lower()
    has_taobao = any(token in normalized for token in _TAOBAO_TOKENS)
    has_xianyu = any(token in normalized for token in _XIANYU_TOKENS)
    if has_taobao and has_xianyu:
        return "both"
    if has_taobao:
        return "taobao"
    if has_xianyu:
        return "xianyu"
    return "both"


def _extract_query_text(user_message: str) -> str:
    normalized = (user_message or "").strip()
    cleaned = normalized
    for noise in _NOISE_PATTERNS:
        cleaned = re.sub(re.escape(noise), " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，。,:;!?")
    return cleaned or normalized or "selection opportunity"


class SelectionQueryTool:
    name = "selection_query"

    def __init__(self, service: ProductSelectionService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        query_text = _extract_query_text(user_message)
        platform_scope = _infer_platform_scope(user_message)
        result = self.service.start_research_job(
            query_type="keyword",
            query_text=query_text,
            platform_scope=platform_scope,
        )
        return {
            **result,
            "query_text": query_text,
            "platform_scope": platform_scope,
            "shortlist": result["items"][:5],
        }


class SelectionCompareTool:
    name = "selection_compare"

    def __init__(self, service: ProductSelectionService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        query_text = _extract_query_text(user_message)
        result = self.service.start_research_job(
            query_type="keyword",
            query_text=query_text,
            platform_scope="both",
        )

        compare_rows: list[dict[str, Any]] = []
        seen_platforms: set[str] = set()
        for item in result["items"]:
            platform = item["platform"]
            if platform in seen_platforms:
                continue
            seen_platforms.add(platform)
            compare_rows.append(
                {
                    "id": item["id"],
                    "platform": item["platform"],
                    "title": item["title"],
                    "opportunity_score": item["opportunity_score"],
                    "confidence_score": item["confidence_score"],
                    "recommended_action": item["recommended_action"],
                }
            )

        return {
            **result,
            "query_text": query_text,
            "platform_scope": "both",
            "shortlist": result["items"][:5],
            "compare_rows": compare_rows,
        }


def build_product_selection_tool_registry(data_manager: DataManager) -> dict[str, object]:
    from .repository import ProductSelectionRepository

    repository = ProductSelectionRepository(data_manager.db_path)
    service = ProductSelectionService(repository=repository)
    tools = [SelectionQueryTool(service), SelectionCompareTool(service)]
    return {tool.name: tool for tool in tools}
