"""
SQLite-backed data manager for VigilAI.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
import hashlib
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH, PRIORITY_INTERVALS, SOURCES_CONFIG
from models import (
    Activity,
    ActivityDates,
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

logger = logging.getLogger(__name__)

TRACKING_STATUS_VALUES = {status.value for status in TrackingStatus}


class DataManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self._ensure_data_dir()
        self._init_db()
        self._init_sources()

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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_source_id ON activities(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracking_status ON tracking_items(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_digests_digest_date ON digests(digest_date)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_digest_candidates_date ON digest_candidates(digest_date)"
            )

    def _ensure_columns(self, conn: sqlite3.Connection, table: str, columns: Dict[str, str]) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, column_type in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")

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

    @staticmethod
    def generate_activity_id(source_id: str, url: str) -> str:
        return hashlib.md5(f"{source_id}:{url}".encode()).hexdigest()

    def _source_snapshot(self, conn: sqlite3.Connection, source_id: str) -> Optional[sqlite3.Row]:
        return conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()

    def _build_summary(self, activity: Activity) -> str:
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

    def _activity_enrichment(
        self,
        activity: Activity,
        source_row: sqlite3.Row | None,
    ) -> Tuple[str, float, Optional[str], str, str]:
        summary = self._build_summary(activity)
        deadline_level = self._deadline_level(activity)
        trust_level = self._trust_level(source_row)
        score, reasons = self._score_components(activity, trust_level, deadline_level)
        return summary, score, ", ".join(reasons) if reasons else None, deadline_level, trust_level

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
            activity = self._row_to_activity(row)
            summary, score, score_reason, deadline_level, trust_level = self._activity_enrichment(
                activity,
                source_row,
            )
            conn.execute(
                """
                UPDATE activities
                SET summary = ?,
                    score = ?,
                    score_reason = ?,
                    deadline_level = ?,
                    trust_level = ?
                WHERE id = ?
                """,
                (
                    summary,
                    score,
                    score_reason,
                    deadline_level,
                    trust_level,
                    activity.id,
                ),
            )

    def add_activity(self, activity: Activity) -> bool:
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM activities WHERE source_id = ? AND url = ?",
                (activity.source_id, activity.url),
            ).fetchone()
            is_new = existing is None
            source_row = self._source_snapshot(conn, activity.source_id)
            summary, score, score_reason, deadline_level, trust_level = self._activity_enrichment(
                activity,
                source_row,
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
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        return Activity(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            full_content=row["full_content"],
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
            summary=row["summary"],
            score=row["score"],
            score_reason=row["score_reason"],
            deadline_level=row["deadline_level"],
            trust_level=row["trust_level"],
            updated_fields=json.loads(row["updated_fields"]) if row["updated_fields"] else [],
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
            return self._row_to_activity(row) if row else None

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
            return [self._row_to_activity(row) for row in rows]

    def get_activity_detail(self, activity_id: str) -> Optional[Dict[str, Any]]:
        activity = self.get_activity_by_id(activity_id)
        if activity is None:
            return None
        result = activity.model_dump(mode="json")
        result["timeline"] = self._timeline_for_activity(activity)
        result["related_items"] = [
            item.model_dump(mode="json") for item in self.get_related_activities(activity.id, activity.category.value)
        ]
        result["tracking"] = self.get_tracking_item(activity.id)
        return result

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
            total = conn.execute(
                f"SELECT COUNT(*) AS total {base_from} WHERE {where_clause}",
                params,
            ).fetchone()["total"]
            rows = conn.execute(
                f"""
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited,
                    CASE WHEN dc.activity_id IS NULL THEN 0 ELSE 1 END AS is_digest_candidate
                {base_from}
                WHERE {where_clause}
                ORDER BY {sort_expression} {direction}, a.created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
            return [self._row_to_activity(row) for row in rows], total

    def get_activities_count(self) -> int:
        with self._get_connection() as conn:
            return conn.execute("SELECT COUNT(*) AS count FROM activities").fetchone()["count"]

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
            category_rows = conn.execute(
                "SELECT category, COUNT(*) AS count FROM activities GROUP BY category"
            ).fetchall()
            source_rows = conn.execute(
                "SELECT source_id, COUNT(*) AS count FROM activities GROUP BY source_id"
            ).fetchall()
            recent_threshold = (datetime.now() - timedelta(days=1)).isoformat()
            return StatsResponse(
                total_activities=conn.execute("SELECT COUNT(*) AS count FROM activities").fetchone()["count"],
                total_sources=conn.execute("SELECT COUNT(*) AS count FROM sources").fetchone()["count"],
                activities_by_category={row["category"]: row["count"] for row in category_rows},
                activities_by_source={row["source_id"]: row["count"] for row in source_rows},
                recent_activities=conn.execute(
                    "SELECT COUNT(*) AS count FROM activities WHERE created_at > ?",
                    (recent_threshold,),
                ).fetchone()["count"],
                last_update=conn.execute("SELECT MAX(updated_at) AS last_update FROM activities").fetchone()["last_update"],
            )

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
            return [self._row_to_activity(row) for row in rows]

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
        activity_map = {row["id"]: self._row_to_activity(row) for row in rows}
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
                LIMIT 5
                """
            ).fetchall()
            trend_rows = conn.execute(
                """
                SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count
                FROM activities
                WHERE created_at >= ?
                GROUP BY substr(created_at, 1, 10)
                ORDER BY day ASC
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
                LIMIT 5
                """,
                (TrackingStatus.DONE.value,),
            ).fetchall()
        digest_preview = self.get_digests(limit=1)
        tracking_items = self.get_tracking_items()
        return {
            "overview": {
                **stats,
                "tracked_count": len(tracking_items),
                "favorited_count": len([item for item in tracking_items if item["is_favorited"]]),
            },
            "top_opportunities": [self._row_to_activity(row).model_dump(mode="json") for row in top_rows],
            "digest_preview": digest_preview[0].model_dump() if digest_preview else None,
            "trends": [{"date": row["day"], "count": row["count"]} for row in trend_rows],
            "alert_sources": [self._source_from_row(row).model_dump(mode="json") for row in source_rows],
            "first_actions": [self._row_to_activity(row).model_dump(mode="json") for row in first_action_rows],
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
