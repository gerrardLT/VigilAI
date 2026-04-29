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

class DataManagerActivityMixin:
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

    @staticmethod
    def _category_value(category: Any) -> str:
        return category.value if hasattr(category, "value") else str(category or "")

    def _is_news_activity(self, category: Any) -> bool:
        return self._category_value(category) == "news"

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

    def _visible_activities_from_rows(
        self,
        rows: List[sqlite3.Row],
        *,
        include_news: bool = False,
    ) -> List[Activity]:
        activities: List[Activity] = []
        for row in rows:
            if self._is_hidden_activity_row(row):
                continue
            if not include_news and self._is_news_activity(row["category"]):
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
            reasons.append("信息很新")
        elif age_days <= 7:
            score += 20
            reasons.append("近期更新")
        else:
            score += 10
        if deadline_level == "urgent":
            score += 30
            reasons.append("截止时间紧")
        elif deadline_level == "soon":
            score += 20
            reasons.append("临近截止")
        elif deadline_level == "upcoming":
            score += 10
        if activity.prize and activity.prize.amount:
            score += 20 if activity.prize.amount >= 5000 else 10
            reasons.append("奖励明确")
        trust_bonus = {"high": 20, "medium": 10, "low": 0}[trust_level]
        score += trust_bonus
        if trust_bonus:
            reasons.append(f"来源可信度{ '高' if trust_level == 'high' else '中等' }")
        return min(score, 100.0), reasons

    def _to_iso(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    def _normalize_digest_date(self, digest_date: str | None = None) -> str:
        return digest_date or date.today().isoformat()

    def _matches_prize_range(self, activity: Activity, prize_range: str) -> bool:
        amount = activity.prize.amount if activity.prize and activity.prize.amount is not None else None
        if prize_range == "unknown":
            return amount is None
        if amount is None:
            return False
        if prize_range == "0-500":
            return 0 <= amount <= 500
        if prize_range == "500-2000":
            return 500 <= amount <= 2000
        if prize_range == "2000-10000":
            return 2000 <= amount <= 10000
        if prize_range == "10000+":
            return amount >= 10000
        return True

    def _normalize_remote_mode(self, location: str | None) -> str:
        if not location:
            return "unknown"

        normalized = location.strip().lower()
        remote_keywords = ("remote", "online", "virtual", "global", "线上", "远程", "云端")
        hybrid_keywords = ("hybrid", "mixed", "线上+线下", "remote + onsite", "online + offline")
        offline_keywords = ("offline", "onsite", "in-person", "线下", "现场")

        if any(keyword in normalized for keyword in hybrid_keywords):
            return "hybrid"
        if any(keyword in normalized for keyword in remote_keywords):
            return "remote"
        if any(keyword in normalized for keyword in offline_keywords):
            return "offline"
        return "offline"

    def _matches_analysis_field(self, activity: Activity, key: str, expected: str) -> bool:
        if not expected:
            return True
        actual = (activity.analysis_fields or {}).get(key)
        return actual == expected

    def _apply_extended_activity_filters(
        self,
        activities: List[Activity],
        filters: Dict[str, Any],
    ) -> List[Activity]:
        filtered = activities

        if filters.get("prize_range"):
            filtered = [
                activity
                for activity in filtered
                if self._matches_prize_range(activity, filters["prize_range"])
            ]

        analysis_field_filters = {
            "solo_friendliness": "solo_friendliness",
            "reward_clarity": "reward_clarity",
            "effort_level": "effort_level",
        }
        for filter_key, analysis_key in analysis_field_filters.items():
            if filters.get(filter_key):
                filtered = [
                    activity
                    for activity in filtered
                    if self._matches_analysis_field(activity, analysis_key, filters[filter_key])
                ]

        if filters.get("remote_mode"):
            filtered = [
                activity
                for activity in filtered
                if self._normalize_remote_mode(activity.location) == filters["remote_mode"]
            ]

        return filtered

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
            "，".join(reasons) if reasons else None,
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
                    analysis_summary_reasons = ?,
                    updated_at = ?
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
            stage=row["stage"] if "stage" in row.keys() else None,
            notes=row["notes"],
            next_action=row["next_action"],
            remind_at=row["remind_at"],
            block_reason=row["block_reason"] if "block_reason" in row.keys() else None,
            abandon_reason=row["abandon_reason"] if "abandon_reason" in row.keys() else None,
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

