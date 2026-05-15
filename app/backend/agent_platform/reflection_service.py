"""Turn-level reflection capture for agent sessions."""

from __future__ import annotations

from typing import Any

from config import AGENT_REFLECTION_RECALL_LIMIT

from .models import AgentInsight, AgentReflection, AgentSession, AgentSessionState, AgentTurn
from .repository import AgentPlatformRepository


class ReflectionService:
    _GLOBAL_REFLECTION_TYPES = {
        "execution_review",
        "failure_review",
        "intake_review",
        "safety_review",
    }

    def __init__(
        self,
        repository: AgentPlatformRepository,
        *,
        recall_limit: int = AGENT_REFLECTION_RECALL_LIMIT,
    ) -> None:
        self.repository = repository
        self.recall_limit = recall_limit

    def recall_session_reflections(self, session_id: str, *, limit: int | None = None) -> list[AgentReflection]:
        return self.repository.list_reflections(session_id, limit=limit or self.recall_limit)

    def recall_for_session(
        self,
        session: AgentSession,
        *,
        include_cross_session: bool = True,
        limit: int | None = None,
    ) -> list[AgentReflection]:
        total_limit = limit or self.recall_limit
        session_reflections = self.repository.list_reflections(session.id, limit=total_limit)
        if not include_cross_session or session.memory_scope == "session_only":
            return session_reflections

        combined = list(session_reflections)
        if session.memory_scope in {"domain", "global"}:
            domain_limit = max(1, total_limit // 2) if session.memory_scope == "domain" else max(1, total_limit // 3)
            combined.extend(
                self.repository.list_domain_reflections(
                    session.domain_type,
                    limit=domain_limit,
                    exclude_session_id=session.id,
                )
            )

        if session.memory_scope == "global":
            global_limit = max(1, total_limit // 3)
            combined.extend(
                self.repository.list_global_reflections(
                    limit=global_limit,
                    exclude_session_id=session.id,
                    allowed_reflection_types=self._GLOBAL_REFLECTION_TYPES,
                )
            )

        deduped: list[AgentReflection] = []
        seen_keys: set[tuple[str, str]] = set()
        for reflection in combined:
            key = (reflection.reflection_type, reflection.summary)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(reflection)
            if len(deduped) >= total_limit:
                break
        return deduped

    def create_turn_reflection(
        self,
        *,
        session: AgentSession,
        user_turn: AgentTurn,
        session_state: AgentSessionState,
        tool_calls: list[dict[str, Any]],
        insights: list[AgentInsight],
    ) -> AgentReflection:
        blocked_tools = [call["tool_name"] for call in tool_calls if call.get("status") == "blocked"]
        failed_tools = [call["tool_name"] for call in tool_calls if call.get("status") == "failed"]
        completed_tools = [call["tool_name"] for call in tool_calls if call.get("status") == "completed"]

        reflection_type = "execution_review"
        summary = (
            f"Completed {len(completed_tools)} tool call(s) and generated {len(insights)} insight(s) for this turn."
        )
        score = 0.8

        if blocked_tools:
            reflection_type = "safety_review"
            summary = (
                f"Blocked {len(blocked_tools)} tool route(s) after safety review. "
                "The request needs a safer reformulation before execution."
            )
            score = 0.25
        elif failed_tools:
            reflection_type = "failure_review"
            summary = (
                f"Completed {len(completed_tools)} tool call(s) but {len(failed_tools)} failed. "
                "The next turn should tighten inputs or repair tool coverage."
            )
            score = 0.45
        elif not completed_tools:
            reflection_type = "intake_review"
            summary = "No tool completed on this turn. The next turn should clarify scope before execution."
            score = 0.6

        action_item = session_state.next_question or session_state.next_action
        if action_item is None and reflection_type == "safety_review":
            action_item = "Reframe the request within allowed research boundaries."

        return self.repository.create_reflection(
            session.id,
            source_turn_id=user_turn.id,
            reflection_type=reflection_type,
            summary=summary,
            action_item=action_item,
            score=score,
            payload={
                "domain_type": session.domain_type,
                "blocked_tools": blocked_tools,
                "failed_tools": failed_tools,
                "completed_tools": completed_tools,
                "insight_count": len(insights),
            },
        )
