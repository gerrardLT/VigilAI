"""SQLite repository for the reward-opportunity bounded context."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
import sqlite3
import uuid
from typing import Any, Iterator

from .models import RewardInvestigationAction, RewardInvestigationRun, RewardOpportunity


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, column_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def ensure_reward_opportunity_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_source_feeds (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_source_feeds",
        {
            "name": "TEXT",
            "source_type": "TEXT",
            "config_json": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_recall_candidates (
            id TEXT PRIMARY KEY,
            source_platform TEXT NOT NULL,
            source_url TEXT NOT NULL,
            title TEXT NOT NULL,
            recall_label TEXT NOT NULL,
            recall_reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_recall_candidates",
        {
            "source_platform": "TEXT",
            "source_url": "TEXT",
            "title": "TEXT",
            "recall_label": "TEXT",
            "recall_reason": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_investigation_runs (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            status TEXT NOT NULL,
            current_round INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_investigation_runs",
        {
            "candidate_id": "TEXT",
            "status": "TEXT",
            "current_round": "INTEGER",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_investigation_actions (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_url TEXT,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_investigation_actions",
        {
            "run_id": "TEXT",
            "action_type": "TEXT",
            "target_url": "TEXT",
            "status": "TEXT",
            "payload_json": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_opportunities (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_platform TEXT NOT NULL,
            source_url TEXT NOT NULL,
            ai_stage_2_label TEXT NOT NULL,
            ai_confidence REAL NOT NULL,
            reward_type TEXT,
            reward_value_text TEXT,
            action_required TEXT,
            ai_summary TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_opportunities",
        {
            "title": "TEXT",
            "source_platform": "TEXT",
            "source_url": "TEXT",
            "ai_stage_2_label": "TEXT",
            "ai_confidence": "REAL",
            "reward_type": "TEXT",
            "reward_value_text": "TEXT",
            "action_required": "TEXT",
            "ai_summary": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_opportunity_evidence (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            snippet TEXT NOT NULL,
            source_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_opportunity_evidence",
        {
            "opportunity_id": "TEXT",
            "evidence_type": "TEXT",
            "snippet": "TEXT",
            "source_url": "TEXT",
            "created_at": "TEXT",
        },
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_candidates_source_url ON reward_recall_candidates(source_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_runs_candidate ON reward_investigation_runs(candidate_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_actions_run ON reward_investigation_actions(run_id)")


class RewardOpportunityRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_data_dir()
        with self._get_connection() as conn:
            ensure_reward_opportunity_tables(conn)

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

    def ensure_schema(self) -> None:
        with self._get_connection() as conn:
            ensure_reward_opportunity_tables(conn)

    def get_overview_stats(self) -> dict[str, int]:
        with self._get_connection() as conn:
            source_count = conn.execute("SELECT COUNT(*) AS count FROM reward_source_feeds").fetchone()["count"]
            opportunity_count = conn.execute("SELECT COUNT(*) AS count FROM reward_opportunities").fetchone()["count"]
        return {
            "source_count": int(source_count),
            "opportunity_count": int(opportunity_count),
        }

    def create_recall_candidate(self, payload: dict[str, object]) -> str:
        candidate_id = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_recall_candidates (
                    id, source_platform, source_url, title, recall_label, recall_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    payload["source_platform"],
                    payload["source_url"],
                    payload["title"],
                    payload["recall_label"],
                    payload["recall_reason"],
                    now,
                ),
            )
        return candidate_id

    def create_investigation_run(self, payload: dict[str, object]) -> str:
        run_id = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_investigation_runs (
                    id, candidate_id, status, current_round, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    payload["candidate_id"],
                    payload["status"],
                    payload["current_round"],
                    now,
                ),
            )
        return run_id

    def append_investigation_action(self, run_id: str, payload: dict[str, object]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_investigation_actions (
                    id, run_id, action_type, target_url, status, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    run_id,
                    payload["action_type"],
                    payload.get("target_url"),
                    payload["status"],
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )

    def get_investigation_run(self, run_id: str) -> dict[str, object]:
        with self._get_connection() as conn:
            run_row = conn.execute(
                """
                SELECT id, candidate_id, status, current_round, created_at
                FROM reward_investigation_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            action_rows = conn.execute(
                """
                SELECT id, run_id, action_type, target_url, status, payload_json, created_at
                FROM reward_investigation_actions
                WHERE run_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (run_id,),
            ).fetchall()

        run = RewardInvestigationRun(
            id=run_row["id"],
            candidate_id=run_row["candidate_id"],
            status=run_row["status"],
            current_round=run_row["current_round"],
            created_at=datetime.fromisoformat(run_row["created_at"]),
            actions=[
                RewardInvestigationAction(
                    id=row["id"],
                    run_id=row["run_id"],
                    action_type=row["action_type"],
                    target_url=row["target_url"],
                    status=row["status"],
                    payload=json.loads(row["payload_json"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in action_rows
            ],
        )
        return run.model_dump(mode="json")

    def list_opportunities(self) -> list[RewardOpportunity]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, source_platform, source_url, ai_stage_2_label, ai_confidence,
                       reward_type, reward_value_text, action_required, ai_summary, created_at
                FROM reward_opportunities
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [
            RewardOpportunity(
                id=row["id"],
                title=row["title"],
                source_platform=row["source_platform"],
                source_url=row["source_url"],
                ai_stage_2_label=row["ai_stage_2_label"],
                ai_confidence=row["ai_confidence"],
                reward_type=row["reward_type"],
                reward_value_text=row["reward_value_text"],
                action_required=row["action_required"],
                ai_summary=row["ai_summary"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_opportunity(self, opportunity_id: str) -> RewardOpportunity | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, source_platform, source_url, ai_stage_2_label, ai_confidence,
                       reward_type, reward_value_text, action_required, ai_summary, created_at
                FROM reward_opportunities
                WHERE id = ?
                """,
                (opportunity_id,),
            ).fetchone()
        if row is None:
            return None
        return RewardOpportunity(
            id=row["id"],
            title=row["title"],
            source_platform=row["source_platform"],
            source_url=row["source_url"],
            ai_stage_2_label=row["ai_stage_2_label"],
            ai_confidence=row["ai_confidence"],
            reward_type=row["reward_type"],
            reward_value_text=row["reward_value_text"],
            action_required=row["action_required"],
            ai_summary=row["ai_summary"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
