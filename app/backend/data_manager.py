"""
SQLite-backed data manager for VigilAI.
"""

from __future__ import annotations

from analysis.schemas import AnalysisSnapshot
from analysis.ai_enrichment import enrich_activity_for_analysis
from analysis.rule_engine import run_analysis
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

from config import DB_PATH, LOW_SIGNAL_FIRECRAWL_SOURCES, PRIORITY_INTERVALS, SOURCES_CONFIG
from models import (
    Activity,
    ActivityDates,
    AnalysisEvidence,
    AnalysisJob,
    AnalysisJobItem,
    AnalysisReview,
    AnalysisStep,
    DigestRecord,
    DigestStatus,
    Prize,
    Source,
    SourceStatus,
    StatsResponse,
    TimelineEvent,
    TrackingState,
    TrackingStatus,
)
from utils.content_cleaning import (
    build_description_from_text,
    clean_detail_content,
    looks_like_invalid_activity_candidate,
    looks_like_noisy_scraped_text,
)

logger = logging.getLogger(__name__)

TRACKING_STATUS_VALUES = {status.value for status in TrackingStatus}
ACTIVITY_SNAPSHOT_COLUMNS = (
    "analysis_status",
    "analysis_summary",
    "analysis_reasons",
    "analysis_risk_flags",
    "analysis_recommended_action",
    "analysis_confidence",
    "analysis_structured",
    "analysis_template_id",
    "analysis_current_run_id",
    "analysis_updated_at",
)


class DataManager:
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
                    notes TEXT,
                    next_action TEXT,
                    remind_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
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

    @staticmethod
    def generate_activity_id(source_id: str, url: str) -> str:
        return hashlib.md5(f"{source_id}:{url}".encode()).hexdigest()

    def _generate_record_id(self) -> str:
        return hashlib.md5(f"{datetime.now().isoformat()}:{os.urandom(8).hex()}".encode()).hexdigest()

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "analysis-template"

    def _unique_template_slug(self, conn: sqlite3.Connection, base_slug: str, exclude_id: str | None = None) -> str:
        candidate = base_slug
        suffix = 2
        while True:
            params: List[Any] = [candidate]
            query = "SELECT id FROM analysis_templates WHERE slug = ?"
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            existing = conn.execute(query, params).fetchone()
            if not existing:
                return candidate
            candidate = f"{base_slug}-{suffix}"
            suffix += 1

    def _insert_analysis_template(self, conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        payload = apply_template_compat_defaults(payload)
        template_id = payload.get("id") or self._generate_record_id()
        slug = self._unique_template_slug(conn, payload.get("slug") or self._slugify(payload["name"]))
        if payload.get("is_default"):
            conn.execute("UPDATE analysis_templates SET is_default = 0")
        conn.execute(
            """
            INSERT INTO analysis_templates (
                id, name, slug, description, is_default, tags, layers, sort_fields, preference_profile,
                risk_tolerance, research_mode, compiled_policy, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                payload["name"],
                slug,
                payload.get("description"),
                1 if payload.get("is_default") else 0,
                json.dumps(payload.get("tags") or []),
                json.dumps(payload.get("layers") or []),
                json.dumps(payload.get("sort_fields") or []),
                payload.get("preference_profile"),
                payload.get("risk_tolerance"),
                payload.get("research_mode"),
                json.dumps(payload.get("compiled_policy") or {}),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
        return self._analysis_template_from_row(row)

    def _analysis_template_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
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
            "compiled_policy": json.loads(row["compiled_policy"])
            if "compiled_policy" in row.keys() and row["compiled_policy"]
            else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        return apply_template_compat_defaults(template)

    def _default_analysis_template_for_conn(self, conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        row = conn.execute(
            """
            SELECT * FROM analysis_templates
            ORDER BY is_default DESC, created_at ASC
            LIMIT 1
            """
        ).fetchone()
        return self._analysis_template_from_row(row) if row else None

    def _source_snapshot(self, conn: sqlite3.Connection, source_id: str) -> Optional[sqlite3.Row]:
        return conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()

    def _is_firecrawl_source(self, source_id: str) -> bool:
        return SOURCES_CONFIG.get(source_id, {}).get("type") == "firecrawl"

    def _is_hidden_activity(
        self,
        *,
        source_id: str,
        title: str,
        url: str,
        description: str | None,
        full_content: str | None,
    ) -> bool:
        if source_id in LOW_SIGNAL_FIRECRAWL_SOURCES:
            return True
        if not self._is_firecrawl_source(source_id):
            return False
        return looks_like_invalid_activity_candidate(
            title,
            url,
            full_content or description,
            source_id=source_id,
        )

    def _is_hidden_activity_row(self, row: sqlite3.Row) -> bool:
        return self._is_hidden_activity(
            source_id=row["source_id"],
            title=row["title"],
            url=row["url"],
            description=row["description"],
            full_content=row["full_content"],
        )

    def _visible_activities_from_rows(self, rows: List[sqlite3.Row]) -> List[Activity]:
        activities: List[Activity] = []
        for row in rows:
            if self._is_hidden_activity_row(row):
                continue
            activities.append(self._row_to_activity(row))
        return activities

    def _clean_activity_texts(
        self,
        *,
        source_id: str,
        title: str,
        description: str | None,
        full_content: str | None,
        summary: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        if not self._is_firecrawl_source(source_id):
            return description, full_content, summary

        cleaned_full_content = clean_detail_content(full_content) if full_content else full_content

        cleaned_description = description
        if description and looks_like_noisy_scraped_text(description):
            cleaned_description = build_description_from_text(description, title=title, max_length=500) or description

        if cleaned_full_content and (not cleaned_description or looks_like_noisy_scraped_text(description or "")):
            cleaned_description = build_description_from_text(
                cleaned_full_content,
                title=title,
                max_length=500,
            ) or cleaned_description

        cleaned_summary = summary
        if not cleaned_summary or looks_like_noisy_scraped_text(cleaned_summary):
            cleaned_summary = build_description_from_text(
                cleaned_full_content or cleaned_description or title,
                title=title,
                max_length=220,
            ) or cleaned_summary

        return cleaned_description, cleaned_full_content, cleaned_summary

    def _build_summary(self, activity: Activity) -> str:
        if self._is_firecrawl_source(activity.source_id):
            if activity.description and not looks_like_noisy_scraped_text(activity.description):
                return activity.description.strip()[:220]
            source_text = activity.full_content or activity.description or activity.title
            cleaned = build_description_from_text(source_text, title=activity.title, max_length=220)
            return cleaned or activity.title[:220]

        source_text = activity.description or activity.full_content or activity.title
        return source_text.strip()[:220]

    def _deadline_level(self, activity: Activity) -> str:
        deadline = activity.dates.deadline if activity.dates else None
        if deadline is None:
            return "none"
        now = datetime.now()
        delta_days = (deadline - now).total_seconds() / 86400
        if delta_days < 0:
            return "expired"
        if delta_days <= 3:
            return "urgent"
        if delta_days <= 7:
            return "soon"
        if delta_days <= 30:
            return "upcoming"
        return "later"

    def _trust_level(self, source_row: sqlite3.Row | None) -> str:
        if source_row is None:
            return "low"
        status = source_row["status"]
        if status == SourceStatus.ERROR.value:
            return "low"
        if status == SourceStatus.RUNNING.value:
            return "medium"
        last_success = source_row["last_success"]
        if not last_success:
            return "low"
        delta = datetime.now() - datetime.fromisoformat(last_success)
        if delta <= timedelta(days=3):
            return "high"
        if delta <= timedelta(days=7):
            return "medium"
        return "low"

    def _score_components(self, activity: Activity, trust_level: str, deadline_level: str) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        age_days = (datetime.now() - activity.created_at).total_seconds() / 86400
        if age_days <= 1:
            score += 30
            reasons.append("recent")
        elif age_days <= 7:
            score += 20
            reasons.append("fresh")
        else:
            score += 10
        if deadline_level == "urgent":
            score += 30
            reasons.append("urgent deadline")
        elif deadline_level == "soon":
            score += 20
            reasons.append("near deadline")
        elif deadline_level == "upcoming":
            score += 10
        if activity.prize and activity.prize.amount:
            score += 20 if activity.prize.amount >= 5000 else 10
            reasons.append("prize available")
        trust_bonus = {"high": 20, "medium": 10, "low": 0}[trust_level]
        score += trust_bonus
        if trust_bonus:
            reasons.append(f"{trust_level} trust")
        return min(score, 100.0), reasons

    def _to_iso(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    def _normalize_digest_date(self, digest_date: str | None = None) -> str:
        return digest_date or date.today().isoformat()

    def _updated_fields(self, existing: sqlite3.Row | None, activity: Activity) -> List[str]:
        if existing is None:
            return []
        fields: List[str] = []
        checks = {
            "title": activity.title,
            "description": activity.description,
            "full_content": activity.full_content,
            "category": activity.category.value,
            "location": activity.location,
            "organizer": activity.organizer,
            "image_url": activity.image_url,
            "status": activity.status,
        }
        for field, new_value in checks.items():
            if existing[field] != new_value:
                fields.append(field)
        if (existing["tags"] or "[]") != json.dumps(activity.tags or []):
            fields.append("tags")
        if (existing["deadline"] or None) != self._to_iso(activity.dates.deadline if activity.dates else None):
            fields.append("deadline")
        if (existing["prize_amount"] or None) != (activity.prize.amount if activity.prize else None):
            fields.append("prize")
        return fields

    def _analysis_result_for_activity(
        self,
        activity: Activity,
        source_row: sqlite3.Row | None,
        conn: sqlite3.Connection,
        template: Dict[str, Any] | None = None,
    ) -> Tuple[Dict[str, Any], Any]:
        analysis_fields = enrich_activity_for_analysis(
            {
                "title": activity.title,
                "description": activity.description or activity.full_content,
                "category": activity.category.value,
                "prize_amount": activity.prize.amount if activity.prize else None,
            }
        )
        trust_level = self._trust_level(source_row)
        analysis_fields["source_trust"] = trust_level
        analysis_fields["trust_score"] = {"high": 85, "medium": 65, "low": 40}[trust_level]

        template = template or self._default_analysis_template_for_conn(conn) or {"layers": []}
        result = run_analysis(
            activity=activity.model_dump(mode="json"),
            template=template,
            analysis_fields=analysis_fields,
        )
        return analysis_fields, result

    def _pack_activity_snapshot_fields(self, snapshot: AnalysisSnapshot | None) -> Dict[str, Any]:
        if snapshot is None:
            return {column: None for column in ACTIVITY_SNAPSHOT_COLUMNS}
        return {
            "analysis_status": snapshot.status,
            "analysis_summary": snapshot.summary,
            "analysis_reasons": json.dumps(snapshot.reasons),
            "analysis_risk_flags": json.dumps(snapshot.risk_flags),
            "analysis_recommended_action": snapshot.recommended_action,
            "analysis_confidence": snapshot.confidence,
            "analysis_structured": json.dumps(snapshot.structured),
            "analysis_template_id": snapshot.template_id,
            "analysis_current_run_id": snapshot.current_run_id,
            "analysis_updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
        }

    def _unpack_activity_snapshot_fields(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "analysis_status": row["analysis_status"] if "analysis_status" in row.keys() else None,
            "analysis_summary": row["analysis_summary"] if "analysis_summary" in row.keys() else None,
            "analysis_reasons": json.loads(row["analysis_reasons"])
            if "analysis_reasons" in row.keys() and row["analysis_reasons"]
            else [],
            "analysis_risk_flags": json.loads(row["analysis_risk_flags"])
            if "analysis_risk_flags" in row.keys() and row["analysis_risk_flags"]
            else [],
            "analysis_recommended_action": row["analysis_recommended_action"]
            if "analysis_recommended_action" in row.keys()
            else None,
            "analysis_confidence": row["analysis_confidence"] if "analysis_confidence" in row.keys() else None,
            "analysis_structured": json.loads(row["analysis_structured"])
            if "analysis_structured" in row.keys() and row["analysis_structured"]
            else {},
            "analysis_template_id": row["analysis_template_id"] if "analysis_template_id" in row.keys() else None,
            "analysis_current_run_id": row["analysis_current_run_id"]
            if "analysis_current_run_id" in row.keys()
            else None,
            "analysis_updated_at": datetime.fromisoformat(row["analysis_updated_at"])
            if "analysis_updated_at" in row.keys() and row["analysis_updated_at"]
            else None,
        }

    def _activity_enrichment(
        self,
        activity: Activity,
        source_row: sqlite3.Row | None,
        conn: sqlite3.Connection,
    ) -> Tuple[
        str,
        float,
        Optional[str],
        str,
        str,
        Dict[str, Any],
        str,
        Optional[str],
        List[str],
    ]:
        summary = self._build_summary(activity)
        deadline_level = self._deadline_level(activity)
        trust_level = self._trust_level(source_row)
        score, reasons = self._score_components(activity, trust_level, deadline_level)
        analysis_fields, analysis_result = self._analysis_result_for_activity(activity, source_row, conn)
        return (
            summary,
            score,
            ", ".join(reasons) if reasons else None,
            deadline_level,
            trust_level,
            analysis_fields,
            analysis_result.status,
            analysis_result.failed_layer,
            analysis_result.folded_summary_reasons,
        )

    def _refresh_source_activity_signals(self, conn: sqlite3.Connection, source_id: str) -> None:
        source_row = self._source_snapshot(conn, source_id)
        activity_rows = conn.execute(
            """
            SELECT a.*,
                0 AS is_tracking,
                0 AS is_favorited
            FROM activities a
            WHERE a.source_id = ?
            """,
            (source_id,),
        ).fetchall()
        for row in activity_rows:
            if self._is_hidden_activity_row(row):
                continue
            activity = self._row_to_activity(row)
            (
                summary,
                score,
                score_reason,
                deadline_level,
                trust_level,
                analysis_fields,
                analysis_status,
                analysis_failed_layer,
                analysis_summary_reasons,
            ) = self._activity_enrichment(
                activity,
                source_row,
                conn,
            )
            conn.execute(
                """
                UPDATE activities
                SET summary = ?,
                    score = ?,
                    score_reason = ?,
                    deadline_level = ?,
                    trust_level = ?,
                    analysis_fields = ?,
                    analysis_status = ?,
                    analysis_failed_layer = ?,
                    analysis_summary_reasons = ?
                WHERE id = ?
                """,
                (
                    summary,
                    score,
                    score_reason,
                    deadline_level,
                    trust_level,
                    json.dumps(analysis_fields),
                    analysis_status,
                    analysis_failed_layer,
                    json.dumps(analysis_summary_reasons),
                    activity.id,
                ),
            )

    def _refresh_all_activity_analysis(self, conn: sqlite3.Connection) -> None:
        activity_rows = conn.execute(
            """
            SELECT a.*,
                0 AS is_tracking,
                0 AS is_favorited
            FROM activities a
            ORDER BY a.created_at DESC
            """
        ).fetchall()
        for row in activity_rows:
            if self._is_hidden_activity_row(row):
                continue
            activity = self._row_to_activity(row)
            source_row = self._source_snapshot(conn, activity.source_id)
            analysis_fields, analysis_result = self._analysis_result_for_activity(activity, source_row, conn)
            conn.execute(
                """
                UPDATE activities
                SET analysis_fields = ?,
                    analysis_status = ?,
                    analysis_failed_layer = ?,
                    analysis_summary_reasons = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(analysis_fields),
                    analysis_result.status,
                    analysis_result.failed_layer,
                    json.dumps(analysis_result.folded_summary_reasons),
                    datetime.now().isoformat(),
                    activity.id,
                ),
            )

    def rerun_analysis_for_all_activities(self) -> int:
        with self._get_connection() as conn:
            self._refresh_all_activity_analysis(conn)
            row = conn.execute("SELECT COUNT(*) AS count FROM activities").fetchone()
            return int(row["count"]) if row else 0

    def _preview_analysis_template_counts(
        self,
        conn: sqlite3.Connection,
        *,
        template: Dict[str, Any],
        template_id: str,
    ) -> Dict[str, Any]:
        activity_rows = conn.execute(
            """
            SELECT a.*,
                0 AS is_tracking,
                0 AS is_favorited
            FROM activities a
            ORDER BY a.created_at DESC
            """
        ).fetchall()

        counts = {"passed": 0, "watch": 0, "rejected": 0}
        total = 0
        for activity_row in activity_rows:
            if self._is_hidden_activity_row(activity_row):
                continue
            total += 1
            activity = self._row_to_activity(activity_row)
            source_row = self._source_snapshot(conn, activity.source_id)
            _, analysis_result = self._analysis_result_for_activity(
                activity,
                source_row,
                conn,
                template=template,
            )
            if analysis_result.status in counts:
                counts[analysis_result.status] += 1

        return {
            "template_id": template_id,
            "total": total,
            "passed": counts["passed"],
            "watch": counts["watch"],
            "rejected": counts["rejected"],
        }

    def preview_analysis_template(self, template_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis template {template_id} not found")

            template = self._analysis_template_from_row(row)
            return self._preview_analysis_template_counts(conn, template=template, template_id=template_id)

    def preview_analysis_template_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_connection() as conn:
            template_id = payload.get("id") or "draft"
            template = apply_template_compat_defaults(
                {
                    "id": template_id,
                    "name": payload.get("name") or "Draft template",
                    "slug": payload.get("slug") or "draft-template",
                    "description": payload.get("description"),
                    "is_default": False,
                    "tags": payload.get("tags") or [],
                    "layers": payload.get("layers") or [],
                    "sort_fields": payload.get("sort_fields") or [],
                    "preference_profile": payload.get("preference_profile"),
                    "risk_tolerance": payload.get("risk_tolerance"),
                    "research_mode": payload.get("research_mode"),
                }
            )
            return self._preview_analysis_template_counts(conn, template=template, template_id=template_id)

    def preview_analysis_template_payload_results(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_connection() as conn:
            template_id = payload.get("id") or "draft"
            template = apply_template_compat_defaults(
                {
                    "id": template_id,
                    "name": payload.get("name") or "Draft template",
                    "slug": payload.get("slug") or "draft-template",
                    "description": payload.get("description"),
                    "is_default": False,
                    "tags": payload.get("tags") or [],
                    "layers": payload.get("layers") or [],
                    "sort_fields": payload.get("sort_fields") or [],
                    "preference_profile": payload.get("preference_profile"),
                    "risk_tolerance": payload.get("risk_tolerance"),
                    "research_mode": payload.get("research_mode"),
                }
            )
            requested_ids = [item for item in (payload.get("activity_ids") or []) if item]
            if requested_ids:
                placeholders = ", ".join("?" for _ in requested_ids)
                rows = conn.execute(
                    f"""
                    SELECT a.*,
                        0 AS is_tracking,
                        0 AS is_favorited,
                        0 AS is_digest_candidate
                    FROM activities a
                    WHERE a.id IN ({placeholders})
                    """,
                    requested_ids,
                ).fetchall()
                visible_activities = self._visible_activities_from_rows(rows)
                activity_by_id = {activity.id: activity for activity in visible_activities}
                activities = [activity_by_id[item_id] for item_id in requested_ids if item_id in activity_by_id]
            else:
                rows = conn.execute(
                    """
                    SELECT a.*,
                        0 AS is_tracking,
                        0 AS is_favorited,
                        0 AS is_digest_candidate
                    FROM activities a
                    ORDER BY a.created_at DESC
                    """
                ).fetchall()
                activities = self._visible_activities_from_rows(rows)

            counts = {"passed": 0, "watch": 0, "rejected": 0}
            items: List[Dict[str, Any]] = []

            for activity in activities:
                source_row = self._source_snapshot(conn, activity.source_id)
                _, analysis_result = self._analysis_result_for_activity(
                    activity,
                    source_row,
                    conn,
                    template=template,
                )
                if analysis_result.status in counts:
                    counts[analysis_result.status] += 1
                items.append(
                    {
                        "activity_id": activity.id,
                        "status": analysis_result.status,
                        "failed_layer": analysis_result.failed_layer,
                        "summary_reasons": analysis_result.folded_summary_reasons,
                        "layer_results": [
                            layer.model_dump(mode="json") if hasattr(layer, "model_dump") else layer
                            for layer in analysis_result.layer_results
                        ],
                    }
                )

            return {
                "template_id": template_id,
                "total": len(activities),
                "passed": counts["passed"],
                "watch": counts["watch"],
                "rejected": counts["rejected"],
                "items": items,
            }

    def add_activity(self, activity: Activity) -> bool:
        if self._is_hidden_activity(
            source_id=activity.source_id,
            title=activity.title,
            url=activity.url,
            description=activity.description,
            full_content=activity.full_content,
        ):
            logger.info("Skipping low-signal firecrawl activity from %s: %s", activity.source_id, activity.title)
            return False
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM activities WHERE source_id = ? AND url = ?",
                (activity.source_id, activity.url),
            ).fetchone()
            is_new = existing is None
            source_row = self._source_snapshot(conn, activity.source_id)
            (
                summary,
                score,
                score_reason,
                deadline_level,
                trust_level,
                analysis_fields,
                analysis_status,
                analysis_failed_layer,
                analysis_summary_reasons,
            ) = self._activity_enrichment(
                activity,
                source_row,
                conn,
            )
            updated_fields = self._updated_fields(existing, activity)
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO activities (
                    id, title, description, full_content, source_id, source_name, url, category, tags,
                    prize_amount, prize_currency, prize_description,
                    start_date, end_date, deadline, location, organizer, image_url,
                    summary, score, score_reason, deadline_level, trust_level, updated_fields,
                    analysis_fields, analysis_status, analysis_failed_layer, analysis_summary_reasons,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity.id,
                    activity.title,
                    activity.description,
                    activity.full_content,
                    activity.source_id,
                    activity.source_name,
                    activity.url,
                    activity.category.value,
                    json.dumps(activity.tags or []),
                    activity.prize.amount if activity.prize else None,
                    activity.prize.currency if activity.prize else None,
                    activity.prize.description if activity.prize else None,
                    self._to_iso(activity.dates.start_date if activity.dates else None),
                    self._to_iso(activity.dates.end_date if activity.dates else None),
                    self._to_iso(activity.dates.deadline if activity.dates else None),
                    activity.location,
                    activity.organizer,
                    activity.image_url,
                    summary,
                    score,
                    score_reason,
                    deadline_level,
                    trust_level,
                    json.dumps(updated_fields),
                    json.dumps(analysis_fields),
                    analysis_status,
                    analysis_failed_layer,
                    json.dumps(analysis_summary_reasons),
                    activity.status,
                    activity.created_at.isoformat() if is_new else existing["created_at"],
                    now,
                ),
            )
            return is_new

    def _row_to_activity(self, row: sqlite3.Row) -> Activity:
        prize = None
        if row["prize_amount"] is not None or row["prize_currency"] or row["prize_description"]:
            prize = Prize(
                amount=row["prize_amount"],
                currency=row["prize_currency"] or "USD",
                description=row["prize_description"],
            )
        dates = None
        if row["start_date"] or row["end_date"] or row["deadline"]:
            dates = ActivityDates(
                start_date=datetime.fromisoformat(row["start_date"]) if row["start_date"] else None,
                end_date=datetime.fromisoformat(row["end_date"]) if row["end_date"] else None,
                deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
            )
        description, full_content, summary = self._clean_activity_texts(
            source_id=row["source_id"],
            title=row["title"],
            description=row["description"],
            full_content=row["full_content"],
            summary=row["summary"],
        )
        snapshot_fields = self._unpack_activity_snapshot_fields(row)
        return Activity(
            id=row["id"],
            title=row["title"],
            description=description,
            full_content=full_content,
            source_id=row["source_id"],
            source_name=row["source_name"],
            url=row["url"],
            category=row["category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            prize=prize,
            dates=dates,
            location=row["location"],
            organizer=row["organizer"],
            image_url=row["image_url"],
            summary=summary,
            score=row["score"],
            score_reason=row["score_reason"],
            deadline_level=row["deadline_level"],
            trust_level=row["trust_level"],
            updated_fields=json.loads(row["updated_fields"]) if row["updated_fields"] else [],
            analysis_fields=json.loads(row["analysis_fields"]) if "analysis_fields" in row.keys() and row["analysis_fields"] else {},
            analysis_status=snapshot_fields["analysis_status"],
            analysis_failed_layer=row["analysis_failed_layer"] if "analysis_failed_layer" in row.keys() else None,
            analysis_summary_reasons=json.loads(row["analysis_summary_reasons"])
            if "analysis_summary_reasons" in row.keys() and row["analysis_summary_reasons"]
            else [],
            analysis_summary=snapshot_fields["analysis_summary"],
            analysis_reasons=snapshot_fields["analysis_reasons"],
            analysis_risk_flags=snapshot_fields["analysis_risk_flags"],
            analysis_recommended_action=snapshot_fields["analysis_recommended_action"],
            analysis_confidence=snapshot_fields["analysis_confidence"],
            analysis_structured=snapshot_fields["analysis_structured"],
            analysis_template_id=snapshot_fields["analysis_template_id"],
            analysis_current_run_id=snapshot_fields["analysis_current_run_id"],
            analysis_updated_at=snapshot_fields["analysis_updated_at"],
            is_tracking=bool(row["is_tracking"]) if "is_tracking" in row.keys() else False,
            is_favorited=bool(row["is_favorited"]) if "is_favorited" in row.keys() else False,
            is_digest_candidate=bool(row["is_digest_candidate"]) if "is_digest_candidate" in row.keys() else False,
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _tracking_state_from_row(self, row: sqlite3.Row) -> TrackingState:
        return TrackingState(
            activity_id=row["activity_id"],
            is_favorited=bool(row["is_favorited"]),
            status=row["status"],
            notes=row["notes"],
            next_action=row["next_action"],
            remind_at=row["remind_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _digest_from_row(self, row: sqlite3.Row) -> DigestRecord:
        return DigestRecord(
            id=row["id"],
            digest_date=row["digest_date"],
            title=row["title"],
            summary=row["summary"],
            content=row["content"],
            item_ids=json.loads(row["item_ids"]) if row["item_ids"] else [],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_sent_at=row["last_sent_at"],
            send_channel=row["send_channel"],
        )

    def _analysis_job_from_row(self, row: sqlite3.Row) -> AnalysisJob:
        return AnalysisJob(
            id=row["id"],
            trigger_type=row["trigger_type"],
            scope_type=row["scope_type"],
            template_id=row["template_id"],
            route_policy=json.loads(row["route_policy"]) if row["route_policy"] else {},
            budget_policy=json.loads(row["budget_policy"]) if row["budget_policy"] else {},
            status=row["status"],
            requested_by=row["requested_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        )

    def _analysis_job_item_from_row(self, row: sqlite3.Row) -> AnalysisJobItem:
        return AnalysisJobItem(
            id=row["id"],
            job_id=row["job_id"],
            activity_id=row["activity_id"],
            status=row["status"],
            needs_research=bool(row["needs_research"]),
            final_draft_status=row["final_draft_status"],
            screening_model=row["screening_model"],
            research_model=row["research_model"],
            verdict_model=row["verdict_model"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _analysis_step_from_row(self, row: sqlite3.Row) -> AnalysisStep:
        return AnalysisStep(
            id=row["id"],
            job_item_id=row["job_item_id"],
            step_type=row["step_type"],
            step_status=row["step_status"],
            input_digest=row["input_digest"],
            output_payload=json.loads(row["output_payload"]) if row["output_payload"] else {},
            latency_ms=row["latency_ms"],
            cost_tokens_in=row["cost_tokens_in"],
            cost_tokens_out=row["cost_tokens_out"],
            model_name=row["model_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _analysis_evidence_from_row(self, row: sqlite3.Row) -> AnalysisEvidence:
        return AnalysisEvidence(
            id=row["id"],
            job_item_id=row["job_item_id"],
            source_type=row["source_type"],
            url=row["url"],
            title=row["title"],
            snippet=row["snippet"],
            relevance_score=row["relevance_score"],
            trust_score=row["trust_score"],
            supports_claim=bool(row["supports_claim"]) if row["supports_claim"] is not None else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _analysis_review_from_row(self, row: sqlite3.Row) -> AnalysisReview:
        return AnalysisReview(
            id=row["id"],
            job_item_id=row["job_item_id"],
            activity_id=row["activity_id"],
            review_action=row["review_action"],
            review_note=row["review_note"],
            reviewed_by=row["reviewed_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_activity_by_id(self, activity_id: str) -> Optional[Activity]:
        with self._get_connection() as conn:
            digest_date = self._normalize_digest_date()
            row = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited,
                    CASE WHEN dc.activity_id IS NULL THEN 0 ELSE 1 END AS is_digest_candidate
                FROM activities a
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                LEFT JOIN digest_candidates dc ON dc.activity_id = a.id AND dc.digest_date = ?
                WHERE a.id = ?
                """,
                (digest_date, activity_id),
            ).fetchone()
            if not row or self._is_hidden_activity_row(row):
                return None
            return self._row_to_activity(row)

    def _timeline_for_activity(self, activity: Activity) -> List[Dict[str, str]]:
        if activity.dates is None:
            return []
        entries: List[TimelineEvent] = []
        if activity.dates.start_date:
            entries.append(TimelineEvent(key="start_date", label="Start", timestamp=activity.dates.start_date.isoformat()))
        if activity.dates.end_date:
            entries.append(TimelineEvent(key="end_date", label="End", timestamp=activity.dates.end_date.isoformat()))
        if activity.dates.deadline:
            entries.append(TimelineEvent(key="deadline", label="Deadline", timestamp=activity.dates.deadline.isoformat()))
        return [entry.model_dump() for entry in entries]

    def get_related_activities(self, activity_id: str, category: str, limit: int = 3) -> List[Activity]:
        with self._get_connection() as conn:
            digest_date = self._normalize_digest_date()
            rows = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited,
                    CASE WHEN dc.activity_id IS NULL THEN 0 ELSE 1 END AS is_digest_candidate
                FROM activities a
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                LEFT JOIN digest_candidates dc ON dc.activity_id = a.id AND dc.digest_date = ?
                WHERE a.category = ? AND a.id != ?
                ORDER BY COALESCE(a.score, 0) DESC, a.created_at DESC
                LIMIT ?
                """,
                (digest_date, category, activity_id, limit),
            ).fetchall()
            return self._visible_activities_from_rows(rows)

    def get_activity_detail(self, activity_id: str) -> Optional[Dict[str, Any]]:
        activity = self.get_activity_by_id(activity_id)
        if activity is None:
            return None
        result = activity.model_dump(mode="json")
        with self._get_connection() as conn:
            source_row = self._source_snapshot(conn, activity.source_id)
            _, analysis_result = self._analysis_result_for_activity(activity, source_row, conn)
        result["analysis_layer_results"] = [
            layer.model_dump(mode="json") if hasattr(layer, "model_dump") else layer
            for layer in analysis_result.layer_results
        ]
        result["analysis_score_breakdown"] = analysis_result.score_breakdown
        result["timeline"] = self._timeline_for_activity(activity)
        result["related_items"] = [
            item.model_dump(mode="json") for item in self.get_related_activities(activity.id, activity.category.value)
        ]
        result["tracking"] = self.get_tracking_item(activity.id)
        return result

    def get_analysis_results(
        self,
        *,
        analysis_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if analysis_status:
            filters["analysis_status"] = analysis_status

        activities, total = self.get_activities(
            filters=filters,
            sort_by="score",
            sort_order="desc",
            page=page,
            page_size=page_size,
        )

        items: List[Dict[str, Any]] = []
        with self._get_connection() as conn:
            for activity in activities:
                source_row = self._source_snapshot(conn, activity.source_id)
                _, analysis_result = self._analysis_result_for_activity(activity, source_row, conn)
                item = activity.model_dump(mode="json")
                item["analysis_layer_results"] = [
                    layer.model_dump(mode="json") if hasattr(layer, "model_dump") else layer
                    for layer in analysis_result.layer_results
                ]
                item["analysis_score_breakdown"] = analysis_result.score_breakdown
                items.append(item)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    def get_activities(
        self,
        filters: dict | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Activity], int]:
        filters = filters or {}
        digest_date = self._normalize_digest_date()
        conditions = []
        params: List[Any] = []
        base_from = """
            FROM activities a
            LEFT JOIN tracking_items t ON t.activity_id = a.id
            LEFT JOIN digest_candidates dc ON dc.activity_id = a.id AND dc.digest_date = ?
        """
        params.append(digest_date)
        if filters.get("category"):
            conditions.append("a.category = ?")
            params.append(filters["category"])
        if filters.get("source_id"):
            conditions.append("a.source_id = ?")
            params.append(filters["source_id"])
        if filters.get("status"):
            conditions.append("a.status = ?")
            params.append(filters["status"])
        if filters.get("search"):
            conditions.append("(a.title LIKE ? OR a.description LIKE ? OR a.summary LIKE ?)")
            term = f"%{filters['search']}%"
            params.extend([term, term, term])
        if filters.get("analysis_status"):
            conditions.append("a.analysis_status = ?")
            params.append(filters["analysis_status"])
        if filters.get("deadline_level"):
            conditions.append("a.deadline_level = ?")
            params.append(filters["deadline_level"])
        if filters.get("trust_level"):
            conditions.append("a.trust_level = ?")
            params.append(filters["trust_level"])
        if "is_tracking" in filters and filters["is_tracking"] not in (None, "", "all"):
            is_tracking = str(filters["is_tracking"]).lower() in {"1", "true", "yes"}
            conditions.append("t.activity_id IS NOT NULL" if is_tracking else "t.activity_id IS NULL")
        if "is_favorited" in filters and filters["is_favorited"] not in (None, "", "all"):
            is_favorited = str(filters["is_favorited"]).lower() in {"1", "true", "yes"}
            conditions.append("COALESCE(t.is_favorited, 0) = ?" )
            params.append(1 if is_favorited else 0)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_map = {
            "created_at": "a.created_at",
            "updated_at": "a.updated_at",
            "deadline": "a.deadline",
            "prize_amount": "a.prize_amount",
            "prize": "a.prize_amount",
            "title": "a.title",
            "score": "COALESCE(a.score, 0)",
            "trust_level": "CASE a.trust_level WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END",
        }
        sort_expression = order_map.get(sort_by, "a.created_at")
        direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited,
                    CASE WHEN dc.activity_id IS NULL THEN 0 ELSE 1 END AS is_digest_candidate
                {base_from}
                WHERE {where_clause}
                ORDER BY {sort_expression} {direction}, a.created_at DESC
                """,
                params,
            ).fetchall()
            visible = self._visible_activities_from_rows(rows)
            total = len(visible)
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            return visible[start:end], total

    def get_activities_count(self) -> int:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT source_id, title, description, full_content, url FROM activities"
            ).fetchall()
            return sum(0 if self._is_hidden_activity_row(row) else 1 for row in rows)

    def update_source_status(
        self,
        source_id: str,
        status: SourceStatus,
        error_message: str | None = None,
        activity_count: int | None = None,
    ) -> None:
        with self._get_connection() as conn:
            now = datetime.now().isoformat()
            updates = ["status = ?", "last_run = ?"]
            params: List[Any] = [status.value, now]
            if status == SourceStatus.SUCCESS:
                updates.extend(["last_success = ?", "error_message = NULL"])
                params.append(now)
            if status == SourceStatus.ERROR and error_message:
                updates.append("error_message = ?")
                params.append(error_message)
            if activity_count is not None:
                updates.append("activity_count = ?")
                params.append(activity_count)
            params.append(source_id)
            conn.execute(f"UPDATE sources SET {', '.join(updates)} WHERE id = ?", params)
            self._refresh_source_activity_signals(conn, source_id)

    def _source_from_row(self, row: sqlite3.Row) -> Source:
        return Source(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            url=row["url"],
            priority=row["priority"],
            update_interval=row["update_interval"],
            enabled=bool(row["enabled"]),
            last_run=datetime.fromisoformat(row["last_run"]) if row["last_run"] else None,
            last_success=datetime.fromisoformat(row["last_success"]) if row["last_success"] else None,
            status=row["status"],
            error_message=row["error_message"],
            activity_count=row["activity_count"],
        )

    def get_sources_status(self) -> List[Source]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY priority, name").fetchall()
            return [self._source_from_row(row) for row in rows]

    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
            return self._source_from_row(row) if row else None

    def get_enabled_sources(self) -> List[Source]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sources WHERE enabled = 1 ORDER BY priority, name").fetchall()
            return [self._source_from_row(row) for row in rows]

    def get_stats(self) -> StatsResponse:
        with self._get_connection() as conn:
            recent_threshold = (datetime.now() - timedelta(days=1)).isoformat()
            rows = conn.execute(
                "SELECT source_id, title, description, full_content, url, category, created_at, updated_at FROM activities"
            ).fetchall()
            visible_rows = [row for row in rows if not self._is_hidden_activity_row(row)]
            category_counts: Dict[str, int] = {}
            source_counts: Dict[str, int] = {}
            recent_activities = 0
            last_update: str | None = None
            for row in visible_rows:
                category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
                source_counts[row["source_id"]] = source_counts.get(row["source_id"], 0) + 1
                if row["created_at"] and row["created_at"] > recent_threshold:
                    recent_activities += 1
                if row["updated_at"] and (last_update is None or row["updated_at"] > last_update):
                    last_update = row["updated_at"]
            return StatsResponse(
                total_activities=len(visible_rows),
                total_sources=conn.execute("SELECT COUNT(*) AS count FROM sources").fetchone()["count"],
                activities_by_category=category_counts,
                activities_by_source=source_counts,
                recent_activities=recent_activities,
                last_update=last_update,
            )

    def get_analysis_templates(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_templates ORDER BY is_default DESC, created_at ASC"
            ).fetchall()
            return [self._analysis_template_from_row(row) for row in rows]

    def get_default_analysis_template(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM analysis_templates
                ORDER BY is_default DESC, created_at ASC
                LIMIT 1
                """
            ).fetchone()
            return self._analysis_template_from_row(row) if row else None

    def create_analysis_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_connection() as conn:
            template_payload = dict(payload)
            template_payload["slug"] = self._unique_template_slug(
                conn,
                template_payload.get("slug") or self._slugify(template_payload["name"]),
            )
            return self._insert_analysis_template(conn, template_payload)

    def duplicate_analysis_template(self, template_id: str, name: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis template {template_id} not found")
            payload = self._analysis_template_from_row(row)
            payload["id"] = self._generate_record_id()
            payload["name"] = name
            payload["slug"] = self._unique_template_slug(conn, self._slugify(name))
            payload["is_default"] = False
            return self._insert_analysis_template(conn, payload)

    def update_analysis_template(self, template_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis template {template_id} not found")

            current = self._analysis_template_from_row(row)
            merged = {**current, **payload}
            business_fields_changed = any(
                field in payload for field in ("preference_profile", "risk_tolerance", "research_mode")
            )
            legacy_shape_overridden = "layers" in payload or "sort_fields" in payload
            if business_fields_changed and not legacy_shape_overridden:
                merged["layers"] = []
                merged["sort_fields"] = []
            merged = apply_template_compat_defaults(merged)
            name = merged["name"]
            slug = payload.get("slug")
            if slug:
                slug = self._unique_template_slug(conn, self._slugify(slug), exclude_id=template_id)
            elif name != current["name"]:
                slug = self._unique_template_slug(conn, self._slugify(name), exclude_id=template_id)
            else:
                slug = current["slug"]

            conn.execute(
                """
                UPDATE analysis_templates
                SET name = ?,
                    slug = ?,
                    description = ?,
                    tags = ?,
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
                    name,
                    slug,
                    merged["description"],
                    json.dumps(merged["tags"]),
                    json.dumps(merged["layers"]),
                    json.dumps(merged["sort_fields"]),
                    merged["preference_profile"],
                    merged["risk_tolerance"],
                    merged["research_mode"],
                    json.dumps(merged["compiled_policy"]),
                    datetime.now().isoformat(),
                    template_id,
                ),
            )
            updated = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            return self._analysis_template_from_row(updated)

    def set_default_analysis_template(self, template_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis template {template_id} not found")
            conn.execute("UPDATE analysis_templates SET is_default = 0")
            conn.execute(
                "UPDATE analysis_templates SET is_default = 1, updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), template_id),
            )
            self._refresh_all_activity_analysis(conn)
            updated = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            return self._analysis_template_from_row(updated)

    def delete_analysis_template(self, template_id: str) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis template {template_id} not found")

            total = conn.execute("SELECT COUNT(*) AS count FROM analysis_templates").fetchone()["count"]
            if total <= 1:
                raise ValueError("Cannot delete the last analysis template")

            was_default = bool(row["is_default"])
            conn.execute("DELETE FROM analysis_templates WHERE id = ?", (template_id,))

            if was_default:
                replacement = conn.execute(
                    "SELECT id FROM analysis_templates ORDER BY created_at ASC LIMIT 1"
                ).fetchone()
                if replacement is not None:
                    conn.execute(
                        "UPDATE analysis_templates SET is_default = 1, updated_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), replacement["id"]),
                    )
                    self._refresh_all_activity_analysis(conn)

            return True

    def upsert_tracking_item(self, activity_id: str, payload: Dict[str, Any]) -> TrackingState:
        with self._get_connection() as conn:
            if not conn.execute("SELECT id FROM activities WHERE id = ?", (activity_id,)).fetchone():
                raise ValueError(f"Activity {activity_id} not found")
            existing = conn.execute("SELECT * FROM tracking_items WHERE activity_id = ?", (activity_id,)).fetchone()
            now = datetime.now().isoformat()
            status = payload.get("status") or (existing["status"] if existing else TrackingStatus.SAVED.value)
            if status not in TRACKING_STATUS_VALUES:
                raise ValueError(f"Unsupported tracking status: {status}")
            is_favorited = payload.get("is_favorited")
            if is_favorited is None:
                is_favorited = bool(existing["is_favorited"]) if existing else False
            conn.execute(
                """
                INSERT OR REPLACE INTO tracking_items (
                    activity_id, is_favorited, status, notes, next_action, remind_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    1 if is_favorited else 0,
                    status,
                    payload.get("notes", existing["notes"] if existing else None),
                    payload.get("next_action", existing["next_action"] if existing else None),
                    payload.get("remind_at", existing["remind_at"] if existing else None),
                    existing["created_at"] if existing else now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM tracking_items WHERE activity_id = ?", (activity_id,)).fetchone()
            return self._tracking_state_from_row(row)

    def get_tracking_item(self, activity_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tracking_items WHERE activity_id = ?", (activity_id,)).fetchone()
            return self._tracking_state_from_row(row).model_dump() if row else None

    def get_tracking_items(self, status: str | None = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            where = "WHERE t.status = ?" if status else ""
            params = [status] if status else []
            rows = conn.execute(
                f"""
                SELECT t.*, a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM tracking_items t
                JOIN activities a ON a.id = t.activity_id
                {where}
                ORDER BY t.updated_at DESC
                """,
                params,
            ).fetchall()
            result = []
            for row in rows:
                if self._is_hidden_activity_row(row):
                    continue
                activity = self._row_to_activity(row)
                tracking = self._tracking_state_from_row(row)
                result.append({"activity": activity.model_dump(mode="json"), **tracking.model_dump()})
            return result

    def delete_tracking_item(self, activity_id: str) -> bool:
        with self._get_connection() as conn:
            result = conn.execute("DELETE FROM tracking_items WHERE activity_id = ?", (activity_id,))
            return result.rowcount > 0

    def add_digest_candidate(self, activity_id: str, digest_date: str | None = None) -> bool:
        target_date = self._normalize_digest_date(digest_date)
        with self._get_connection() as conn:
            if not conn.execute("SELECT id FROM activities WHERE id = ?", (activity_id,)).fetchone():
                raise ValueError(f"Activity {activity_id} not found")
            conn.execute(
                """
                INSERT OR IGNORE INTO digest_candidates (digest_date, activity_id, created_at)
                VALUES (?, ?, ?)
                """,
                (target_date, activity_id, datetime.now().isoformat()),
            )
            return True

    def remove_digest_candidate(self, activity_id: str, digest_date: str | None = None) -> bool:
        target_date = self._normalize_digest_date(digest_date)
        with self._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM digest_candidates WHERE digest_date = ? AND activity_id = ?",
                (target_date, activity_id),
            )
            return result.rowcount > 0

    def get_digest_candidates(self, digest_date: str | None = None) -> List[Activity]:
        target_date = self._normalize_digest_date(digest_date)
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited,
                    1 AS is_digest_candidate
                FROM digest_candidates dc
                JOIN activities a ON a.id = dc.activity_id
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                WHERE dc.digest_date = ?
                ORDER BY COALESCE(a.score, 0) DESC, a.created_at DESC, dc.created_at ASC
                """,
                (target_date,),
            ).fetchall()
            return self._visible_activities_from_rows(rows)

    def _digest_item_ids_for_date(self, conn: sqlite3.Connection, digest_date: str) -> List[str]:
        candidate_rows = conn.execute(
            """
            SELECT activity_id
            FROM digest_candidates
            WHERE digest_date = ?
            ORDER BY created_at ASC
            """,
            (digest_date,),
        ).fetchall()
        if candidate_rows:
            return [row["activity_id"] for row in candidate_rows]

        digest_day = datetime.fromisoformat(digest_date)
        rows = conn.execute(
            """
            SELECT id FROM activities
            WHERE created_at BETWEEN ? AND ?
            ORDER BY COALESCE(score, 0) DESC, created_at DESC
            LIMIT 5
            """,
            (
                (digest_day - timedelta(days=7)).isoformat(),
                datetime.combine(digest_day.date(), time.max).isoformat(),
            ),
        ).fetchall()
        return [row["id"] for row in rows]

    def _build_digest_content(self, activities: List[Activity]) -> Tuple[str, str]:
        content = "\n".join(
            f"- {activity.title}: {activity.summary or activity.description or activity.title}"
            for activity in activities
        ) or "No qualifying opportunities for this digest."
        summary = f"{len(activities)} opportunities selected for this digest"
        return summary, content

    def _get_activities_by_ids(self, conn: sqlite3.Connection, item_ids: List[str]) -> List[Activity]:
        if not item_ids:
            return []
        digest_date = self._normalize_digest_date()
        placeholders = ",".join(["?"] * len(item_ids))
        rows = conn.execute(
            f"""
            SELECT a.*,
                CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                COALESCE(t.is_favorited, 0) AS is_favorited,
                CASE WHEN dc.activity_id IS NULL THEN 0 ELSE 1 END AS is_digest_candidate
            FROM activities a
            LEFT JOIN tracking_items t ON t.activity_id = a.id
            LEFT JOIN digest_candidates dc ON dc.activity_id = a.id AND dc.digest_date = ?
            WHERE a.id IN ({placeholders})
            """,
            [digest_date, *item_ids],
        ).fetchall()
        activity_map = {
            row["id"]: self._row_to_activity(row)
            for row in rows
            if not self._is_hidden_activity_row(row)
        }
        return [activity_map[item_id] for item_id in item_ids if item_id in activity_map]

    def generate_digest(self, digest_date: str | None = None) -> DigestRecord:
        digest_date = self._normalize_digest_date(digest_date)
        with self._get_connection() as conn:
            existing = conn.execute("SELECT * FROM digests WHERE digest_date = ?", (digest_date,)).fetchone()
            if existing and existing["status"] == DigestStatus.SENT.value:
                return self._digest_from_row(existing)

            item_ids = self._digest_item_ids_for_date(conn, digest_date)
            activities = self._get_activities_by_ids(conn, item_ids)
            summary, content = self._build_digest_content(activities)
            now = datetime.now().isoformat()
            digest_id = hashlib.md5(f"digest:{digest_date}".encode()).hexdigest()
            if existing:
                digest_id = existing["id"]
                conn.execute(
                    """
                    UPDATE digests
                    SET title = ?,
                        summary = ?,
                        content = ?,
                        item_ids = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        f"VigilAI Digest {digest_date}",
                        summary,
                        content,
                        json.dumps(item_ids),
                        now,
                        digest_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO digests (
                        id, digest_date, title, summary, content, item_ids, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        digest_id,
                        digest_date,
                        f"VigilAI Digest {digest_date}",
                        summary,
                        content,
                        json.dumps(item_ids),
                        DigestStatus.DRAFT.value,
                        now,
                        now,
                    ),
                )
        return self.get_digest_by_id(digest_id)

    def get_digests(self, limit: int = 30) -> List[DigestRecord]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM digests ORDER BY digest_date DESC LIMIT ?", (limit,)).fetchall()
            return [self._digest_from_row(row) for row in rows]

    def get_digest_by_date(self, digest_date: str) -> Optional[DigestRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM digests WHERE digest_date = ?", (digest_date,)).fetchone()
            return self._digest_from_row(row) if row else None

    def get_digest_by_id(self, digest_id: str) -> Optional[DigestRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM digests WHERE id = ?", (digest_id,)).fetchone()
            return self._digest_from_row(row) if row else None

    def mark_digest_sent(self, digest_id: str, send_channel: str = "manual") -> DigestRecord:
        with self._get_connection() as conn:
            now = datetime.now().isoformat()
            conn.execute(
                """
                UPDATE digests
                SET status = ?, updated_at = ?, last_sent_at = ?, send_channel = ?
                WHERE id = ?
                """,
                (DigestStatus.SENT.value, now, now, send_channel, digest_id),
            )
        digest = self.get_digest_by_id(digest_id)
        if digest is None:
            raise ValueError(f"Digest {digest_id} not found")
        return digest

    def get_workspace(self) -> Dict[str, Any]:
        stats = self.get_stats().model_dump()
        with self._get_connection() as conn:
            top_rows = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM activities a
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                ORDER BY COALESCE(a.score, 0) DESC, a.created_at DESC
                LIMIT 20
                """
            ).fetchall()
            trend_source_rows = conn.execute(
                """
                SELECT source_id, title, description, full_content, url, created_at
                FROM activities
                WHERE created_at >= ?
                """,
                ((datetime.now() - timedelta(days=6)).isoformat(),),
            ).fetchall()
            source_rows = conn.execute(
                """
                SELECT * FROM sources
                WHERE status = ? OR (status = ? AND last_success IS NOT NULL AND last_success < ?)
                ORDER BY name ASC
                LIMIT 5
                """,
                (
                    SourceStatus.ERROR.value,
                    SourceStatus.SUCCESS.value,
                    (datetime.now() - timedelta(days=3)).isoformat(),
                ),
            ).fetchall()
            first_action_rows = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM activities a
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                WHERE (t.activity_id IS NULL OR t.status != ?) AND a.deadline IS NOT NULL
                ORDER BY a.deadline ASC, COALESCE(a.score, 0) DESC
                LIMIT 20
                """,
                (TrackingStatus.DONE.value,),
            ).fetchall()
            analysis_rows = conn.execute(
                """
                SELECT source_id, title, description, full_content, url, analysis_status
                FROM activities
                """
            ).fetchall()
            blocked_rows = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited,
                    0 AS is_digest_candidate
                FROM activities a
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                WHERE a.analysis_status = ?
                ORDER BY COALESCE(a.score, 0) DESC, a.created_at DESC
                LIMIT 20
                """,
                ("rejected",),
            ).fetchall()
        digest_preview = self.get_digests(limit=1)
        tracking_items = self.get_tracking_items()
        trends: Dict[str, int] = {}
        analysis_overview = {"total": 0, "passed": 0, "watch": 0, "rejected": 0}
        for row in trend_source_rows:
            if self._is_hidden_activity_row(row):
                continue
            day = row["created_at"][:10]
            trends[day] = trends.get(day, 0) + 1
        for row in analysis_rows:
            if self._is_hidden_activity_row(row):
                continue
            analysis_overview["total"] += 1
            status = row["analysis_status"]
            if status in {"passed", "watch", "rejected"}:
                analysis_overview[status] += 1
        top_opportunities = [activity.model_dump(mode="json") for activity in self._visible_activities_from_rows(top_rows)[:5]]
        first_actions = [activity.model_dump(mode="json") for activity in self._visible_activities_from_rows(first_action_rows)[:5]]
        blocked_opportunities = [
            activity.model_dump(mode="json") for activity in self._visible_activities_from_rows(blocked_rows)[:4]
        ]
        return {
            "overview": {
                **stats,
                "tracked_count": len(tracking_items),
                "favorited_count": len([item for item in tracking_items if item["is_favorited"]]),
            },
            "top_opportunities": top_opportunities,
            "digest_preview": digest_preview[0].model_dump() if digest_preview else None,
            "trends": [{"date": day, "count": trends[day]} for day in sorted(trends)],
            "alert_sources": [self._source_from_row(row).model_dump(mode="json") for row in source_rows],
            "first_actions": first_actions,
            "analysis_overview": analysis_overview,
            "blocked_opportunities": blocked_opportunities,
        }

    def delete_activity(self, activity_id: str) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM digest_candidates WHERE activity_id = ?", (activity_id,))
            conn.execute("DELETE FROM tracking_items WHERE activity_id = ?", (activity_id,))
            result = conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
            return result.rowcount > 0

    def clear_all_activities(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM digest_candidates")
            conn.execute("DELETE FROM tracking_items")
            conn.execute("DELETE FROM digests")
            conn.execute("DELETE FROM activities")
