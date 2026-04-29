from __future__ import annotations

from datetime import date, datetime, time, timedelta
import hashlib
import json
import logging
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from analysis.ai_enrichment import enrich_activity_for_analysis
from analysis.rule_engine import run_analysis
from analysis.schemas import AnalysisSnapshot, ResearchEvidence
from analysis.template_defaults import apply_template_compat_defaults, get_default_analysis_templates
from config import LOW_SIGNAL_FIRECRAWL_SOURCES, PRIORITY_INTERVALS, SOURCES_CONFIG
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
TRACKING_STAGE_VALUES = {"to_decide", "watching", "preparing", "submitted", "dropped"}
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

class DataManagerWorkspaceMixin:
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
            return self._visible_activities_from_rows(
                rows,
                include_news=self._is_news_activity(category),
            )

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
        else:
            conditions.append("a.category != ?")
            params.append("news")
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
            visible = self._visible_activities_from_rows(
                rows,
                include_news=filters.get("category") == "news",
            )
            visible = self._apply_extended_activity_filters(visible, filters)
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

    def get_stats(self, *, include_news: bool = True) -> StatsResponse:
        with self._get_connection() as conn:
            recent_threshold = (datetime.now() - timedelta(days=1)).isoformat()
            rows = conn.execute(
                "SELECT source_id, title, description, full_content, url, category, created_at, updated_at FROM activities"
            ).fetchall()
            visible_rows = [
                row
                for row in rows
                if not self._is_hidden_activity_row(row)
                and (include_news or not self._is_news_activity(row["category"]))
            ]
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
                total_sources=(
                    conn.execute("SELECT COUNT(*) AS count FROM sources").fetchone()["count"]
                    if include_news
                    else len(source_counts)
                ),
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

    def get_analysis_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_templates WHERE id = ?", (template_id,)).fetchone()
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
            stage = payload.get("stage", existing["stage"] if existing and "stage" in existing.keys() else None)
            if stage and stage not in TRACKING_STAGE_VALUES:
                raise ValueError(f"Unsupported tracking stage: {stage}")
            is_favorited = payload.get("is_favorited")
            if is_favorited is None:
                is_favorited = bool(existing["is_favorited"]) if existing else False
            conn.execute(
                """
                INSERT OR REPLACE INTO tracking_items (
                    activity_id, is_favorited, status, stage, notes, next_action, remind_at, block_reason,
                    abandon_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    1 if is_favorited else 0,
                    status,
                    stage,
                    payload.get("notes", existing["notes"] if existing else None),
                    payload.get("next_action", existing["next_action"] if existing else None),
                    payload.get("remind_at", existing["remind_at"] if existing else None),
                    payload.get("block_reason", existing["block_reason"] if existing else None),
                    payload.get("abandon_reason", existing["abandon_reason"] if existing else None),
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
        stats = self.get_stats(include_news=False).model_dump()
        with self._get_connection() as conn:
            top_rows = conn.execute(
                """
                SELECT a.*,
                    CASE WHEN t.activity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM activities a
                LEFT JOIN tracking_items t ON t.activity_id = a.id
                WHERE a.category != ?
                ORDER BY COALESCE(a.score, 0) DESC, a.created_at DESC
                LIMIT 20
                """
                ,
                ("news",),
            ).fetchall()
            trend_source_rows = conn.execute(
                """
                SELECT source_id, title, description, full_content, url, created_at
                FROM activities
                WHERE created_at >= ?
                    AND category != ?
                """,
                ((datetime.now() - timedelta(days=6)).isoformat(), "news"),
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
                WHERE (t.activity_id IS NULL OR t.status != ?)
                    AND a.deadline IS NOT NULL
                    AND a.category != ?
                ORDER BY a.deadline ASC, COALESCE(a.score, 0) DESC
                LIMIT 20
                """,
                (TrackingStatus.DONE.value, "news"),
            ).fetchall()
            analysis_rows = conn.execute(
                """
                SELECT source_id, title, description, full_content, url, analysis_status
                FROM activities
                WHERE category != ?
                """
                ,
                ("news",),
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
                    AND a.category != ?
                ORDER BY COALESCE(a.score, 0) DESC, a.created_at DESC
                LIMIT 20
                """,
                ("rejected", "news"),
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
