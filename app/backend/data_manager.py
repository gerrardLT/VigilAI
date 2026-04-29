"""
SQLite-backed data manager for VigilAI.
"""

from __future__ import annotations

from agent_platform.repository import ensure_agent_platform_tables
from analysis.template_defaults import apply_template_compat_defaults, get_default_analysis_templates
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
import hashlib
import json
import logging
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH, PRIORITY_INTERVALS, SOURCES_CONFIG
from models import SourceStatus
from product_selection.repository import ensure_product_selection_tables
from data_manager_components import (
    DataManagerActivityMixin,
    DataManagerAnalysisMixin,
    DataManagerWorkspaceMixin,
)

logger = logging.getLogger(__name__)


class DataManager(DataManagerActivityMixin, DataManagerAnalysisMixin, DataManagerWorkspaceMixin):
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self._ensure_data_dir()
        self._init_db()
        self._init_sources()
        self._init_analysis_templates()

    def _ensure_data_dir(self) -> None:
        data_dir = os.path.dirname(self.db_path)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)

    @contextmanager
    def _get_connection(self):
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

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    full_content TEXT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    prize_amount REAL,
                    prize_currency TEXT,
                    prize_description TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    deadline TEXT,
                    location TEXT,
                    organizer TEXT,
                    image_url TEXT,
                    summary TEXT,
                    score REAL,
                    score_reason TEXT,
                    deadline_level TEXT,
                    trust_level TEXT,
                    updated_fields TEXT,
                    status TEXT DEFAULT 'upcoming',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, url)
                )
                """
            )
            self._ensure_columns(
                conn,
                "activities",
                {
                    "image_url": "TEXT",
                    "full_content": "TEXT",
                    "summary": "TEXT",
                    "score": "REAL",
                    "score_reason": "TEXT",
                    "deadline_level": "TEXT",
                    "trust_level": "TEXT",
                    "updated_fields": "TEXT",
                    "analysis_fields": "TEXT",
                    "analysis_status": "TEXT",
                    "analysis_failed_layer": "TEXT",
                    "analysis_summary_reasons": "TEXT",
                    "analysis_summary": "TEXT",
                    "analysis_reasons": "TEXT",
                    "analysis_risk_flags": "TEXT",
                    "analysis_recommended_action": "TEXT",
                    "analysis_confidence": "REAL",
                    "analysis_structured": "TEXT",
                    "analysis_template_id": "TEXT",
                    "analysis_current_run_id": "TEXT",
                    "analysis_updated_at": "TEXT",
                },
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    update_interval INTEGER NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    last_success TEXT,
                    status TEXT DEFAULT 'idle',
                    error_message TEXT,
                    activity_count INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tracking_items (
                    activity_id TEXT PRIMARY KEY,
                    is_favorited INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'saved',
                    stage TEXT,
                    notes TEXT,
                    next_action TEXT,
                    remind_at TEXT,
                    block_reason TEXT,
                    abandon_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_columns(
                conn,
                "tracking_items",
                {
                    "stage": "TEXT",
                    "block_reason": "TEXT",
                    "abandon_reason": "TEXT",
                },
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS digests (
                    id TEXT PRIMARY KEY,
                    digest_date TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    summary TEXT,
                    content TEXT NOT NULL,
                    item_ids TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_sent_at TEXT,
                    send_channel TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS digest_candidates (
                    digest_date TEXT NOT NULL,
                    activity_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (digest_date, activity_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_default INTEGER DEFAULT 0,
                    tags TEXT NOT NULL,
                    layers TEXT NOT NULL,
                    sort_fields TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_columns(
                conn,
                "analysis_templates",
                {
                    "preference_profile": "TEXT",
                    "risk_tolerance": "TEXT",
                    "research_mode": "TEXT",
                    "compiled_policy": "TEXT",
                },
            )
            self._init_agent_analysis_tables(conn)
            ensure_agent_platform_tables(conn)
            ensure_product_selection_tables(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_source_id ON activities(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracking_status ON tracking_items(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_digests_digest_date ON digests(digest_date)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_digest_candidates_date ON digest_candidates(digest_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analysis_templates_default ON analysis_templates(is_default)"
            )

    def _ensure_columns(self, conn: sqlite3.Connection, table: str, columns: Dict[str, str]) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, column_type in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")

    def _init_agent_analysis_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_jobs (
                id TEXT PRIMARY KEY,
                trigger_type TEXT NOT NULL,
                scope_type TEXT NOT NULL,
                template_id TEXT,
                route_policy TEXT,
                budget_policy TEXT,
                status TEXT NOT NULL,
                requested_by TEXT,
                created_at TEXT NOT NULL,
                finished_at TEXT
            )
            """
        )
        self._ensure_columns(
            conn,
            "analysis_jobs",
            {
                "trigger_type": "TEXT",
                "scope_type": "TEXT",
                "template_id": "TEXT",
                "route_policy": "TEXT",
                "budget_policy": "TEXT",
                "status": "TEXT",
                "requested_by": "TEXT",
                "created_at": "TEXT",
                "finished_at": "TEXT",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_job_items (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                status TEXT NOT NULL,
                needs_research INTEGER DEFAULT 0,
                final_draft_status TEXT,
                screening_model TEXT,
                research_model TEXT,
                verdict_model TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._ensure_columns(
            conn,
            "analysis_job_items",
            {
                "job_id": "TEXT",
                "activity_id": "TEXT",
                "status": "TEXT",
                "needs_research": "INTEGER",
                "final_draft_status": "TEXT",
                "screening_model": "TEXT",
                "research_model": "TEXT",
                "verdict_model": "TEXT",
                "started_at": "TEXT",
                "finished_at": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_item_steps (
                id TEXT PRIMARY KEY,
                job_item_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                step_status TEXT NOT NULL,
                input_digest TEXT,
                output_payload TEXT,
                latency_ms INTEGER,
                cost_tokens_in INTEGER,
                cost_tokens_out INTEGER,
                model_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._ensure_columns(
            conn,
            "analysis_item_steps",
            {
                "job_item_id": "TEXT",
                "step_type": "TEXT",
                "step_status": "TEXT",
                "input_digest": "TEXT",
                "output_payload": "TEXT",
                "latency_ms": "INTEGER",
                "cost_tokens_in": "INTEGER",
                "cost_tokens_out": "INTEGER",
                "model_name": "TEXT",
                "created_at": "TEXT",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_evidence (
                id TEXT PRIMARY KEY,
                job_item_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                url TEXT,
                title TEXT,
                snippet TEXT,
                relevance_score REAL,
                trust_score REAL,
                supports_claim INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
        self._ensure_columns(
            conn,
            "analysis_evidence",
            {
                "job_item_id": "TEXT",
                "source_type": "TEXT",
                "url": "TEXT",
                "title": "TEXT",
                "snippet": "TEXT",
                "relevance_score": "REAL",
                "trust_score": "REAL",
                "supports_claim": "INTEGER",
                "created_at": "TEXT",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_reviews (
                id TEXT PRIMARY KEY,
                job_item_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                review_action TEXT NOT NULL,
                review_note TEXT,
                reviewed_by TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._ensure_columns(
            conn,
            "analysis_reviews",
            {
                "job_item_id": "TEXT",
                "activity_id": "TEXT",
                "review_action": "TEXT",
                "review_note": "TEXT",
                "reviewed_by": "TEXT",
                "created_at": "TEXT",
            },
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_job_items_job ON analysis_job_items(job_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_job_items_activity ON analysis_job_items(activity_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_item_steps_item ON analysis_item_steps(job_item_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_evidence_item ON analysis_evidence(job_item_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_reviews_item ON analysis_reviews(job_item_id)")

    def _init_sources(self) -> None:
        with self._get_connection() as conn:
            for source_id, config in SOURCES_CONFIG.items():
                row = conn.execute("SELECT id FROM sources WHERE id = ?", (source_id,)).fetchone()
                if row:
                    continue
                conn.execute(
                    """
                    INSERT INTO sources (id, name, type, url, priority, update_interval, enabled, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        config["name"],
                        config["type"],
                        config["url"],
                        config["priority"],
                        PRIORITY_INTERVALS.get(config["priority"], 7200),
                        1 if config.get("enabled", True) else 0,
                        SourceStatus.IDLE.value,
                    ),
                )

    def _init_analysis_templates(self) -> None:
        with self._get_connection() as conn:
            existing = conn.execute("SELECT COUNT(*) AS count FROM analysis_templates").fetchone()["count"]
            if existing:
                self._backfill_analysis_template_records(conn)
                return
            for template in get_default_analysis_templates():
                self._insert_analysis_template(conn, template)

    def _backfill_analysis_template_records(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT * FROM analysis_templates").fetchall()
        now = datetime.now().isoformat()
        for row in rows:
            template = {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
                "description": row["description"],
                "is_default": bool(row["is_default"]),
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "layers": json.loads(row["layers"]) if row["layers"] else [],
                "sort_fields": json.loads(row["sort_fields"]) if row["sort_fields"] else [],
                "preference_profile": row["preference_profile"] if "preference_profile" in row.keys() else None,
                "risk_tolerance": row["risk_tolerance"] if "risk_tolerance" in row.keys() else None,
                "research_mode": row["research_mode"] if "research_mode" in row.keys() else None,
            }
            normalized = apply_template_compat_defaults(template)
            stored_compiled_policy = row["compiled_policy"] if "compiled_policy" in row.keys() else None
            normalized_compiled_policy = json.dumps(normalized["compiled_policy"])

            if (
                template["preference_profile"] == normalized["preference_profile"]
                and template["risk_tolerance"] == normalized["risk_tolerance"]
                and template["research_mode"] == normalized["research_mode"]
                and template["layers"] == normalized["layers"]
                and template["sort_fields"] == normalized["sort_fields"]
                and stored_compiled_policy == normalized_compiled_policy
            ):
                continue

            conn.execute(
                """
                UPDATE analysis_templates
                SET tags = ?,
                    layers = ?,
                    sort_fields = ?,
                    preference_profile = ?,
                    risk_tolerance = ?,
                    research_mode = ?,
                    compiled_policy = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(normalized["tags"]),
                    json.dumps(normalized["layers"]),
                    json.dumps(normalized["sort_fields"]),
                    normalized["preference_profile"],
                    normalized["risk_tolerance"],
                    normalized["research_mode"],
                    normalized_compiled_policy,
                    now,
                    row["id"],
                ),
            )

