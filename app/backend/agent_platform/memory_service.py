"""Long-term memory promotion and recall for agent sessions."""

from __future__ import annotations

from config import AGENT_MEMORY_IMPORTANCE_THRESHOLD, AGENT_MEMORY_RECALL_LIMIT

from .models import AgentInsight, AgentMemory, AgentSession, AgentSessionState, AgentTurn
from .repository import AgentPlatformRepository

_PERSISTENT_INSIGHT_TYPES = {
    "goal": "goal",
    "preferences": "preference",
    "top_candidate": "candidate",
    "top_opportunity": "candidate",
    "safety": "guardrail",
}


class MemoryService:
    _GLOBAL_MEMORY_TYPES = {"preference", "guardrail", "summary"}

    def __init__(
        self,
        repository: AgentPlatformRepository,
        *,
        importance_threshold: float = AGENT_MEMORY_IMPORTANCE_THRESHOLD,
        recall_limit: int = AGENT_MEMORY_RECALL_LIMIT,
    ) -> None:
        self.repository = repository
        self.importance_threshold = importance_threshold
        self.recall_limit = recall_limit

    def recall_session_memories(self, session_id: str, *, limit: int | None = None) -> list[AgentMemory]:
        return self.repository.list_memories(session_id, limit=limit or self.recall_limit)

    def recall_for_session(
        self,
        session: AgentSession,
        *,
        include_cross_session: bool = True,
        limit: int | None = None,
    ) -> list[AgentMemory]:
        total_limit = limit or self.recall_limit
        session_memories = self.repository.list_memories(session.id, limit=total_limit)
        if not include_cross_session or session.memory_scope == "session_only":
            return session_memories

        combined = list(session_memories)
        if session.memory_scope in {"domain", "global"}:
            domain_limit = max(1, total_limit // 2) if session.memory_scope == "domain" else max(1, total_limit // 3)
            combined.extend(
                self.repository.list_domain_memories(
                    session.domain_type,
                    limit=domain_limit,
                    exclude_session_id=session.id,
                )
            )

        if session.memory_scope == "global":
            global_limit = max(1, total_limit // 3)
            combined.extend(
                self.repository.list_global_memories(
                    limit=global_limit,
                    exclude_session_id=session.id,
                    allowed_memory_types=self._GLOBAL_MEMORY_TYPES,
                )
            )

        deduped: list[AgentMemory] = []
        seen_keys: set[tuple[str, str]] = set()
        for memory in combined:
            key = (memory.memory_type, memory.content)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(memory)
            if len(deduped) >= total_limit:
                break
        return deduped

    def promote_from_turn(
        self,
        *,
        session: AgentSession,
        user_turn: AgentTurn,
        session_state: AgentSessionState,
        insights: list[AgentInsight],
    ) -> list[AgentMemory]:
        memories: list[AgentMemory] = []
        seen_keys: set[tuple[str, str]] = set()

        for insight in insights:
            memory_type = _PERSISTENT_INSIGHT_TYPES.get(insight.insight_type)
            if memory_type is None or insight.importance < self.importance_threshold:
                continue

            key = (memory_type, insight.content)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            memories.append(
                self.repository.create_memory(
                    session.id,
                    source_turn_id=user_turn.id,
                    memory_type=memory_type,
                    content=insight.content,
                    importance=insight.importance,
                    payload={
                        **insight.payload,
                        "domain_type": session.domain_type,
                        "insight_type": insight.insight_type,
                    },
                )
            )

        if memories or not session_state.summary:
            return memories

        memories.append(
            self.repository.create_memory(
                session.id,
                source_turn_id=user_turn.id,
                memory_type="summary",
                content=session_state.summary,
                importance=max(self.importance_threshold - 0.05, 0.55),
                payload={
                    "domain_type": session.domain_type,
                    "source": "session_state",
                },
            )
        )
        return memories

    def build_context(self, session: AgentSession, *, limit: int | None = None) -> list[str]:
        return [item.content for item in self.recall_for_session(session, limit=limit)]
