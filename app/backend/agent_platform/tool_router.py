"""
Domain-aware tool routing for the shared agent platform.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis.run_manager import AnalysisRunManager
    from data_manager import DataManager


_OPPORTUNITY_SEARCH_KEYWORDS = (
    "grant",
    "grants",
    "bounty",
    "hackathon",
    "search",
    "find",
    "\u627e",
    "\u641c",
    "\u7b5b",
    "\u673a\u4f1a",
    "\u6d3b\u52a8",
    "\u8d5b\u4e8b",
)
_OPPORTUNITY_EXPLAIN_KEYWORDS = (
    "worth",
    "why",
    "explain",
    "\u4e3a\u4ec0\u4e48",
    "\u5206\u6790",
    "\u89e3\u91ca",
    "\u8be6\u60c5",
    "\u503c\u4e0d\u503c\u5f97",
)
_OPPORTUNITY_NEXT_ACTION_KEYWORDS = (
    "follow",
    "follow-up",
    "next action",
    "\u4e0b\u4e00\u6b65",
    "\u8ddf\u8fdb",
    "\u600e\u4e48\u505a",
    "\u600e\u4e48\u8ddf\u8fdb",
)

_SELECTION_COMPARE_KEYWORDS = (
    "compare",
    "comparison",
    "\u5bf9\u6bd4",
    "\u6bd4\u8f83",
)

_SELECTION_TAOBAO_KEYWORDS = ("taobao", "\u6dd8\u5b9d")
_SELECTION_XIANYU_KEYWORDS = ("xianyu", "\u95f2\u9c7c")


class ToolRouter:
    def __init__(
        self,
        tool_registry: dict[str, object] | None = None,
        registry_key: str | None = None,
    ) -> None:
        self.tool_registry = tool_registry or {}
        self.registry_key = registry_key

    def get_tool(self, tool_name: str) -> object | None:
        return self.tool_registry.get(tool_name)

    def resolve_tools(self, *, domain_type: str, user_message: str) -> list[str]:
        normalized_message = (user_message or "").lower()

        if domain_type == "opportunity":
            return self._resolve_opportunity_tools(normalized_message)

        if domain_type == "product_selection":
            wants_compare = any(token in normalized_message for token in _SELECTION_COMPARE_KEYWORDS)
            mentions_taobao = any(token in normalized_message for token in _SELECTION_TAOBAO_KEYWORDS)
            mentions_xianyu = any(token in normalized_message for token in _SELECTION_XIANYU_KEYWORDS)
            if wants_compare or (mentions_taobao and mentions_xianyu):
                return ["selection_compare"]
            return ["selection_query"]

        return ["general_reasoning"]

    def _resolve_opportunity_tools(self, normalized_message: str) -> list[str]:
        wants_explain = any(token in normalized_message for token in _OPPORTUNITY_EXPLAIN_KEYWORDS)
        wants_next_action = any(token in normalized_message for token in _OPPORTUNITY_NEXT_ACTION_KEYWORDS)
        wants_search = any(token in normalized_message for token in _OPPORTUNITY_SEARCH_KEYWORDS)

        ordered_tools: list[str] = []
        if wants_search or not (wants_explain or wants_next_action):
            ordered_tools.append("opportunity_search")
        if wants_explain:
            ordered_tools.append("opportunity_explain")
        if wants_next_action:
            ordered_tools.append("opportunity_next_action")

        return ordered_tools or ["opportunity_search"]


def build_default_registry(
    data_manager: DataManager | None = None,
    run_manager: AnalysisRunManager | None = None,
) -> dict[str, object]:
    registry: dict[str, object] = {}
    if data_manager is None:
        return registry

    from opportunity_domain.tools import build_opportunity_tool_registry
    from product_selection.tools import build_product_selection_tool_registry

    registry.update(build_opportunity_tool_registry(data_manager=data_manager, run_manager=run_manager))
    registry.update(build_product_selection_tool_registry(data_manager=data_manager))
    return registry
