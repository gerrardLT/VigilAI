"""SQLite repository for the reward-opportunity bounded context."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
import sqlite3
import uuid
from typing import Any, Iterator

from .models import (
    RewardCrawlJob,
    RewardEvaluationRun,
    RewardInvestigationAction,
    RewardInvestigationRun,
    RewardOpportunity,
    RewardOpportunityEvidence,
    RewardRawDocument,
    RewardSourceFeed,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


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
            source_platform TEXT,
            entry_url TEXT,
            status TEXT NOT NULL DEFAULT 'idle',
            config_json TEXT NOT NULL DEFAULT '{}',
            last_crawled_at TEXT,
            last_success_at TEXT,
            last_error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_source_feeds",
        {
            "source_platform": "TEXT",
            "entry_url": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'idle'",
            "config_json": "TEXT NOT NULL DEFAULT '{}'",
            "last_crawled_at": "TEXT",
            "last_success_at": "TEXT",
            "last_error_message": "TEXT",
            "updated_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_scout_settings (
            id TEXT PRIMARY KEY,
            query_templates_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_discovery_ignored (
            id TEXT PRIMARY KEY,
            dedupe_key TEXT NOT NULL UNIQUE,
            entry_url TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_source_audit (
            id TEXT PRIMARY KEY,
            source_feed_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_crawl_jobs (
            id TEXT PRIMARY KEY,
            source_feed_id TEXT NOT NULL,
            status TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'scheduled',
            target_url TEXT,
            document_count INTEGER NOT NULL DEFAULT 0,
            candidate_count INTEGER NOT NULL DEFAULT 0,
            opportunity_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_raw_documents (
            id TEXT PRIMARY KEY,
            crawl_job_id TEXT,
            source_feed_id TEXT,
            source_platform TEXT NOT NULL,
            source_type TEXT,
            source_url TEXT NOT NULL,
            canonical_url TEXT,
            title TEXT NOT NULL,
            body TEXT,
            summary TEXT,
            published_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_recall_candidates (
            id TEXT PRIMARY KEY,
            raw_document_id TEXT,
            source_platform TEXT NOT NULL,
            source_url TEXT NOT NULL,
            title TEXT NOT NULL,
            recall_label TEXT NOT NULL,
            recall_reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(conn, "reward_recall_candidates", {"raw_document_id": "TEXT"})

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

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_opportunities (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            normalized_title TEXT,
            source_platform TEXT NOT NULL,
            source_type TEXT,
            source_url TEXT NOT NULL,
            canonical_url TEXT,
            published_at TEXT,
            discovered_at TEXT,
            content_language TEXT,
            raw_text_excerpt TEXT,
            opportunity_type TEXT,
            reward_type TEXT,
            reward_value_text TEXT,
            action_required TEXT,
            eligibility TEXT,
            deadline_text TEXT,
            deadline_at TEXT,
            region_limit TEXT,
            platform_limit TEXT,
            ai_stage_1_recall_reason TEXT,
            ai_stage_2_label TEXT NOT NULL,
            ai_confidence REAL NOT NULL,
            ai_summary TEXT,
            ai_reasoning_brief TEXT,
            ai_missing_evidence TEXT NOT NULL DEFAULT '[]',
            ai_risk_flags TEXT NOT NULL DEFAULT '[]',
            ai_structured_evidence TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            dedupe_key TEXT,
            content_hash TEXT,
            last_evaluated_at TEXT,
            recheck_after TEXT,
            external_links_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "reward_opportunities",
        {
            "normalized_title": "TEXT",
            "source_type": "TEXT",
            "canonical_url": "TEXT",
            "published_at": "TEXT",
            "discovered_at": "TEXT",
            "content_language": "TEXT",
            "raw_text_excerpt": "TEXT",
            "opportunity_type": "TEXT",
            "eligibility": "TEXT",
            "deadline_text": "TEXT",
            "deadline_at": "TEXT",
            "region_limit": "TEXT",
            "platform_limit": "TEXT",
            "ai_stage_1_recall_reason": "TEXT",
            "ai_reasoning_brief": "TEXT",
            "ai_missing_evidence": "TEXT NOT NULL DEFAULT '[]'",
            "ai_risk_flags": "TEXT NOT NULL DEFAULT '[]'",
            "ai_structured_evidence": "TEXT NOT NULL DEFAULT '{}'",
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "dedupe_key": "TEXT",
            "content_hash": "TEXT",
            "last_evaluated_at": "TEXT",
            "recheck_after": "TEXT",
            "external_links_json": "TEXT NOT NULL DEFAULT '[]'",
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
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(conn, "reward_opportunity_evidence", {"metadata_json": "TEXT NOT NULL DEFAULT '{}'"})

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_evaluation_runs (
            id TEXT PRIMARY KEY,
            candidate_id TEXT,
            opportunity_id TEXT,
            ai_stage_2_label TEXT NOT NULL,
            ai_confidence REAL NOT NULL,
            ai_summary TEXT,
            ai_reasoning_brief TEXT,
            ai_missing_evidence TEXT NOT NULL DEFAULT '[]',
            ai_risk_flags TEXT NOT NULL DEFAULT '[]',
            ai_structured_evidence TEXT NOT NULL DEFAULT '{}',
            needs_investigation INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_agent_runs (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_agent_steps (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT NOT NULL DEFAULT '{}',
            output_json TEXT NOT NULL DEFAULT '{}',
            latency_ms INTEGER NOT NULL DEFAULT 0,
            failure_type TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_tool_calls (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT NOT NULL DEFAULT '{}',
            output_json TEXT NOT NULL DEFAULT '{}',
            latency_ms INTEGER NOT NULL DEFAULT 0,
            failure_type TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_evaluator_snapshots (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_candidates_source_url ON reward_recall_candidates(source_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_runs_candidate ON reward_investigation_runs(candidate_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_actions_run ON reward_investigation_actions(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_jobs_feed ON reward_crawl_jobs(source_feed_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_raw_job ON reward_raw_documents(crawl_job_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_evidence_opp ON reward_opportunity_evidence(opportunity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_opps_dedupe ON reward_opportunities(dedupe_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_audit_source ON reward_source_audit(source_feed_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_agent_runs_thread ON reward_agent_runs(thread_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_agent_steps_run ON reward_agent_steps(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_tool_calls_run ON reward_tool_calls(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_evaluator_snapshots_run ON reward_evaluator_snapshots(run_id)")


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

    def upsert_source_feed(self, payload: dict[str, Any]) -> str:
        feed_id = str(payload.get("id") or uuid.uuid4().hex)
        now = _now_iso()
        with self._get_connection() as conn:
            existing = conn.execute("SELECT id, created_at FROM reward_source_feeds WHERE id = ?", (feed_id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO reward_source_feeds (
                    id, name, source_type, source_platform, entry_url, status, config_json,
                    last_crawled_at, last_success_at, last_error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    source_type=excluded.source_type,
                    source_platform=excluded.source_platform,
                    entry_url=excluded.entry_url,
                    status=excluded.status,
                    config_json=excluded.config_json,
                    last_crawled_at=excluded.last_crawled_at,
                    last_success_at=excluded.last_success_at,
                    last_error_message=excluded.last_error_message,
                    updated_at=excluded.updated_at
                """,
                (
                    feed_id,
                    payload["name"],
                    payload["source_type"],
                    payload.get("source_platform"),
                    payload.get("entry_url"),
                    payload.get("status", "idle"),
                    json.dumps(payload.get("config", {}), ensure_ascii=False),
                    payload.get("last_crawled_at"),
                    payload.get("last_success_at"),
                    payload.get("last_error_message"),
                    created_at,
                    now,
                ),
            )
        return feed_id

    def list_source_feeds(self) -> list[RewardSourceFeed]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, source_type, source_platform, entry_url, status, config_json,
                       last_crawled_at, last_success_at, last_error_message, created_at, updated_at
                FROM reward_source_feeds
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()
        return [
            RewardSourceFeed(
                id=row["id"],
                name=row["name"],
                source_type=row["source_type"],
                source_platform=row["source_platform"],
                entry_url=row["entry_url"],
                status=row["status"],
                config=_json_loads(row["config_json"], {}),
                last_crawled_at=_parse_dt(row["last_crawled_at"]),
                last_success_at=_parse_dt(row["last_success_at"]),
                last_error_message=row["last_error_message"],
                created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
                updated_at=_parse_dt(row["updated_at"]) or datetime.now(UTC),
            )
            for row in rows
        ]

    def get_source_feed(self, source_feed_id: str) -> RewardSourceFeed | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, source_type, source_platform, entry_url, status, config_json,
                       last_crawled_at, last_success_at, last_error_message, created_at, updated_at
                FROM reward_source_feeds
                WHERE id = ?
                """,
                (source_feed_id,),
            ).fetchone()
        if row is None:
            return None
        return RewardSourceFeed(
            id=row["id"],
            name=row["name"],
            source_type=row["source_type"],
            source_platform=row["source_platform"],
            entry_url=row["entry_url"],
            status=row["status"],
            config=_json_loads(row["config_json"], {}),
            last_crawled_at=_parse_dt(row["last_crawled_at"]),
            last_success_at=_parse_dt(row["last_success_at"]),
            last_error_message=row["last_error_message"],
            created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
            updated_at=_parse_dt(row["updated_at"]) or datetime.now(UTC),
        )

    def get_scout_settings(self) -> dict[str, Any]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, query_templates_json, updated_at
                FROM reward_scout_settings
                WHERE id = 'default'
                """
            ).fetchone()
        if row is None:
            return {"id": "default", "query_templates": [], "updated_at": None}
        return {
            "id": row["id"],
            "query_templates": _json_loads(row["query_templates_json"], []),
            "updated_at": row["updated_at"],
        }

    def update_scout_settings(self, query_templates: list[str]) -> dict[str, Any]:
        updated_at = _now_iso()
        normalized = [item.strip() for item in query_templates if item and item.strip()]
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_scout_settings (id, query_templates_json, updated_at)
                VALUES ('default', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    query_templates_json=excluded.query_templates_json,
                    updated_at=excluded.updated_at
                """,
                (json.dumps(normalized, ensure_ascii=False), updated_at),
            )
        return {"id": "default", "query_templates": normalized, "updated_at": updated_at}

    def create_crawl_job(self, payload: dict[str, Any]) -> str:
        job_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_crawl_jobs (
                    id, source_feed_id, status, mode, target_url,
                    document_count, candidate_count, opportunity_count, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    payload["source_feed_id"],
                    payload["status"],
                    payload.get("mode", "scheduled"),
                    payload.get("target_url"),
                    payload.get("document_count", 0),
                    payload.get("candidate_count", 0),
                    payload.get("opportunity_count", 0),
                    payload.get("error_message"),
                    _now_iso(),
                ),
            )
        return job_id

    def update_crawl_job(self, job_id: str, payload: dict[str, Any]) -> None:
        columns = {
            "status": payload.get("status"),
            "document_count": payload.get("document_count"),
            "candidate_count": payload.get("candidate_count"),
            "opportunity_count": payload.get("opportunity_count"),
            "error_message": payload.get("error_message"),
            "completed_at": payload.get("completed_at"),
        }
        assignments = ", ".join(f"{key} = ?" for key, value in columns.items() if value is not None)
        values = [value for value in columns.values() if value is not None]
        if not assignments:
            return
        with self._get_connection() as conn:
            conn.execute(f"UPDATE reward_crawl_jobs SET {assignments} WHERE id = ?", (*values, job_id))

    def list_recent_crawl_jobs(self, limit: int = 20) -> list[RewardCrawlJob]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, source_feed_id, status, mode, target_url, document_count, candidate_count,
                       opportunity_count, error_message, created_at, completed_at
                FROM reward_crawl_jobs
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            RewardCrawlJob(
                id=row["id"],
                source_feed_id=row["source_feed_id"],
                status=row["status"],
                mode=row["mode"],
                target_url=row["target_url"],
                document_count=row["document_count"],
                candidate_count=row["candidate_count"],
                opportunity_count=row["opportunity_count"],
                error_message=row["error_message"],
                created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
                completed_at=_parse_dt(row["completed_at"]),
            )
            for row in rows
        ]

    def list_recent_crawl_jobs_for_source(self, source_feed_id: str, limit: int = 10) -> list[RewardCrawlJob]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, source_feed_id, status, mode, target_url, document_count, candidate_count,
                       opportunity_count, error_message, created_at, completed_at
                FROM reward_crawl_jobs
                WHERE source_feed_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (source_feed_id, limit),
            ).fetchall()
        return [
            RewardCrawlJob(
                id=row["id"],
                source_feed_id=row["source_feed_id"],
                status=row["status"],
                mode=row["mode"],
                target_url=row["target_url"],
                document_count=row["document_count"],
                candidate_count=row["candidate_count"],
                opportunity_count=row["opportunity_count"],
                error_message=row["error_message"],
                created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
                completed_at=_parse_dt(row["completed_at"]),
            )
            for row in rows
        ]

    def update_source_feed_runtime(
        self,
        source_feed_id: str,
        *,
        status: str,
        last_crawled_at: str | None = None,
        last_success_at: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE reward_source_feeds
                SET status = ?, last_crawled_at = ?, last_success_at = ?, last_error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    last_crawled_at,
                    last_success_at,
                    last_error_message,
                    _now_iso(),
                    source_feed_id,
                ),
            )

    def update_source_feed_config(self, source_feed_id: str, config_patch: dict[str, Any]) -> RewardSourceFeed | None:
        current = self.get_source_feed(source_feed_id)
        if current is None:
            return None
        merged_config = dict(current.config or {})
        merged_config.update(config_patch)
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE reward_source_feeds
                SET config_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(merged_config, ensure_ascii=False), _now_iso(), source_feed_id),
            )
        return self.get_source_feed(source_feed_id)

    def update_source_feed_fields(self, source_feed_id: str, payload: dict[str, Any]) -> RewardSourceFeed | None:
        current = self.get_source_feed(source_feed_id)
        if current is None:
            return None
        columns = {
            "name": payload.get("name", current.name),
            "source_type": payload.get("source_type", current.source_type),
            "source_platform": payload.get("source_platform", current.source_platform),
            "entry_url": payload.get("entry_url", current.entry_url),
            "status": payload.get("status", current.status),
            "config_json": json.dumps(payload.get("config", current.config), ensure_ascii=False),
            "updated_at": _now_iso(),
        }
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE reward_source_feeds
                SET name = ?, source_type = ?, source_platform = ?, entry_url = ?, status = ?, config_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    columns["name"],
                    columns["source_type"],
                    columns["source_platform"],
                    columns["entry_url"],
                    columns["status"],
                    columns["config_json"],
                    columns["updated_at"],
                    source_feed_id,
                ),
            )
        return self.get_source_feed(source_feed_id)

    def append_source_audit(self, source_feed_id: str, action_type: str, payload: dict[str, Any] | None = None) -> str:
        audit_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_source_audit (id, source_feed_id, action_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (audit_id, source_feed_id, action_type, json.dumps(payload or {}, ensure_ascii=False), _now_iso()),
            )
        return audit_id

    def list_source_audit(self, source_feed_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, source_feed_id, action_type, payload_json, created_at
                FROM reward_source_audit
                WHERE source_feed_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (source_feed_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "source_feed_id": row["source_feed_id"],
                "action_type": row["action_type"],
                "payload": _json_loads(row["payload_json"], {}),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def ignore_discovery_candidate(self, dedupe_key: str, entry_url: str, reason: str | None = None) -> dict[str, Any]:
        now = _now_iso()
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT id, created_at FROM reward_discovery_ignored WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()
            ignored_id = existing["id"] if existing else uuid.uuid4().hex
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO reward_discovery_ignored (id, dedupe_key, entry_url, reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    entry_url = excluded.entry_url,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (ignored_id, dedupe_key, entry_url, reason, created_at, now),
            )
        return {
            "id": ignored_id,
            "dedupe_key": dedupe_key,
            "entry_url": entry_url,
            "reason": reason,
            "created_at": created_at,
            "updated_at": now,
        }

    def unignore_discovery_candidate(self, dedupe_key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM reward_discovery_ignored WHERE dedupe_key = ?", (dedupe_key,))
        return bool(cursor.rowcount)

    def list_ignored_discovery_candidates(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, dedupe_key, entry_url, reason, created_at, updated_at
                FROM reward_discovery_ignored
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_raw_document(self, payload: dict[str, Any]) -> str:
        document_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_raw_documents (
                    id, crawl_job_id, source_feed_id, source_platform, source_type,
                    source_url, canonical_url, title, body, summary, published_at, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    payload.get("crawl_job_id"),
                    payload.get("source_feed_id"),
                    payload["source_platform"],
                    payload.get("source_type"),
                    payload["source_url"],
                    payload.get("canonical_url"),
                    payload["title"],
                    payload.get("body"),
                    payload.get("summary"),
                    payload.get("published_at"),
                    json.dumps(payload.get("metadata", {}), ensure_ascii=False),
                    _now_iso(),
                ),
            )
        return document_id

    def list_raw_documents(self, crawl_job_id: str | None = None) -> list[RewardRawDocument]:
        sql = """
            SELECT id, crawl_job_id, source_feed_id, source_platform, source_type, source_url,
                   canonical_url, title, body, summary, published_at, metadata_json, created_at
            FROM reward_raw_documents
        """
        params: tuple[Any, ...] = ()
        if crawl_job_id:
            sql += " WHERE crawl_job_id = ?"
            params = (crawl_job_id,)
        sql += " ORDER BY created_at DESC, id DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            RewardRawDocument(
                id=row["id"],
                crawl_job_id=row["crawl_job_id"],
                source_feed_id=row["source_feed_id"],
                source_platform=row["source_platform"],
                source_type=row["source_type"],
                source_url=row["source_url"],
                canonical_url=row["canonical_url"],
                title=row["title"],
                body=row["body"],
                summary=row["summary"],
                published_at=_parse_dt(row["published_at"]),
                metadata=_json_loads(row["metadata_json"], {}),
                created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
            )
            for row in rows
        ]

    def create_recall_candidate(self, payload: dict[str, object]) -> str:
        candidate_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_recall_candidates (
                    id, raw_document_id, source_platform, source_url, title, recall_label, recall_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    payload.get("raw_document_id"),
                    payload["source_platform"],
                    payload["source_url"],
                    payload["title"],
                    payload["recall_label"],
                    payload["recall_reason"],
                    _now_iso(),
                ),
            )
        return candidate_id

    def list_recall_candidates(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, raw_document_id, source_platform, source_url, title, recall_label, recall_reason, created_at
                FROM reward_recall_candidates
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_investigation_run(self, payload: dict[str, object]) -> str:
        run_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_investigation_runs (
                    id, candidate_id, status, current_round, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, payload["candidate_id"], payload["status"], payload["current_round"], _now_iso()),
            )
        return run_id

    def update_investigation_run(self, run_id: str, payload: dict[str, Any]) -> None:
        assignments = []
        values: list[Any] = []
        for key in ("status", "current_round"):
            if key in payload:
                assignments.append(f"{key} = ?")
                values.append(payload[key])
        if not assignments:
            return
        with self._get_connection() as conn:
            conn.execute(f"UPDATE reward_investigation_runs SET {', '.join(assignments)} WHERE id = ?", (*values, run_id))

    def append_investigation_action(self, run_id: str, payload: dict[str, object]) -> None:
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
                    _now_iso(),
                ),
            )

    def get_investigation_run(self, run_id: str) -> dict[str, object]:
        with self._get_connection() as conn:
            run_row = conn.execute(
                "SELECT id, candidate_id, status, current_round, created_at FROM reward_investigation_runs WHERE id = ?",
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
            created_at=_parse_dt(run_row["created_at"]) or datetime.now(UTC),
            actions=[
                RewardInvestigationAction(
                    id=row["id"],
                    run_id=row["run_id"],
                    action_type=row["action_type"],
                    target_url=row["target_url"],
                    status=row["status"],
                    payload=_json_loads(row["payload_json"], {}),
                    created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
                )
                for row in action_rows
            ],
        )
        return run.model_dump(mode="json")

    def create_evaluation_run(self, payload: dict[str, Any]) -> str:
        evaluation_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_evaluation_runs (
                    id, candidate_id, opportunity_id, ai_stage_2_label, ai_confidence,
                    ai_summary, ai_reasoning_brief, ai_missing_evidence, ai_risk_flags,
                    ai_structured_evidence, needs_investigation, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id,
                    payload.get("candidate_id"),
                    payload.get("opportunity_id"),
                    payload["ai_stage_2_label"],
                    payload["ai_confidence"],
                    payload.get("ai_summary"),
                    payload.get("ai_reasoning_brief"),
                    json.dumps(payload.get("ai_missing_evidence", []), ensure_ascii=False),
                    json.dumps(payload.get("ai_risk_flags", []), ensure_ascii=False),
                    json.dumps(payload.get("ai_structured_evidence", {}), ensure_ascii=False),
                    1 if payload.get("needs_investigation") else 0,
                    _now_iso(),
                ),
            )
        return evaluation_id

    def get_latest_evaluation_for_candidate(self, candidate_id: str) -> RewardEvaluationRun | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, candidate_id, opportunity_id, ai_stage_2_label, ai_confidence, ai_summary,
                       ai_reasoning_brief, ai_missing_evidence, ai_risk_flags, ai_structured_evidence,
                       needs_investigation, created_at
                FROM reward_evaluation_runs
                WHERE candidate_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (candidate_id,),
            ).fetchone()
        if row is None:
            return None
        return RewardEvaluationRun(
            id=row["id"],
            candidate_id=row["candidate_id"],
            opportunity_id=row["opportunity_id"],
            ai_stage_2_label=row["ai_stage_2_label"],
            ai_confidence=row["ai_confidence"],
            ai_summary=row["ai_summary"],
            ai_reasoning_brief=row["ai_reasoning_brief"],
            ai_missing_evidence=_json_loads(row["ai_missing_evidence"], []),
            ai_risk_flags=_json_loads(row["ai_risk_flags"], []),
            ai_structured_evidence=_json_loads(row["ai_structured_evidence"], {}),
            needs_investigation=bool(row["needs_investigation"]),
            created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
        )

    def create_agent_run(self, payload: dict[str, Any]) -> str:
        run_id = str(payload.get("id") or uuid.uuid4().hex)
        now = _now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_agent_runs (id, thread_id, status, metadata_json, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    payload["thread_id"],
                    payload.get("status", "running"),
                    json.dumps(payload.get("metadata", {}), ensure_ascii=False),
                    now,
                    now,
                    payload.get("completed_at"),
                ),
            )
        return run_id

    def update_agent_run(self, run_id: str, payload: dict[str, Any]) -> None:
        columns = {
            "status": payload.get("status"),
            "metadata_json": json.dumps(payload["metadata"], ensure_ascii=False) if "metadata" in payload else None,
            "completed_at": payload.get("completed_at") or (_now_iso() if payload.get("status") in {"completed", "failed"} else None),
            "updated_at": _now_iso(),
        }
        assignments = ", ".join(f"{key} = ?" for key, value in columns.items() if value is not None)
        values = [value for value in columns.values() if value is not None]
        if not assignments:
            return
        with self._get_connection() as conn:
            conn.execute(f"UPDATE reward_agent_runs SET {assignments} WHERE id = ?", (*values, run_id))

    def append_agent_step(self, run_id: str, payload: dict[str, Any]) -> str:
        step_id = str(payload.get("id") or uuid.uuid4().hex)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_agent_steps (
                    id, run_id, step_name, status, input_json, output_json,
                    latency_ms, failure_type, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_id,
                    run_id,
                    payload["step_name"],
                    payload.get("status", "completed"),
                    json.dumps(payload.get("input_payload", {}), ensure_ascii=False),
                    json.dumps(payload.get("output_payload", {}), ensure_ascii=False),
                    int(payload.get("latency_ms") or 0),
                    payload.get("failure_type"),
                    payload.get("error_message"),
                    _now_iso(),
                ),
            )
        return step_id

    def append_tool_call(self, run_id: str, payload: dict[str, Any]) -> str:
        call_id = str(payload.get("id") or uuid.uuid4().hex)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_tool_calls (
                    id, run_id, tool_name, status, input_json, output_json,
                    latency_ms, failure_type, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    run_id,
                    payload["tool_name"],
                    payload.get("status", "completed"),
                    json.dumps(payload.get("input_payload", {}), ensure_ascii=False),
                    json.dumps(payload.get("output_payload", {}), ensure_ascii=False),
                    int(payload.get("latency_ms") or 0),
                    payload.get("failure_type"),
                    payload.get("error_message"),
                    _now_iso(),
                ),
            )
        return call_id

    def append_evaluator_snapshot(self, run_id: str, payload: dict[str, Any]) -> str:
        snapshot_id = uuid.uuid4().hex
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reward_evaluator_snapshots (id, run_id, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (snapshot_id, run_id, json.dumps(payload, ensure_ascii=False), _now_iso()),
            )
        return snapshot_id

    def get_agent_run(self, run_id: str) -> dict[str, Any]:
        with self._get_connection() as conn:
            run = conn.execute(
                """
                SELECT id, thread_id, status, metadata_json, created_at, updated_at, completed_at
                FROM reward_agent_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            steps = conn.execute(
                """
                SELECT id, step_name, status, input_json, output_json, latency_ms,
                       failure_type, error_message, created_at
                FROM reward_agent_steps
                WHERE run_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (run_id,),
            ).fetchall()
            tool_calls = conn.execute(
                """
                SELECT id, tool_name, status, input_json, output_json, latency_ms,
                       failure_type, error_message, created_at
                FROM reward_tool_calls
                WHERE run_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (run_id,),
            ).fetchall()
            snapshots = conn.execute(
                """
                SELECT id, payload_json, created_at
                FROM reward_evaluator_snapshots
                WHERE run_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (run_id,),
            ).fetchall()
        if run is None:
            raise KeyError(f"Agent run not found: {run_id}")
        return {
            "id": run["id"],
            "thread_id": run["thread_id"],
            "status": run["status"],
            "metadata": _json_loads(run["metadata_json"], {}),
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "completed_at": run["completed_at"],
            "steps": [
                {
                    "id": row["id"],
                    "step_name": row["step_name"],
                    "status": row["status"],
                    "input_payload": _json_loads(row["input_json"], {}),
                    "output_payload": _json_loads(row["output_json"], {}),
                    "latency_ms": row["latency_ms"],
                    "failure_type": row["failure_type"],
                    "error_message": row["error_message"],
                    "created_at": row["created_at"],
                }
                for row in steps
            ],
            "tool_calls": [
                {
                    "id": row["id"],
                    "tool_name": row["tool_name"],
                    "status": row["status"],
                    "input_payload": _json_loads(row["input_json"], {}),
                    "output_payload": _json_loads(row["output_json"], {}),
                    "latency_ms": row["latency_ms"],
                    "failure_type": row["failure_type"],
                    "error_message": row["error_message"],
                    "created_at": row["created_at"],
                }
                for row in tool_calls
            ],
            "evaluator_snapshots": [
                {
                    "id": row["id"],
                    "payload": _json_loads(row["payload_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in snapshots
            ],
        }

    def upsert_opportunity(self, payload: dict[str, Any]) -> str:
        opportunity_id = str(payload.get("id") or uuid.uuid4().hex)
        created_at = payload.get("created_at") or _now_iso()
        with self._get_connection() as conn:
            existing = conn.execute("SELECT id, created_at FROM reward_opportunities WHERE id = ?", (opportunity_id,)).fetchone()
            if existing:
                created_at = existing["created_at"]
            conn.execute(
                """
                INSERT INTO reward_opportunities (
                    id, title, normalized_title, source_platform, source_type, source_url, canonical_url,
                    published_at, discovered_at, content_language, raw_text_excerpt, opportunity_type,
                    reward_type, reward_value_text, action_required, eligibility, deadline_text, deadline_at,
                    region_limit, platform_limit, ai_stage_1_recall_reason, ai_stage_2_label, ai_confidence,
                    ai_summary, ai_reasoning_brief, ai_missing_evidence, ai_risk_flags, ai_structured_evidence,
                    status, dedupe_key, content_hash, last_evaluated_at, recheck_after, external_links_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    normalized_title=excluded.normalized_title,
                    source_platform=excluded.source_platform,
                    source_type=excluded.source_type,
                    source_url=excluded.source_url,
                    canonical_url=excluded.canonical_url,
                    published_at=excluded.published_at,
                    discovered_at=excluded.discovered_at,
                    content_language=excluded.content_language,
                    raw_text_excerpt=excluded.raw_text_excerpt,
                    opportunity_type=excluded.opportunity_type,
                    reward_type=excluded.reward_type,
                    reward_value_text=excluded.reward_value_text,
                    action_required=excluded.action_required,
                    eligibility=excluded.eligibility,
                    deadline_text=excluded.deadline_text,
                    deadline_at=excluded.deadline_at,
                    region_limit=excluded.region_limit,
                    platform_limit=excluded.platform_limit,
                    ai_stage_1_recall_reason=excluded.ai_stage_1_recall_reason,
                    ai_stage_2_label=excluded.ai_stage_2_label,
                    ai_confidence=excluded.ai_confidence,
                    ai_summary=excluded.ai_summary,
                    ai_reasoning_brief=excluded.ai_reasoning_brief,
                    ai_missing_evidence=excluded.ai_missing_evidence,
                    ai_risk_flags=excluded.ai_risk_flags,
                    ai_structured_evidence=excluded.ai_structured_evidence,
                    status=excluded.status,
                    dedupe_key=excluded.dedupe_key,
                    content_hash=excluded.content_hash,
                    last_evaluated_at=excluded.last_evaluated_at,
                    recheck_after=excluded.recheck_after,
                    external_links_json=excluded.external_links_json
                """,
                (
                    opportunity_id,
                    payload["title"],
                    payload.get("normalized_title"),
                    payload["source_platform"],
                    payload.get("source_type"),
                    payload["source_url"],
                    payload.get("canonical_url"),
                    payload.get("published_at"),
                    payload.get("discovered_at"),
                    payload.get("content_language"),
                    payload.get("raw_text_excerpt"),
                    payload.get("opportunity_type"),
                    payload.get("reward_type"),
                    payload.get("reward_value_text"),
                    payload.get("action_required"),
                    payload.get("eligibility"),
                    payload.get("deadline_text"),
                    payload.get("deadline_at"),
                    payload.get("region_limit"),
                    payload.get("platform_limit"),
                    payload.get("ai_stage_1_recall_reason"),
                    payload["ai_stage_2_label"],
                    payload["ai_confidence"],
                    payload.get("ai_summary"),
                    payload.get("ai_reasoning_brief"),
                    json.dumps(payload.get("ai_missing_evidence", []), ensure_ascii=False),
                    json.dumps(payload.get("ai_risk_flags", []), ensure_ascii=False),
                    json.dumps(payload.get("ai_structured_evidence", {}), ensure_ascii=False),
                    payload.get("status", "active"),
                    payload.get("dedupe_key"),
                    payload.get("content_hash"),
                    payload.get("last_evaluated_at"),
                    payload.get("recheck_after"),
                    json.dumps(payload.get("external_links", []), ensure_ascii=False),
                    created_at,
                ),
            )
        return opportunity_id

    def find_opportunity_by_keys(
        self,
        *,
        canonical_url: str | None,
        dedupe_key: str | None,
        title: str,
        source_platform: str,
    ) -> RewardOpportunity | None:
        clauses: list[str] = []
        params: list[Any] = []
        if canonical_url:
            clauses.append("canonical_url = ?")
            params.append(canonical_url)
        if dedupe_key:
            clauses.append("dedupe_key = ?")
            params.append(dedupe_key)
        clauses.append("(title = ? AND source_platform = ?)")
        params.extend([title, source_platform])
        with self._get_connection() as conn:
            row = conn.execute(
                f"""
                SELECT * FROM reward_opportunities
                WHERE {' OR '.join(clauses)}
                ORDER BY created_at ASC
                LIMIT 1
                """,
                tuple(params),
            ).fetchone()
        if row is None:
            return None
        return self.get_opportunity(row["id"])

    def replace_opportunity_evidence(self, opportunity_id: str, evidence_items: list[dict[str, Any]]) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM reward_opportunity_evidence WHERE opportunity_id = ?", (opportunity_id,))
            for item in evidence_items:
                conn.execute(
                    """
                    INSERT INTO reward_opportunity_evidence (
                        id, opportunity_id, evidence_type, snippet, source_url, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex,
                        opportunity_id,
                        item["evidence_type"],
                        item["snippet"],
                        item["source_url"],
                        json.dumps(item.get("metadata", {}), ensure_ascii=False),
                        _now_iso(),
                    ),
                )

    def list_opportunities(
        self,
        *,
        classification: str | None = None,
        source_platform: str | None = None,
        opportunity_type: str | None = None,
        reward_type: str | None = None,
        evidence_status: str | None = None,
        sort_by: str = "created_at",
    ) -> list[RewardOpportunity]:
        clauses: list[str] = []
        params: list[Any] = []
        if classification:
            clauses.append("ai_stage_2_label = ?")
            params.append(classification)
        if source_platform:
            clauses.append("source_platform = ?")
            params.append(source_platform)
        if opportunity_type:
            clauses.append("opportunity_type = ?")
            params.append(opportunity_type)
        if reward_type:
            clauses.append("reward_type = ?")
            params.append(reward_type)
        if evidence_status == "complete":
            clauses.append("json_array_length(ai_missing_evidence) = 0")
        elif evidence_status == "missing":
            clauses.append("json_array_length(ai_missing_evidence) > 0")

        sort_column = {
            "created_at": "created_at",
            "published_at": "published_at",
            "last_evaluated_at": "last_evaluated_at",
        }.get(sort_by, "created_at")
        sql = "SELECT * FROM reward_opportunities"
        if clauses:
            sql += f" WHERE {' AND '.join(clauses)}"
        sql += f" ORDER BY {sort_column} DESC, id DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._hydrate_opportunity(row) for row in rows]

    def get_opportunity(self, opportunity_id: str) -> RewardOpportunity | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM reward_opportunities WHERE id = ?", (opportunity_id,)).fetchone()
        if row is None:
            return None
        return self._hydrate_opportunity(row)

    def _hydrate_opportunity(self, row: sqlite3.Row) -> RewardOpportunity:
        with self._get_connection() as conn:
            evidence_rows = conn.execute(
                """
                SELECT id, opportunity_id, evidence_type, snippet, source_url, metadata_json, created_at
                FROM reward_opportunity_evidence
                WHERE opportunity_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (row["id"],),
            ).fetchall()
        return RewardOpportunity(
            id=row["id"],
            title=row["title"],
            normalized_title=row["normalized_title"],
            source_platform=row["source_platform"],
            source_type=row["source_type"],
            source_url=row["source_url"],
            canonical_url=row["canonical_url"],
            published_at=_parse_dt(row["published_at"]),
            discovered_at=_parse_dt(row["discovered_at"]),
            content_language=row["content_language"],
            raw_text_excerpt=row["raw_text_excerpt"],
            opportunity_type=row["opportunity_type"],
            reward_type=row["reward_type"],
            reward_value_text=row["reward_value_text"],
            action_required=row["action_required"],
            eligibility=row["eligibility"],
            deadline_text=row["deadline_text"],
            deadline_at=_parse_dt(row["deadline_at"]),
            region_limit=row["region_limit"],
            platform_limit=row["platform_limit"],
            ai_stage_1_recall_reason=row["ai_stage_1_recall_reason"],
            ai_stage_2_label=row["ai_stage_2_label"],
            ai_confidence=row["ai_confidence"],
            ai_summary=row["ai_summary"],
            ai_reasoning_brief=row["ai_reasoning_brief"],
            ai_missing_evidence=_json_loads(row["ai_missing_evidence"], []),
            ai_risk_flags=_json_loads(row["ai_risk_flags"], []),
            ai_structured_evidence=_json_loads(row["ai_structured_evidence"], {}),
            status=row["status"],
            dedupe_key=row["dedupe_key"],
            content_hash=row["content_hash"],
            last_evaluated_at=_parse_dt(row["last_evaluated_at"]),
            recheck_after=_parse_dt(row["recheck_after"]),
            external_links=_json_loads(row["external_links_json"], []),
            evidence=[
                RewardOpportunityEvidence(
                    id=evidence_row["id"],
                    opportunity_id=evidence_row["opportunity_id"],
                    evidence_type=evidence_row["evidence_type"],
                    snippet=evidence_row["snippet"],
                    source_url=evidence_row["source_url"],
                    metadata=_json_loads(evidence_row["metadata_json"], {}),
                    created_at=_parse_dt(evidence_row["created_at"]) or datetime.now(UTC),
                )
                for evidence_row in evidence_rows
            ],
            created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
        )

    def get_overview_stats(self) -> dict[str, Any]:
        today_prefix = datetime.now(UTC).date().isoformat()
        with self._get_connection() as conn:
            source_count = conn.execute("SELECT COUNT(*) AS count FROM reward_source_feeds").fetchone()["count"]
            opportunity_count = conn.execute("SELECT COUNT(*) AS count FROM reward_opportunities").fetchone()["count"]
            candidate_count = conn.execute("SELECT COUNT(*) AS count FROM reward_recall_candidates").fetchone()["count"]
            high_value_count = conn.execute(
                "SELECT COUNT(*) AS count FROM reward_opportunities WHERE ai_stage_2_label = ?",
                ("高价值",),
            ).fetchone()["count"]
            today_crawled_count = conn.execute(
                "SELECT COUNT(*) AS count FROM reward_raw_documents WHERE created_at LIKE ?",
                (f"{today_prefix}%",),
            ).fetchone()["count"]
            today_candidate_count = conn.execute(
                "SELECT COUNT(*) AS count FROM reward_recall_candidates WHERE created_at LIKE ?",
                (f"{today_prefix}%",),
            ).fetchone()["count"]
            today_deep_screened_count = conn.execute(
                """
                SELECT COUNT(*) AS count FROM reward_evaluation_runs
                WHERE created_at LIKE ? AND ai_stage_2_label IN ('高价值', '可跟')
                """,
                (f"{today_prefix}%",),
            ).fetchone()["count"]
            distribution_rows = conn.execute(
                """
                SELECT ai_stage_2_label, COUNT(*) AS count
                FROM reward_opportunities
                GROUP BY ai_stage_2_label
                ORDER BY ai_stage_2_label ASC
                """
            ).fetchall()
            recent_high_value_rows = conn.execute(
                """
                SELECT id, title, source_platform, source_url, ai_stage_2_label, ai_confidence, created_at
                FROM reward_opportunities
                WHERE ai_stage_2_label = '高价值'
                ORDER BY created_at DESC, id DESC
                LIMIT 5
                """
            ).fetchall()
            source_health_rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM reward_source_feeds
                GROUP BY status
                ORDER BY status ASC
                """
            ).fetchall()
            failed_job_rows = conn.execute(
                """
                SELECT id, source_feed_id, status, mode, target_url, document_count, candidate_count,
                       opportunity_count, error_message, created_at, completed_at
                FROM reward_crawl_jobs
                WHERE status = 'failed'
                ORDER BY created_at DESC, id DESC
                LIMIT 5
                """
            ).fetchall()
        return {
            "source_count": int(source_count),
            "opportunity_count": int(opportunity_count),
            "candidate_count": int(candidate_count),
            "high_value_count": int(high_value_count),
            "today_crawled_count": int(today_crawled_count),
            "today_candidate_count": int(today_candidate_count),
            "today_deep_screened_count": int(today_deep_screened_count),
            "classification_distribution": {row["ai_stage_2_label"]: int(row["count"]) for row in distribution_rows},
            "recent_high_value": [dict(row) for row in recent_high_value_rows],
            "source_health": {row["status"]: int(row["count"]) for row in source_health_rows},
            "recent_failed_jobs": [dict(row) for row in failed_job_rows],
        }

    def get_operations_snapshot(self) -> dict[str, Any]:
        sources = [source.model_dump(mode="json") for source in self.list_source_feeds()]
        jobs = [job.model_dump(mode="json") for job in self.list_recent_crawl_jobs(limit=20)]
        return {
            "sources": sources,
            "recent_jobs": jobs,
            "failed_jobs": [job for job in jobs if job.get("status") == "failed"][:5],
        }

    def list_raw_documents_for_urls(self, urls: list[str], limit: int = 20) -> list[RewardRawDocument]:
        if not urls:
            return []
        placeholders = ", ".join("?" for _ in urls)
        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, crawl_job_id, source_feed_id, source_platform, source_type, source_url,
                       canonical_url, title, body, summary, published_at, metadata_json, created_at
                FROM reward_raw_documents
                WHERE source_url IN ({placeholders}) OR canonical_url IN ({placeholders})
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                tuple(urls + urls + [limit]),
            ).fetchall()
        return [
            RewardRawDocument(
                id=row["id"],
                crawl_job_id=row["crawl_job_id"],
                source_feed_id=row["source_feed_id"],
                source_platform=row["source_platform"],
                source_type=row["source_type"],
                source_url=row["source_url"],
                canonical_url=row["canonical_url"],
                title=row["title"],
                body=row["body"],
                summary=row["summary"],
                published_at=_parse_dt(row["published_at"]),
                metadata=_json_loads(row["metadata_json"], {}),
                created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
            )
            for row in rows
        ]
