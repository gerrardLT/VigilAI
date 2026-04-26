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

from .models import AgentArtifact, AgentSession, AgentTurn
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

    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_sessions_domain ON agent_sessions(domain_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_turns_session_seq ON agent_turns(session_id, sequence_no)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_artifacts_session ON agent_artifacts(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_jobs_v2_session ON agent_jobs_v2(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_jobs_v2_domain ON agent_jobs_v2(domain_type)")


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

    def create_session(self, *, domain_type: str, entry_mode: str, title: Optional[str] = None) -> AgentSession:
        now = datetime.now(UTC)
        session = AgentSession(
            id=uuid.uuid4().hex,
            domain_type=domain_type,
            entry_mode=entry_mode,
            status=default_session_status(),
            title=title,
            created_at=now,
            updated_at=now,
            last_turn_at=None,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_sessions (
                    id, domain_type, entry_mode, status, title, created_at, updated_at, last_turn_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.domain_type,
                    session.entry_mode,
                    session.status,
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
                SELECT id, domain_type, entry_mode, status, title, created_at, updated_at, last_turn_at
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

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> AgentSession:
        return AgentSession(
            id=row["id"],
            domain_type=row["domain_type"],
            entry_mode=row["entry_mode"],
            status=row["status"],
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
