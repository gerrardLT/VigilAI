"""
Helpers for building stored-content analysis context payloads.
"""

from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Any

from analysis.ai_enrichment import extract_heuristic_signals
from analysis.schemas import AnalysisContent, AnalysisContext, AnalysisSnapshot


def build_source_health_payload(source_row: sqlite3.Row | None) -> dict[str, Any]:
    if source_row is None:
        return {
            "status": "missing",
            "health_score": 0,
            "freshness_level": "never",
            "last_success_age_hours": None,
            "needs_attention": True,
            "activity_count": 0,
        }

    now = datetime.now()
    status = source_row["status"]
    last_success_age_hours = None
    freshness_level = "never"

    if source_row["last_success"]:
        last_success = datetime.fromisoformat(source_row["last_success"])
        last_success_age_hours = round((now - last_success).total_seconds() / 3600, 1)
        if last_success_age_hours <= 24:
            freshness_level = "fresh"
        elif last_success_age_hours <= 72:
            freshness_level = "aging"
        else:
            freshness_level = "stale"

    if status == "error":
        freshness_level = "critical" if source_row["last_success"] else "never"

    score = 40
    score += {"success": 35, "running": 25, "idle": 10, "error": -20}.get(status, 0)
    score += {"fresh": 20, "aging": 8, "stale": -10, "critical": -25, "never": -15}[freshness_level]
    activity_count = source_row["activity_count"] or 0
    if activity_count >= 10:
        score += 10
    elif activity_count > 0:
        score += 5

    return {
        "status": status,
        "health_score": max(0, min(100, int(score))),
        "freshness_level": freshness_level,
        "last_success_age_hours": last_success_age_hours,
        "needs_attention": status == "error" or freshness_level in {"stale", "critical", "never"},
        "activity_count": activity_count,
        "last_run": source_row["last_run"],
        "last_success": source_row["last_success"],
        "error_message": source_row["error_message"],
    }


def _resolved_snapshot(activity, current_snapshot: AnalysisSnapshot | None) -> AnalysisSnapshot | None:
    if current_snapshot is not None:
        return current_snapshot
    if not getattr(activity, "analysis_status", None) or not getattr(activity, "analysis_summary", None):
        return None
    return AnalysisSnapshot(
        status=activity.analysis_status,
        summary=activity.analysis_summary,
        reasons=list(getattr(activity, "analysis_reasons", []) or []),
        risk_flags=list(getattr(activity, "analysis_risk_flags", []) or []),
        recommended_action=getattr(activity, "analysis_recommended_action", None),
        confidence=getattr(activity, "analysis_confidence", None),
        structured=dict(getattr(activity, "analysis_structured", {}) or {}),
        template_id=getattr(activity, "analysis_template_id", None),
        current_run_id=getattr(activity, "analysis_current_run_id", None),
        updated_at=getattr(activity, "analysis_updated_at", None),
    )


def _deadline_level(activity) -> str:
    dates = getattr(activity, "dates", None)
    deadline = getattr(dates, "deadline", None) if dates else None
    if deadline is None:
        return "none"
    delta_days = (deadline - datetime.now()).total_seconds() / 86400
    if delta_days < 0:
        return "expired"
    if delta_days <= 3:
        return "urgent"
    if delta_days <= 7:
        return "soon"
    if delta_days <= 30:
        return "upcoming"
    return "later"


def _source_trust_level(source_row: sqlite3.Row | None) -> str:
    if source_row is None:
        return "low"
    status = source_row["status"]
    if status == "error":
        return "low"
    if status == "running":
        return "medium"
    if not source_row["last_success"]:
        return "low"
    delta = datetime.now() - datetime.fromisoformat(source_row["last_success"])
    if delta.days <= 3:
        return "high"
    if delta.days <= 7:
        return "medium"
    return "low"


def build_analysis_context(
    activity,
    source_row: sqlite3.Row | None,
    current_snapshot: AnalysisSnapshot | None,
) -> AnalysisContext:
    content_parts = [
        getattr(activity, "title", None),
        getattr(activity, "description", None),
        getattr(activity, "full_content", None),
    ]
    category = getattr(getattr(activity, "category", None), "value", getattr(activity, "category", None))
    content = AnalysisContent(
        title=activity.title,
        description=activity.description,
        full_content=activity.full_content,
        full_text="\n\n".join(part.strip() for part in content_parts if part and str(part).strip()),
        url=activity.url,
        category=category or "unknown",
        summary=getattr(activity, "summary", None),
        source_name=getattr(activity, "source_name", None),
    )
    prize = getattr(activity, "prize", None)
    prize_amount = getattr(prize, "amount", None) if prize is not None else None
    heuristic_signals = extract_heuristic_signals(activity)
    source_trust = _source_trust_level(source_row)
    heuristic_signals["source_trust"] = source_trust
    heuristic_signals["trust_score"] = {"high": 85, "medium": 65, "low": 40}[source_trust]

    return AnalysisContext(
        activity_id=activity.id,
        source_id=activity.source_id,
        content=content,
        source_health=build_source_health_payload(source_row),
        tracking={
            "is_tracking": bool(getattr(activity, "is_tracking", False)),
            "is_favorited": bool(getattr(activity, "is_favorited", False)),
            "activity_status": getattr(activity, "status", None),
        },
        heuristic_signals=heuristic_signals,
        metadata={
            "deadline_level": _deadline_level(activity),
            "prize_amount": prize_amount,
            "organizer": getattr(activity, "organizer", None),
            "template_id": getattr(activity, "analysis_template_id", None),
        },
        current_snapshot=_resolved_snapshot(activity, current_snapshot),
    )
