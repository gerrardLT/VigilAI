"""
Session-state, insight, and thinking-trace builders for agent sessions.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from .models import AgentSession, AgentTurn


class SessionStateDraft(BaseModel):
    goal: str | None = None
    constraints: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    working_memory: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    next_question: str | None = None
    next_action: str | None = None
    summary: str | None = None
    last_tool_names: list[str] = Field(default_factory=list)
    state_payload: dict[str, Any] = Field(default_factory=dict)


class InsightDraft(BaseModel):
    insight_type: str
    content: str
    importance: float = 0.5
    payload: dict[str, Any] = Field(default_factory=dict)


class ThinkingStepDraft(BaseModel):
    phase: str
    summary: str
    tool_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionIntelligenceService:
    def build(
        self,
        *,
        session: AgentSession,
        user_turn: AgentTurn,
        assistant_turn: str,
        tool_calls: list[dict[str, Any]],
        tool_results: dict[str, dict[str, Any]],
    ) -> tuple[SessionStateDraft, list[InsightDraft], list[ThinkingStepDraft]]:
        last_tool_names = [call["tool_name"] for call in tool_calls if call.get("status") == "completed"]
        goal = user_turn.content.strip()[:240] or None
        constraints = self._infer_constraints(user_turn.content)
        preferences = self._infer_preferences(user_turn.content)
        working_memory = self._build_working_memory(tool_results)
        current_focus = self._infer_current_focus(tool_results, fallback=user_turn.content)
        next_question = self._extract_next_question(assistant_turn)
        next_action = self._infer_next_action(tool_results)
        summary = self._build_summary(session.domain_type, tool_results, assistant_turn)

        state = SessionStateDraft(
            goal=goal,
            constraints=constraints,
            preferences=preferences,
            working_memory=working_memory,
            current_focus=current_focus,
            next_question=next_question,
            next_action=next_action,
            summary=summary,
            last_tool_names=last_tool_names,
            state_payload={
                "domain_type": session.domain_type,
                "completed_tool_count": len(last_tool_names),
                "tool_statuses": {call["tool_name"]: call.get("status") for call in tool_calls},
            },
        )

        insights = self._build_insights(
            goal=goal,
            preferences=preferences,
            tool_calls=tool_calls,
            tool_results=tool_results,
        )
        thinking_steps = self._build_thinking_steps(
            session=session,
            tool_calls=tool_calls,
            tool_results=tool_results,
            next_question=next_question,
            summary=summary,
        )
        return state, insights, thinking_steps

    @staticmethod
    def _infer_constraints(user_message: str) -> list[str]:
        lowered = user_message.lower()
        constraints: list[str] = []
        if "solo" in lowered:
            constraints.append("solo execution preferred")
        if "低风险" in user_message or "risk" in lowered:
            constraints.append("risk sensitivity is high")
        if "deadline" in lowered or "截止" in user_message:
            constraints.append("time window is important")
        if "预算" in user_message or "budget" in lowered:
            constraints.append("budget should be considered")
        return constraints

    @staticmethod
    def _infer_preferences(user_message: str) -> list[str]:
        lowered = user_message.lower()
        preferences: list[str] = []
        keyword_map = {
            "margin": ("margin", "利润"),
            "sell_through_speed": ("sell-through", "动销", "出单"),
            "after_sales_risk": ("after-sales", "售后"),
            "reward_size": ("reward", "prize", "奖金"),
            "platform_taobao": ("taobao", "淘宝"),
            "platform_xianyu": ("xianyu", "闲鱼"),
            "solo_friendly": ("solo", "单人"),
        }
        for label, tokens in keyword_map.items():
            if any(token in lowered or token in user_message for token in tokens):
                preferences.append(label)
        return preferences

    @staticmethod
    def _build_working_memory(tool_results: dict[str, dict[str, Any]]) -> list[str]:
        shortlist_result = tool_results.get("selection_query") or tool_results.get("selection_compare")
        if shortlist_result and shortlist_result.get("shortlist"):
            return [
                f"{item.get('platform', 'unknown')}: {item.get('title', '')}".strip()
                for item in shortlist_result["shortlist"][:3]
            ]

        search_result = tool_results.get("opportunity_search")
        if search_result and search_result.get("items"):
            return [str(item.get("title", "")) for item in search_result["items"][:3]]

        explain_result = tool_results.get("opportunity_explain")
        if explain_result and explain_result.get("matched"):
            return [str(explain_result.get("activity", {}).get("title", ""))]

        return []

    @staticmethod
    def _infer_current_focus(tool_results: dict[str, dict[str, Any]], *, fallback: str) -> str | None:
        shortlist_result = tool_results.get("selection_query") or tool_results.get("selection_compare")
        if shortlist_result and shortlist_result.get("query_text"):
            return str(shortlist_result["query_text"])

        search_result = tool_results.get("opportunity_search")
        if search_result and search_result.get("query"):
            return str(search_result["query"])

        fallback_text = fallback.strip()
        return fallback_text[:120] if fallback_text else None

    @staticmethod
    def _extract_next_question(assistant_turn: str) -> str | None:
        for sentence in re.split(r"(?<=[.!?])\s+", assistant_turn.strip()):
            if "tell me" in sentence.lower():
                return sentence.strip()
        return None

    @staticmethod
    def _infer_next_action(tool_results: dict[str, dict[str, Any]]) -> str | None:
        shortlist_result = tool_results.get("selection_query") or tool_results.get("selection_compare")
        if shortlist_result:
            shortlist = shortlist_result.get("shortlist") or []
            if shortlist and shortlist[0].get("recommended_action"):
                return str(shortlist[0]["recommended_action"])

        next_action_result = tool_results.get("opportunity_next_action")
        if next_action_result and next_action_result.get("next_action"):
            return str(next_action_result["next_action"])

        return None

    def _build_summary(
        self,
        domain_type: str,
        tool_results: dict[str, dict[str, Any]],
        assistant_turn: str,
    ) -> str | None:
        shortlist_result = tool_results.get("selection_query")
        if shortlist_result:
            item_count = len(shortlist_result.get("items") or [])
            return f"Generated {item_count} selection candidates for {shortlist_result.get('query_text', 'current query')}."

        compare_result = tool_results.get("selection_compare")
        if compare_result:
            return (
                f"Compared {len(compare_result.get('compare_rows') or [])} platform views for "
                f"{compare_result.get('query_text', 'current query')}."
            )

        search_result = tool_results.get("opportunity_search")
        if search_result:
            return f"Generated {len(search_result.get('items') or [])} opportunity matches."

        explain_result = tool_results.get("opportunity_explain")
        if explain_result and explain_result.get("matched"):
            return f"Explained the opportunity {explain_result.get('activity', {}).get('title', 'selection')}."

        if domain_type:
            return assistant_turn.strip()[:200]
        return None

    def _build_insights(
        self,
        *,
        goal: str | None,
        preferences: list[str],
        tool_calls: list[dict[str, Any]],
        tool_results: dict[str, dict[str, Any]],
    ) -> list[InsightDraft]:
        insights: list[InsightDraft] = []
        if goal:
            insights.append(
                InsightDraft(
                    insight_type="goal",
                    content=goal,
                    importance=0.9,
                    payload={"source": "user_turn"},
                )
            )

        if preferences:
            insights.append(
                InsightDraft(
                    insight_type="preferences",
                    content="User preferences: " + ", ".join(preferences),
                    importance=0.7,
                    payload={"preferences": preferences},
                )
            )

        shortlist_result = tool_results.get("selection_query") or tool_results.get("selection_compare")
        if shortlist_result and shortlist_result.get("shortlist"):
            top_item = shortlist_result["shortlist"][0]
            insights.append(
                InsightDraft(
                    insight_type="top_candidate",
                    content=(
                        f"Top selection candidate: {top_item.get('title')} "
                        f"on {top_item.get('platform')} with opportunity {top_item.get('opportunity_score')}."
                    ),
                    importance=0.8,
                    payload={
                        "platform": top_item.get("platform"),
                        "opportunity_score": top_item.get("opportunity_score"),
                        "confidence_score": top_item.get("confidence_score"),
                    },
                )
            )

        opportunity_result = tool_results.get("opportunity_search")
        if opportunity_result and opportunity_result.get("items"):
            top_item = opportunity_result["items"][0]
            insights.append(
                InsightDraft(
                    insight_type="top_opportunity",
                    content=f"Top opportunity match: {top_item.get('title')}.",
                    importance=0.8,
                    payload={"item_id": top_item.get("id"), "score": top_item.get("score")},
                )
            )

        failed_tools = [call["tool_name"] for call in tool_calls if call.get("status") == "failed"]
        if failed_tools:
            insights.append(
                InsightDraft(
                    insight_type="reflection",
                    content="Execution had tool failures: " + ", ".join(failed_tools),
                    importance=0.6,
                    payload={"failed_tools": failed_tools},
                )
            )
        elif not shortlist_result and not opportunity_result:
            insights.append(
                InsightDraft(
                    insight_type="reflection",
                    content="The session still needs tighter user input before it can produce a strong result.",
                    importance=0.55,
                    payload={"reason": "low_signal"},
                )
            )

        return insights

    def _build_thinking_steps(
        self,
        *,
        session: AgentSession,
        tool_calls: list[dict[str, Any]],
        tool_results: dict[str, dict[str, Any]],
        next_question: str | None,
        summary: str | None,
    ) -> list[ThinkingStepDraft]:
        thinking_steps: list[ThinkingStepDraft] = [
            ThinkingStepDraft(
                phase="routing",
                summary=(
                    f"Resolved {len(tool_calls)} tool routes for domain {session.domain_type}: "
                    + ", ".join(call["tool_name"] for call in tool_calls)
                ).strip(),
                payload={"domain_type": session.domain_type},
            )
        ]

        for call in tool_calls:
            status = call.get("status", "planned")
            result_summary = call.get("result_summary") or {}
            thinking_steps.append(
                ThinkingStepDraft(
                    phase="tool_execution",
                    summary=f"Tool {call['tool_name']} finished with status {status}.",
                    tool_name=call["tool_name"],
                    payload=result_summary,
                )
            )

        if summary:
            thinking_steps.append(
                ThinkingStepDraft(
                    phase="synthesis",
                    summary=summary,
                    payload={"tool_result_keys": list(tool_results.keys())},
                )
            )

        if next_question:
            thinking_steps.append(
                ThinkingStepDraft(
                    phase="follow_up",
                    summary=f"Assistant follow-up question: {next_question}",
                    payload={"next_question": next_question},
                )
            )

        return thinking_steps
