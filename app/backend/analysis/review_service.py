"""
Human review and writeback helpers for agent-analysis drafts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from analysis.schemas import AnalysisSnapshot
from models import AnalysisReviewResult


class ReviewService:
    def __init__(self, *, data_manager) -> None:
        self.data_manager = data_manager

    def _resolve_final_snapshot(
        self,
        *,
        item_id: str,
        edited_snapshot: dict[str, Any] | None,
    ) -> AnalysisSnapshot:
        current = self.data_manager.get_latest_draft_snapshot(item_id)
        if current is None:
            raise ValueError(f"No draft snapshot found for analysis item {item_id}")
        if not edited_snapshot:
            return current

        merged = current.model_dump(mode="json")
        if "structured" in edited_snapshot and isinstance(edited_snapshot["structured"], dict):
            structured = dict(merged.get("structured") or {})
            structured.update(edited_snapshot["structured"])
            merged["structured"] = structured
        merged.update({key: value for key, value in edited_snapshot.items() if key != "structured"})
        merged.setdefault("current_run_id", current.current_run_id)
        merged.setdefault("template_id", current.template_id)
        merged["updated_at"] = datetime.now().isoformat()
        return AnalysisSnapshot.model_validate(merged)

    def approve_item(
        self,
        item_id: str,
        *,
        review_note: str | None = None,
        reviewed_by: str | None = None,
        edited_snapshot: dict[str, Any] | None = None,
    ) -> AnalysisReviewResult:
        item = self.data_manager.get_analysis_job_item(item_id)
        if item is None:
            raise ValueError(f"Analysis item {item_id} not found")

        final_snapshot = self._resolve_final_snapshot(item_id=item_id, edited_snapshot=edited_snapshot)
        self.data_manager.write_activity_snapshot(item.activity_id, final_snapshot)
        self.data_manager.insert_analysis_review(
            job_item_id=item.id,
            activity_id=item.activity_id,
            review_action="approved",
            review_note=review_note,
            reviewed_by=reviewed_by,
        )
        return AnalysisReviewResult(
            review_action="approved",
            item_id=item.id,
            activity_id=item.activity_id,
            review_note=review_note,
            snapshot=final_snapshot,
        )

    def reject_item(
        self,
        item_id: str,
        *,
        review_note: str | None = None,
        reviewed_by: str | None = None,
    ) -> AnalysisReviewResult:
        item = self.data_manager.get_analysis_job_item(item_id)
        if item is None:
            raise ValueError(f"Analysis item {item_id} not found")

        self.data_manager.insert_analysis_review(
            job_item_id=item.id,
            activity_id=item.activity_id,
            review_action="rejected",
            review_note=review_note,
            reviewed_by=reviewed_by,
        )
        return AnalysisReviewResult(
            review_action="rejected",
            item_id=item.id,
            activity_id=item.activity_id,
            review_note=review_note,
            snapshot=None,
        )
