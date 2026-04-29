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

class DataManagerAnalysisMixin:
    def replace_analysis_evidence(
        self,
        job_item_id: str,
        evidence: list[ResearchEvidence],
    ) -> List[AnalysisEvidence]:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM analysis_evidence WHERE job_item_id = ?", (job_item_id,))
            for item in evidence:
                payload = item.model_dump() if hasattr(item, "model_dump") else dict(item)
                conn.execute(
                    """
                    INSERT INTO analysis_evidence (
                        id, job_item_id, source_type, url, title, snippet, relevance_score,
                        trust_score, supports_claim, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._generate_record_id(),
                        job_item_id,
                        payload.get("source_type"),
                        payload.get("url"),
                        payload.get("title"),
                        payload.get("snippet"),
                        payload.get("relevance_score"),
                        payload.get("trust_score"),
                        payload.get("supports_claim"),
                        datetime.now().isoformat(),
                    ),
                )
            rows = conn.execute(
                """
                SELECT * FROM analysis_evidence
                WHERE job_item_id = ?
                ORDER BY rowid ASC
                """,
                (job_item_id,),
            ).fetchall()
            return [self._analysis_evidence_from_row(row) for row in rows]

    def get_analysis_evidence(self, job_item_id: str) -> List[AnalysisEvidence]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_evidence
                WHERE job_item_id = ?
                ORDER BY rowid ASC
                """,
                (job_item_id,),
            ).fetchall()
            return [self._analysis_evidence_from_row(row) for row in rows]

    def create_analysis_job(
        self,
        *,
        trigger_type: str,
        scope_type: str,
        template_id: str | None,
        route_policy: dict[str, Any],
        budget_policy: dict[str, Any],
        status: str,
        requested_by: str | None = None,
    ) -> AnalysisJob:
        with self._get_connection() as conn:
            job_id = self._generate_record_id()
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO analysis_jobs (
                    id, trigger_type, scope_type, template_id, route_policy, budget_policy,
                    status, requested_by, created_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    trigger_type,
                    scope_type,
                    template_id,
                    json.dumps(route_policy),
                    json.dumps(budget_policy),
                    status,
                    requested_by,
                    now,
                    now if status in {"completed", "failed"} else None,
                ),
            )
            row = conn.execute("SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)).fetchone()
            return self._analysis_job_from_row(row)

    def update_analysis_job(self, job_id: str, **fields: Any) -> AnalysisJob:
        if not fields:
            job = self.get_analysis_job(job_id)
            if job is None:
                raise ValueError(f"Analysis job {job_id} not found")
            return job

        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            if key in {"route_policy", "budget_policy"} and isinstance(value, dict):
                params.append(json.dumps(value))
            elif isinstance(value, datetime):
                params.append(value.isoformat())
            else:
                params.append(value)
        if "status" in fields and fields["status"] in {"completed", "failed"} and "finished_at" not in fields:
            assignments.append("finished_at = ?")
            params.append(datetime.now().isoformat())
        params.append(job_id)

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE analysis_jobs SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
            row = conn.execute("SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis job {job_id} not found")
            return self._analysis_job_from_row(row)

    def get_analysis_job(self, job_id: str) -> AnalysisJob | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)).fetchone()
            return self._analysis_job_from_row(row) if row else None

    def create_analysis_job_item(
        self,
        *,
        job_id: str,
        activity_id: str,
        status: str,
        needs_research: bool = False,
        final_draft_status: str | None = None,
        screening_model: str | None = None,
        research_model: str | None = None,
        verdict_model: str | None = None,
    ) -> AnalysisJobItem:
        with self._get_connection() as conn:
            item_id = self._generate_record_id()
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO analysis_job_items (
                    id, job_id, activity_id, status, needs_research, final_draft_status,
                    screening_model, research_model, verdict_model, started_at, finished_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    job_id,
                    activity_id,
                    status,
                    1 if needs_research else 0,
                    final_draft_status,
                    screening_model,
                    research_model,
                    verdict_model,
                    now,
                    now if status in {"completed", "failed"} else None,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM analysis_job_items WHERE id = ?", (item_id,)).fetchone()
            return self._analysis_job_item_from_row(row)

    def update_analysis_job_item(self, item_id: str, **fields: Any) -> AnalysisJobItem:
        if not fields:
            item = self.get_analysis_job_item(item_id)
            if item is None:
                raise ValueError(f"Analysis job item {item_id} not found")
            return item

        assignments: list[str] = ["updated_at = ?"]
        params: list[Any] = [datetime.now().isoformat()]
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            if key == "needs_research":
                params.append(1 if value else 0)
            elif isinstance(value, datetime):
                params.append(value.isoformat())
            else:
                params.append(value)
        if "status" in fields and fields["status"] in {"completed", "failed"} and "finished_at" not in fields:
            assignments.append("finished_at = ?")
            params.append(datetime.now().isoformat())
        params.append(item_id)

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE analysis_job_items SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
            row = conn.execute("SELECT * FROM analysis_job_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise ValueError(f"Analysis job item {item_id} not found")
            return self._analysis_job_item_from_row(row)

    def get_analysis_job_item(self, item_id: str) -> AnalysisJobItem | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM analysis_job_items WHERE id = ?", (item_id,)).fetchone()
            return self._analysis_job_item_from_row(row) if row else None

    def get_analysis_job_items(self, job_id: str) -> List[AnalysisJobItem]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_job_items
                WHERE job_id = ?
                ORDER BY created_at ASC
                """,
                (job_id,),
            ).fetchall()
            return [self._analysis_job_item_from_row(row) for row in rows]

    def create_analysis_step(
        self,
        *,
        job_item_id: str,
        step_type: str,
        step_status: str,
        input_digest: str | None = None,
        output_payload: dict[str, Any] | None = None,
        latency_ms: int | None = None,
        cost_tokens_in: int | None = None,
        cost_tokens_out: int | None = None,
        model_name: str | None = None,
    ) -> AnalysisStep:
        with self._get_connection() as conn:
            step_id = self._generate_record_id()
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO analysis_item_steps (
                    id, job_item_id, step_type, step_status, input_digest, output_payload,
                    latency_ms, cost_tokens_in, cost_tokens_out, model_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_id,
                    job_item_id,
                    step_type,
                    step_status,
                    input_digest,
                    json.dumps(output_payload or {}, default=str),
                    latency_ms,
                    cost_tokens_in,
                    cost_tokens_out,
                    model_name,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM analysis_item_steps WHERE id = ?", (step_id,)).fetchone()
            return self._analysis_step_from_row(row)

    def get_analysis_steps(self, job_item_id: str) -> List[AnalysisStep]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_item_steps
                WHERE job_item_id = ?
                ORDER BY created_at ASC
                """,
                (job_item_id,),
            ).fetchall()
            return [self._analysis_step_from_row(row) for row in rows]

    def _analysis_snapshot_from_payload(self, payload: dict[str, Any]) -> AnalysisSnapshot | None:
        if not payload:
            return None
        draft_payload = payload.get("draft") if isinstance(payload.get("draft"), dict) else payload
        if not isinstance(draft_payload, dict):
            return None
        try:
            return AnalysisSnapshot.model_validate(draft_payload)
        except Exception:
            return None

    def get_latest_draft_snapshot(self, job_item_id: str) -> AnalysisSnapshot | None:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_item_steps
                WHERE job_item_id = ? AND step_type IN ('safety', 'verdict')
                ORDER BY CASE step_type WHEN 'safety' THEN 0 ELSE 1 END, created_at DESC
                """,
                (job_item_id,),
            ).fetchall()
            for row in rows:
                payload = json.loads(row["output_payload"]) if row["output_payload"] else {}
                draft = self._analysis_snapshot_from_payload(payload)
                if draft is not None:
                    return draft
            return None

    def get_analysis_item_detail(self, item_id: str) -> Dict[str, Any] | None:
        item = self.get_analysis_job_item(item_id)
        if item is None:
            return None
        activity = self.get_activity_by_id(item.activity_id)
        draft = self.get_latest_draft_snapshot(item.id)
        return {
            **item.model_dump(mode="json"),
            "activity": activity.model_dump(mode="json") if activity else None,
            "draft": draft.model_dump(mode="json") if draft else None,
            "steps": [step.model_dump(mode="json") for step in self.get_analysis_steps(item.id)],
            "evidence": [evidence.model_dump(mode="json") for evidence in self.get_analysis_evidence(item.id)],
            "reviews": [review.model_dump(mode="json") for review in self.get_analysis_reviews(item.id)],
        }

    def get_analysis_job_detail(self, job_id: str) -> Dict[str, Any] | None:
        job = self.get_analysis_job(job_id)
        if job is None:
            return None
        items = [self.get_analysis_item_detail(item.id) for item in self.get_analysis_job_items(job_id)]
        materialized_items = [item for item in items if item is not None]
        return {
            **job.model_dump(mode="json"),
            "item_count": len(materialized_items),
            "items": materialized_items,
        }

    def list_analysis_jobs(self, limit: int = 20) -> Dict[str, Any]:
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM analysis_jobs").fetchone()["count"]
            rows = conn.execute(
                """
                SELECT * FROM analysis_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            items: list[dict[str, Any]] = []
            for row in rows:
                job = self._analysis_job_from_row(row)
                item_rows = conn.execute(
                    """
                    SELECT status, needs_research
                    FROM analysis_job_items
                    WHERE job_id = ?
                    """,
                    (job.id,),
                ).fetchall()
                items.append(
                    {
                        **job.model_dump(mode="json"),
                        "item_count": len(item_rows),
                        "completed_items": sum(1 for item in item_rows if item["status"] == "completed"),
                        "failed_items": sum(1 for item in item_rows if item["status"] == "failed"),
                        "needs_research_count": sum(1 for item in item_rows if item["needs_research"]),
                    }
                )
            return {"total": total, "items": items}

    def select_batch_candidates(
        self,
        *,
        stale_before_hours: int,
        max_items: int,
    ) -> List[str]:
        threshold = (datetime.now() - timedelta(hours=stale_before_hours)).isoformat()
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM activities
                WHERE analysis_updated_at IS NULL
                   OR analysis_updated_at < updated_at
                   OR analysis_updated_at < ?
                ORDER BY
                    CASE
                        WHEN analysis_updated_at IS NULL THEN 0
                        WHEN analysis_updated_at < updated_at THEN 1
                        ELSE 2
                    END,
                    updated_at DESC
                LIMIT ?
                """,
                (threshold, max_items * 3),
            ).fetchall()

        candidate_ids: list[str] = []
        for row in rows:
            if self._is_hidden_activity_row(row):
                continue
            candidate_ids.append(row["id"])
            if len(candidate_ids) >= max_items:
                break
        return candidate_ids

    def insert_analysis_review(
        self,
        *,
        job_item_id: str,
        activity_id: str,
        review_action: str,
        review_note: str | None = None,
        reviewed_by: str | None = None,
    ) -> AnalysisReview:
        with self._get_connection() as conn:
            review_id = self._generate_record_id()
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO analysis_reviews (
                    id, job_item_id, activity_id, review_action, review_note, reviewed_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    job_item_id,
                    activity_id,
                    review_action,
                    review_note,
                    reviewed_by,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM analysis_reviews WHERE id = ?", (review_id,)).fetchone()
            return self._analysis_review_from_row(row)

    def get_analysis_reviews(self, job_item_id: str) -> List[AnalysisReview]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_reviews
                WHERE job_item_id = ?
                ORDER BY created_at ASC
                """,
                (job_item_id,),
            ).fetchall()
            return [self._analysis_review_from_row(row) for row in rows]

    def write_activity_snapshot(self, activity_id: str, snapshot: AnalysisSnapshot) -> Activity:
        packed = self._pack_activity_snapshot_fields(snapshot)
        assignment_clause = ", ".join(f"{column} = ?" for column in packed.keys())
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE activities SET {assignment_clause} WHERE id = ?",
                [*packed.values(), activity_id],
            )
        activity = self.get_activity_by_id(activity_id)
        if activity is None:
            raise ValueError(f"Activity {activity_id} not found")
        return activity

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

