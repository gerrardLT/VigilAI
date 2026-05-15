"""
SQLite repository for the shared agent platform layer.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
import sqlite3
import uuid
from typing import Any, Iterator, Optional

from .models import (
    AgentArtifact,
    AgentExecutionPlan,
    AgentExecutionPlanStep,
    AgentInsight,
    AgentJob,
    AgentMemory,
    AgentReflection,
    AgentSession,
    AgentSessionState,
    AgentThinkingStep,
    AgentTurn,
)
from .state_machine import (
    default_session_status,
    ensure_session_allows_turns,
    transition_session_status,
    validate_turn_role,
)


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, column_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def ensure_agent_platform_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            domain_type TEXT NOT NULL,
            entry_mode TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            policy_mode TEXT NOT NULL DEFAULT 'standard',
            memory_scope TEXT NOT NULL DEFAULT 'domain',
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_turn_at TEXT
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_sessions",
        {
            "domain_type": "TEXT",
            "entry_mode": "TEXT",
            "status": "TEXT",
            "policy_mode": "TEXT",
            "memory_scope": "TEXT",
            "title": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
            "last_turn_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_turns (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sequence_no INTEGER NOT NULL,
            tool_name TEXT,
            tool_payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_turns",
        {
            "session_id": "TEXT",
            "role": "TEXT",
            "content": "TEXT",
            "sequence_no": "INTEGER",
            "tool_name": "TEXT",
            "tool_payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_artifacts (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_artifacts",
        {
            "session_id": "TEXT",
            "artifact_type": "TEXT",
            "title": "TEXT",
            "content": "TEXT",
            "payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_execution_plans (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            source_turn_id TEXT,
            mode TEXT NOT NULL,
            summary TEXT NOT NULL,
            requested_steps TEXT,
            runnable_tools TEXT,
            blocked_tools TEXT,
            risk_flags TEXT,
            reasoning TEXT,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_execution_plans",
        {
            "session_id": "TEXT",
            "source_turn_id": "TEXT",
            "mode": "TEXT",
            "summary": "TEXT",
            "requested_steps": "TEXT",
            "runnable_tools": "TEXT",
            "blocked_tools": "TEXT",
            "risk_flags": "TEXT",
            "reasoning": "TEXT",
            "payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_session_states (
            session_id TEXT PRIMARY KEY,
            goal TEXT,
            constraints TEXT,
            preferences TEXT,
            working_memory TEXT,
            current_focus TEXT,
            next_question TEXT,
            next_action TEXT,
            summary TEXT,
            last_tool_names TEXT,
            state_payload TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_session_states",
        {
            "goal": "TEXT",
            "constraints": "TEXT",
            "preferences": "TEXT",
            "working_memory": "TEXT",
            "current_focus": "TEXT",
            "next_question": "TEXT",
            "next_action": "TEXT",
            "summary": "TEXT",
            "last_tool_names": "TEXT",
            "state_payload": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_insights (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            source_turn_id TEXT,
            insight_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL NOT NULL DEFAULT 0.5,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_insights",
        {
            "session_id": "TEXT",
            "source_turn_id": "TEXT",
            "insight_type": "TEXT",
            "content": "TEXT",
            "importance": "REAL",
            "payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_thinking_steps (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            source_turn_id TEXT,
            phase TEXT NOT NULL,
            summary TEXT NOT NULL,
            tool_name TEXT,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_thinking_steps",
        {
            "session_id": "TEXT",
            "source_turn_id": "TEXT",
            "phase": "TEXT",
            "summary": "TEXT",
            "tool_name": "TEXT",
            "payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_jobs_v2 (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            domain_type TEXT NOT NULL,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_by TEXT,
            input_payload TEXT,
            result_payload TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            finished_at TEXT
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_jobs_v2",
        {
            "session_id": "TEXT",
            "domain_type": "TEXT",
            "job_type": "TEXT",
            "status": "TEXT",
            "requested_by": "TEXT",
            "input_payload": "TEXT",
            "result_payload": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
            "finished_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            source_turn_id TEXT,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL NOT NULL DEFAULT 0.5,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_memories",
        {
            "session_id": "TEXT",
            "source_turn_id": "TEXT",
            "memory_type": "TEXT",
            "content": "TEXT",
            "importance": "REAL",
            "payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_reflections (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            source_turn_id TEXT,
            reflection_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            action_item TEXT,
            score REAL NOT NULL DEFAULT 0.5,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "agent_reflections",
        {
            "session_id": "TEXT",
            "source_turn_id": "TEXT",
            "reflection_type": "TEXT",
            "summary": "TEXT",
            "action_item": "TEXT",
            "score": "REAL",
            "payload": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_sessions_domain ON agent_sessions(domain_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_turns_session_seq ON agent_turns(session_id, sequence_no)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_artifacts_session ON agent_artifacts(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_execution_plans_session ON agent_execution_plans(session_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_session_states_session ON agent_session_states(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_insights_session ON agent_insights(session_id, created_at)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_thinking_steps_session ON agent_thinking_steps(session_id, created_at)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_jobs_v2_session ON agent_jobs_v2(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_jobs_v2_domain ON agent_jobs_v2(domain_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_memories_session ON agent_memories(session_id, created_at)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_reflections_session ON agent_reflections(session_id, created_at)"
    )


class AgentPlatformRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_data_dir()
        with self._get_connection() as conn:
            ensure_agent_platform_tables(conn)

    def _ensure_data_dir(self) -> None:
        data_dir = os.path.dirname(self.db_path)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_session(
        self,
        *,
        domain_type: str,
        entry_mode: str,
        policy_mode: str = "standard",
        memory_scope: str = "domain",
        title: Optional[str] = None,
    ) -> AgentSession:
        now = datetime.now(UTC)
        session = AgentSession(
            id=uuid.uuid4().hex,
            domain_type=domain_type,
            entry_mode=entry_mode,
            status=default_session_status(),
            policy_mode=policy_mode,
            memory_scope=memory_scope,
            title=title,
            created_at=now,
            updated_at=now,
            last_turn_at=None,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_sessions (
                    id, domain_type, entry_mode, status, policy_mode, memory_scope, title, created_at, updated_at, last_turn_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.domain_type,
                    session.entry_mode,
                    session.status,
                    session.policy_mode,
                    session.memory_scope,
                    session.title,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    None,
                ),
            )

        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, domain_type, entry_mode, status, policy_mode, memory_scope, title, created_at, updated_at, last_turn_at
                FROM agent_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()

        if not row:
            return None

        return self._row_to_session(row)

    def update_session_status(self, session_id: str, *, status: str) -> AgentSession:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"Agent session '{session_id}' not found")

            next_status = transition_session_status(row["status"], status)
            updated_at = datetime.now(UTC).isoformat()
            conn.execute(
                """
                UPDATE agent_sessions
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_status, updated_at, session_id),
            )

            refreshed = conn.execute("SELECT * FROM agent_sessions WHERE id = ?", (session_id,)).fetchone()

        return self._row_to_session(refreshed)

    def append_turn(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_payload: Optional[dict[str, Any]] = None,
    ) -> AgentTurn:
        validate_turn_role(role)

        with self._get_connection() as conn:
            session_row = conn.execute(
                "SELECT * FROM agent_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not session_row:
                raise ValueError(f"Agent session '{session_id}' not found")

            ensure_session_allows_turns(session_row["status"])

            next_sequence = conn.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM agent_turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            created_at = datetime.now(UTC)
            turn = AgentTurn(
                id=uuid.uuid4().hex,
                session_id=session_id,
                role=role,
                content=content,
                sequence_no=next_sequence,
                tool_name=tool_name,
                tool_payload=tool_payload or {},
                created_at=created_at,
            )

            conn.execute(
                """
                INSERT INTO agent_turns (
                    id, session_id, role, content, sequence_no, tool_name, tool_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.id,
                    turn.session_id,
                    turn.role,
                    turn.content,
                    turn.sequence_no,
                    turn.tool_name,
                    json.dumps(turn.tool_payload, ensure_ascii=False),
                    turn.created_at.isoformat(),
                ),
            )
            conn.execute(
                """
                UPDATE agent_sessions
                SET updated_at = ?, last_turn_at = ?
                WHERE id = ?
                """,
                (created_at.isoformat(), created_at.isoformat(), session_id),
            )

        return turn

    def list_turns(self, session_id: str) -> list[AgentTurn]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, sequence_no, tool_name, tool_payload, created_at
                FROM agent_turns
                WHERE session_id = ?
                ORDER BY sequence_no ASC, created_at ASC
                """,
                (session_id,),
            ).fetchall()

        return [self._row_to_turn(row) for row in rows]

    def create_artifact(
        self,
        session_id: str,
        *,
        artifact_type: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> AgentArtifact:
        created_at = datetime.now(UTC)
        artifact = AgentArtifact(
            id=uuid.uuid4().hex,
            session_id=session_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            payload=payload or {},
            created_at=created_at,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_artifacts (
                    id, session_id, artifact_type, title, content, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.session_id,
                    artifact.artifact_type,
                    artifact.title,
                    artifact.content,
                    json.dumps(artifact.payload, ensure_ascii=False),
                    artifact.created_at.isoformat(),
                ),
            )

        return artifact

    def list_artifacts(self, session_id: str) -> list[AgentArtifact]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, artifact_type, title, content, payload, created_at
                FROM agent_artifacts
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()

        return [self._row_to_artifact(row) for row in rows]

    def create_execution_plan(
        self,
        session_id: str,
        *,
        mode: str,
        summary: str,
        requested_steps: Optional[list[dict[str, Any]]] = None,
        runnable_tools: Optional[list[str]] = None,
        blocked_tools: Optional[list[str]] = None,
        risk_flags: Optional[list[str]] = None,
        reasoning: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        source_turn_id: Optional[str] = None,
    ) -> AgentExecutionPlan:
        created_at = datetime.now(UTC)
        plan = AgentExecutionPlan(
            id=uuid.uuid4().hex,
            session_id=session_id,
            source_turn_id=source_turn_id,
            mode=mode,
            summary=summary,
            requested_steps=[AgentExecutionPlanStep.model_validate(item) for item in (requested_steps or [])],
            runnable_tools=runnable_tools or [],
            blocked_tools=blocked_tools or [],
            risk_flags=risk_flags or [],
            reasoning=reasoning,
            payload=payload or {},
            created_at=created_at,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_execution_plans (
                    id, session_id, source_turn_id, mode, summary, requested_steps,
                    runnable_tools, blocked_tools, risk_flags, reasoning, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.id,
                    plan.session_id,
                    plan.source_turn_id,
                    plan.mode,
                    plan.summary,
                    json.dumps([item.model_dump(mode="json") for item in plan.requested_steps], ensure_ascii=False),
                    json.dumps(plan.runnable_tools, ensure_ascii=False),
                    json.dumps(plan.blocked_tools, ensure_ascii=False),
                    json.dumps(plan.risk_flags, ensure_ascii=False),
                    plan.reasoning,
                    json.dumps(plan.payload, ensure_ascii=False),
                    plan.created_at.isoformat(),
                ),
            )

        return plan

    def list_execution_plans(self, session_id: str, *, limit: int = 20) -> list[AgentExecutionPlan]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM agent_execution_plans
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        return [self._row_to_execution_plan(row) for row in rows]

    def upsert_session_state(
        self,
        session_id: str,
        *,
        goal: Optional[str] = None,
        constraints: Optional[list[str]] = None,
        preferences: Optional[list[str]] = None,
        working_memory: Optional[list[str]] = None,
        current_focus: Optional[str] = None,
        next_question: Optional[str] = None,
        next_action: Optional[str] = None,
        summary: Optional[str] = None,
        last_tool_names: Optional[list[str]] = None,
        state_payload: Optional[dict[str, Any]] = None,
    ) -> AgentSessionState:
        now = datetime.now(UTC)
        created_at = now.isoformat()
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT created_at FROM agent_session_states WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if existing and existing["created_at"]:
                created_at = existing["created_at"]

            conn.execute(
                """
                INSERT INTO agent_session_states (
                    session_id, goal, constraints, preferences, working_memory,
                    current_focus, next_question, next_action, summary,
                    last_tool_names, state_payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    goal = excluded.goal,
                    constraints = excluded.constraints,
                    preferences = excluded.preferences,
                    working_memory = excluded.working_memory,
                    current_focus = excluded.current_focus,
                    next_question = excluded.next_question,
                    next_action = excluded.next_action,
                    summary = excluded.summary,
                    last_tool_names = excluded.last_tool_names,
                    state_payload = excluded.state_payload,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    goal,
                    json.dumps(constraints or [], ensure_ascii=False),
                    json.dumps(preferences or [], ensure_ascii=False),
                    json.dumps(working_memory or [], ensure_ascii=False),
                    current_focus,
                    next_question,
                    next_action,
                    summary,
                    json.dumps(last_tool_names or [], ensure_ascii=False),
                    json.dumps(state_payload or {}, ensure_ascii=False),
                    created_at,
                    now.isoformat(),
                ),
            )
            row = conn.execute(
                "SELECT * FROM agent_session_states WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        return self._row_to_session_state(row)

    def get_session_state(self, session_id: str) -> Optional[AgentSessionState]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent_session_states WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_session_state(row) if row else None

    def create_insight(
        self,
        session_id: str,
        *,
        insight_type: str,
        content: str,
        importance: float = 0.5,
        payload: Optional[dict[str, Any]] = None,
        source_turn_id: Optional[str] = None,
    ) -> AgentInsight:
        created_at = datetime.now(UTC)
        insight = AgentInsight(
            id=uuid.uuid4().hex,
            session_id=session_id,
            source_turn_id=source_turn_id,
            insight_type=insight_type,
            content=content,
            importance=importance,
            payload=payload or {},
            created_at=created_at,
        )

        with self._get_connection() as conn:
            latest = conn.execute(
                """
                SELECT id FROM agent_insights
                WHERE session_id = ? AND insight_type = ? AND content = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id, insight_type, content),
            ).fetchone()
            if latest:
                row = conn.execute("SELECT * FROM agent_insights WHERE id = ?", (latest["id"],)).fetchone()
                return self._row_to_insight(row)

            conn.execute(
                """
                INSERT INTO agent_insights (
                    id, session_id, source_turn_id, insight_type, content, importance, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    insight.id,
                    insight.session_id,
                    insight.source_turn_id,
                    insight.insight_type,
                    insight.content,
                    insight.importance,
                    json.dumps(insight.payload, ensure_ascii=False),
                    insight.created_at.isoformat(),
                ),
            )

        return insight

    def list_insights(self, session_id: str, *, limit: int = 20) -> list[AgentInsight]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_insights
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._row_to_insight(row) for row in rows]

    def create_thinking_step(
        self,
        session_id: str,
        *,
        phase: str,
        summary: str,
        tool_name: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        source_turn_id: Optional[str] = None,
    ) -> AgentThinkingStep:
        created_at = datetime.now(UTC)
        step = AgentThinkingStep(
            id=uuid.uuid4().hex,
            session_id=session_id,
            source_turn_id=source_turn_id,
            phase=phase,
            summary=summary,
            tool_name=tool_name,
            payload=payload or {},
            created_at=created_at,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_thinking_steps (
                    id, session_id, source_turn_id, phase, summary, tool_name, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step.id,
                    step.session_id,
                    step.source_turn_id,
                    step.phase,
                    step.summary,
                    step.tool_name,
                    json.dumps(step.payload, ensure_ascii=False),
                    step.created_at.isoformat(),
                ),
            )

        return step

    def list_thinking_steps(self, session_id: str, *, limit: int = 50) -> list[AgentThinkingStep]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_thinking_steps
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._row_to_thinking_step(row) for row in rows]

    def create_memory(
        self,
        session_id: str,
        *,
        memory_type: str,
        content: str,
        importance: float = 0.5,
        payload: Optional[dict[str, Any]] = None,
        source_turn_id: Optional[str] = None,
    ) -> AgentMemory:
        created_at = datetime.now(UTC)
        memory = AgentMemory(
            id=uuid.uuid4().hex,
            session_id=session_id,
            source_turn_id=source_turn_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            payload=payload or {},
            created_at=created_at,
        )

        with self._get_connection() as conn:
            latest = conn.execute(
                """
                SELECT id FROM agent_memories
                WHERE session_id = ? AND memory_type = ? AND content = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id, memory_type, content),
            ).fetchone()
            if latest:
                row = conn.execute("SELECT * FROM agent_memories WHERE id = ?", (latest["id"],)).fetchone()
                return self._row_to_memory(row)

            conn.execute(
                """
                INSERT INTO agent_memories (
                    id, session_id, source_turn_id, memory_type, content, importance, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.session_id,
                    memory.source_turn_id,
                    memory.memory_type,
                    memory.content,
                    memory.importance,
                    json.dumps(memory.payload, ensure_ascii=False),
                    memory.created_at.isoformat(),
                ),
            )

        return memory

    def list_memories(self, session_id: str, *, limit: int = 20) -> list[AgentMemory]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_memories
                WHERE session_id = ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def list_domain_memories(
        self,
        domain_type: str,
        *,
        limit: int = 20,
        exclude_session_id: Optional[str] = None,
    ) -> list[AgentMemory]:
        query = """
            SELECT m.*
            FROM agent_memories m
            INNER JOIN agent_sessions s ON s.id = m.session_id
            WHERE s.domain_type = ?
        """
        params: list[Any] = [domain_type]
        if exclude_session_id:
            query += " AND m.session_id != ?"
            params.append(exclude_session_id)
        query += " ORDER BY m.importance DESC, m.created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def list_global_memories(
        self,
        *,
        limit: int = 20,
        exclude_session_id: Optional[str] = None,
        allowed_memory_types: Optional[set[str]] = None,
    ) -> list[AgentMemory]:
        query = "SELECT * FROM agent_memories WHERE 1 = 1"
        params: list[Any] = []
        if exclude_session_id:
            query += " AND session_id != ?"
            params.append(exclude_session_id)
        if allowed_memory_types:
            placeholders = ", ".join("?" for _ in allowed_memory_types)
            query += f" AND memory_type IN ({placeholders})"
            params.extend(sorted(allowed_memory_types))
        query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def create_reflection(
        self,
        session_id: str,
        *,
        reflection_type: str,
        summary: str,
        action_item: Optional[str] = None,
        score: float = 0.5,
        payload: Optional[dict[str, Any]] = None,
        source_turn_id: Optional[str] = None,
    ) -> AgentReflection:
        created_at = datetime.now(UTC)
        reflection = AgentReflection(
            id=uuid.uuid4().hex,
            session_id=session_id,
            source_turn_id=source_turn_id,
            reflection_type=reflection_type,
            summary=summary,
            action_item=action_item,
            score=score,
            payload=payload or {},
            created_at=created_at,
        )

        with self._get_connection() as conn:
            latest = conn.execute(
                """
                SELECT id FROM agent_reflections
                WHERE session_id = ? AND source_turn_id IS ? AND reflection_type = ? AND summary = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id, source_turn_id, reflection_type, summary),
            ).fetchone()
            if latest:
                row = conn.execute("SELECT * FROM agent_reflections WHERE id = ?", (latest["id"],)).fetchone()
                return self._row_to_reflection(row)

            conn.execute(
                """
                INSERT INTO agent_reflections (
                    id, session_id, source_turn_id, reflection_type, summary,
                    action_item, score, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reflection.id,
                    reflection.session_id,
                    reflection.source_turn_id,
                    reflection.reflection_type,
                    reflection.summary,
                    reflection.action_item,
                    reflection.score,
                    json.dumps(reflection.payload, ensure_ascii=False),
                    reflection.created_at.isoformat(),
                ),
            )

        return reflection

    def list_reflections(self, session_id: str, *, limit: int = 20) -> list[AgentReflection]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_reflections
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._row_to_reflection(row) for row in rows]

    def list_domain_reflections(
        self,
        domain_type: str,
        *,
        limit: int = 20,
        exclude_session_id: Optional[str] = None,
    ) -> list[AgentReflection]:
        query = """
            SELECT r.*
            FROM agent_reflections r
            INNER JOIN agent_sessions s ON s.id = r.session_id
            WHERE s.domain_type = ?
        """
        params: list[Any] = [domain_type]
        if exclude_session_id:
            query += " AND r.session_id != ?"
            params.append(exclude_session_id)
        query += " ORDER BY r.score DESC, r.created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_reflection(row) for row in rows]

    def list_global_reflections(
        self,
        *,
        limit: int = 20,
        exclude_session_id: Optional[str] = None,
        allowed_reflection_types: Optional[set[str]] = None,
    ) -> list[AgentReflection]:
        query = "SELECT * FROM agent_reflections WHERE 1 = 1"
        params: list[Any] = []
        if exclude_session_id:
            query += " AND session_id != ?"
            params.append(exclude_session_id)
        if allowed_reflection_types:
            placeholders = ", ".join("?" for _ in allowed_reflection_types)
            query += f" AND reflection_type IN ({placeholders})"
            params.extend(sorted(allowed_reflection_types))
        query += " ORDER BY score DESC, created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_reflection(row) for row in rows]

    def create_job(
        self,
        *,
        domain_type: str,
        job_type: str,
        status: str = "running",
        session_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        input_payload: Optional[dict[str, Any]] = None,
        result_payload: Optional[dict[str, Any]] = None,
    ) -> AgentJob:
        now = datetime.now(UTC)
        job = AgentJob(
            id=uuid.uuid4().hex,
            session_id=session_id,
            domain_type=domain_type,
            job_type=job_type,
            status=status,
            requested_by=requested_by,
            input_payload=input_payload or {},
            result_payload=result_payload or {},
            created_at=now,
            updated_at=now,
            finished_at=now if status in {"completed", "failed", "cancelled"} else None,
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_jobs_v2 (
                    id, session_id, domain_type, job_type, status, requested_by,
                    input_payload, result_payload, created_at, updated_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.session_id,
                    job.domain_type,
                    job.job_type,
                    job.status,
                    job.requested_by,
                    json.dumps(job.input_payload, ensure_ascii=False),
                    json.dumps(job.result_payload, ensure_ascii=False),
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.finished_at.isoformat() if job.finished_at else None,
                ),
            )
        return job

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        result_payload: Optional[dict[str, Any]] = None,
    ) -> AgentJob:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_jobs_v2 WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                raise ValueError(f"Agent job '{job_id}' not found")

            next_status = status or row["status"]
            next_result_payload = result_payload
            if next_result_payload is None:
                next_result_payload = json.loads(row["result_payload"] or "{}")

            finished_at = row["finished_at"]
            if next_status in {"completed", "failed", "cancelled"}:
                finished_at = datetime.now(UTC).isoformat()

            conn.execute(
                """
                UPDATE agent_jobs_v2
                SET status = ?, result_payload = ?, updated_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (
                    next_status,
                    json.dumps(next_result_payload, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                    finished_at,
                    job_id,
                ),
            )
            refreshed = conn.execute("SELECT * FROM agent_jobs_v2 WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(refreshed)

    def get_job(self, job_id: str) -> Optional[AgentJob]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_jobs_v2 WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(
        self,
        *,
        domain_type: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[AgentJob]:
        conditions: list[str] = []
        params: list[Any] = []
        if domain_type:
            conditions.append("domain_type = ?")
            params.append(domain_type)
        if job_type:
            conditions.append("job_type = ?")
            params.append(job_type)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM agent_jobs_v2
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> AgentSession:
        return AgentSession(
            id=row["id"],
            domain_type=row["domain_type"],
            entry_mode=row["entry_mode"],
            status=row["status"],
            policy_mode=row["policy_mode"] or "standard",
            memory_scope=row["memory_scope"] or "domain",
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_turn_at=datetime.fromisoformat(row["last_turn_at"]) if row["last_turn_at"] else None,
        )

    @staticmethod
    def _row_to_turn(row: sqlite3.Row) -> AgentTurn:
        return AgentTurn(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            sequence_no=row["sequence_no"],
            tool_name=row["tool_name"],
            tool_payload=json.loads(row["tool_payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row) -> AgentArtifact:
        return AgentArtifact(
            id=row["id"],
            session_id=row["session_id"],
            artifact_type=row["artifact_type"],
            title=row["title"],
            content=row["content"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_execution_plan(row: sqlite3.Row) -> AgentExecutionPlan:
        return AgentExecutionPlan(
            id=row["id"],
            session_id=row["session_id"],
            source_turn_id=row["source_turn_id"],
            mode=row["mode"],
            summary=row["summary"],
            requested_steps=[
                AgentExecutionPlanStep.model_validate(item)
                for item in json.loads(row["requested_steps"] or "[]")
            ],
            runnable_tools=json.loads(row["runnable_tools"] or "[]"),
            blocked_tools=json.loads(row["blocked_tools"] or "[]"),
            risk_flags=json.loads(row["risk_flags"] or "[]"),
            reasoning=row["reasoning"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_session_state(row: sqlite3.Row) -> AgentSessionState:
        return AgentSessionState(
            session_id=row["session_id"],
            goal=row["goal"],
            constraints=json.loads(row["constraints"] or "[]"),
            preferences=json.loads(row["preferences"] or "[]"),
            working_memory=json.loads(row["working_memory"] or "[]"),
            current_focus=row["current_focus"],
            next_question=row["next_question"],
            next_action=row["next_action"],
            summary=row["summary"],
            last_tool_names=json.loads(row["last_tool_names"] or "[]"),
            state_payload=json.loads(row["state_payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_insight(row: sqlite3.Row) -> AgentInsight:
        return AgentInsight(
            id=row["id"],
            session_id=row["session_id"],
            source_turn_id=row["source_turn_id"],
            insight_type=row["insight_type"],
            content=row["content"],
            importance=row["importance"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_thinking_step(row: sqlite3.Row) -> AgentThinkingStep:
        return AgentThinkingStep(
            id=row["id"],
            session_id=row["session_id"],
            source_turn_id=row["source_turn_id"],
            phase=row["phase"],
            summary=row["summary"],
            tool_name=row["tool_name"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> AgentMemory:
        return AgentMemory(
            id=row["id"],
            session_id=row["session_id"],
            source_turn_id=row["source_turn_id"],
            memory_type=row["memory_type"],
            content=row["content"],
            importance=row["importance"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_reflection(row: sqlite3.Row) -> AgentReflection:
        return AgentReflection(
            id=row["id"],
            session_id=row["session_id"],
            source_turn_id=row["source_turn_id"],
            reflection_type=row["reflection_type"],
            summary=row["summary"],
            action_item=row["action_item"],
            score=row["score"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> AgentJob:
        return AgentJob(
            id=row["id"],
            session_id=row["session_id"],
            domain_type=row["domain_type"],
            job_type=row["job_type"],
            status=row["status"],
            requested_by=row["requested_by"],
            input_payload=json.loads(row["input_payload"] or "{}"),
            result_payload=json.loads(row["result_payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        )
