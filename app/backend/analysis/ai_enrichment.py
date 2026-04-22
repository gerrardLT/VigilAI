"""
Deterministic AI-like enrichment for analysis fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any, Dict

from analysis.schemas import AnalysisContext, ScreeningResult

if TYPE_CHECKING:
    from models import Activity


def _normalize_activity_payload(activity: Dict[str, Any] | "Activity") -> Dict[str, Any]:
    if isinstance(activity, dict):
        return activity

    prize_amount = None
    prize = getattr(activity, "prize", None)
    if prize is not None:
        prize_amount = getattr(prize, "amount", None)

    category = getattr(activity, "category", None)
    category_value = getattr(category, "value", category)

    return {
        "title": getattr(activity, "title", None),
        "description": getattr(activity, "description", None),
        "full_content": getattr(activity, "full_content", None),
        "summary": getattr(activity, "summary", None),
        "category": category_value,
        "prize_amount": prize_amount,
    }


def _as_text(activity: Dict[str, Any]) -> str:
    return " ".join(
        str(part)
        for part in (
            activity.get("title"),
            activity.get("description"),
            activity.get("full_content"),
            activity.get("category"),
            activity.get("prize_amount"),
        )
        if part
    ).lower()


def _confidence(level: str) -> str:
    return level


def extract_heuristic_signals(activity: Dict[str, Any] | "Activity") -> Dict[str, Any]:
    normalized = _normalize_activity_payload(activity)
    text = _as_text(normalized)
    prize_amount = normalized.get("prize_amount") or 0

    if any(keyword in text for keyword in ("team", "squad", "group")):
        solo_friendliness = "team_required"
    elif any(keyword in text for keyword in ("solo", "individual", "single", "personal")):
        solo_friendliness = "solo_friendly"
    else:
        solo_friendliness = "unclear"

    if prize_amount >= 1000 or any(keyword in text for keyword in ("guaranteed reward", "cash prize", "reward payout")):
        reward_clarity = "high"
        reward_clarity_score = 3
    elif prize_amount > 0 or "reward" in text:
        reward_clarity = "medium"
        reward_clarity_score = 2
    else:
        reward_clarity = "low"
        reward_clarity_score = 1

    if any(keyword in text for keyword in ("small fix", "quick", "lightweight", "simple")):
        effort_level = "low"
    elif any(keyword in text for keyword in ("proposal", "deck", "application", "long-form")):
        effort_level = "high"
    else:
        effort_level = "medium"

    if any(keyword in text for keyword in ("within 7 days", "within 14 days", "fast payout", "quick payout")):
        payout_speed = "14d"
    elif any(keyword in text for keyword in ("30 days", "monthly", "review cycle")):
        payout_speed = "30d"
    else:
        payout_speed = "21d"

    trust_level = "high" if any(keyword in text for keyword in ("official", "guaranteed", "verified")) else "medium"

    roi_score = 40
    if prize_amount >= 1000:
        roi_score += 25
    elif prize_amount >= 500:
        roi_score += 15
    if effort_level == "low":
        roi_score += 20
    elif effort_level == "medium":
        roi_score += 10
    if payout_speed == "14d":
        roi_score += 10
    elif payout_speed == "21d":
        roi_score += 5
    if solo_friendliness == "solo_friendly":
        roi_score += 10
    roi_score = max(0, min(100, roi_score))

    if roi_score >= 80:
        roi_level = "high"
    elif roi_score >= 55:
        roi_level = "medium"
    else:
        roi_level = "low"

    trust_score = 80 if trust_level == "high" else 65

    return {
        "solo_friendliness": solo_friendliness,
        "reward_clarity": reward_clarity,
        "reward_clarity_score": reward_clarity_score,
        "effort_level": effort_level,
        "payout_speed": payout_speed,
        "source_trust": trust_level,
        "trust_score": trust_score,
        "roi_score": roi_score,
        "roi_level": roi_level,
        "_confidence": {
            "solo_friendliness": _confidence("high" if solo_friendliness != "unclear" else "medium"),
            "reward_clarity": _confidence("high" if reward_clarity != "low" else "medium"),
            "roi_level": _confidence("high" if prize_amount else "medium"),
            "source_trust": _confidence("medium"),
        },
    }


def enrich_activity_for_analysis(activity: Dict[str, Any]) -> Dict[str, Any]:
    return extract_heuristic_signals(activity)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def screening_result_from_heuristics(
    context: AnalysisContext,
    *,
    model_name: str | None = None,
    provider_error: str | None = None,
) -> ScreeningResult:
    signals = dict(context.heuristic_signals)
    source_health = context.source_health
    reward_clarity = str(signals.get("reward_clarity") or "low")
    effort_level = str(signals.get("effort_level") or "medium")
    payout_speed = str(signals.get("payout_speed") or "21d")
    roi_level = str(signals.get("roi_level") or "low")
    source_trust = str(signals.get("source_trust") or "low")
    solo_fit = str(signals.get("solo_friendliness") or "unclear")
    freshness_level = str(source_health.get("freshness_level") or "never")
    prize_amount = context.metadata.get("prize_amount")

    should_deep_research = (
        reward_clarity != "high"
        or source_trust == "low"
        or freshness_level in {"stale", "critical", "never"}
        or (
            context.current_snapshot is not None
            and context.current_snapshot.status == "watch"
        )
    )

    risk_flags: list[str] = []
    if source_trust == "low":
        risk_flags.append("low_source_trust")
    if freshness_level in {"stale", "critical", "never"}:
        risk_flags.append("stale_source")
    if reward_clarity == "low":
        risk_flags.append("unclear_rewards")
    if provider_error:
        risk_flags.append("heuristic_fallback")

    if source_trust == "low" and freshness_level in {"critical", "never"} and reward_clarity == "low":
        status = "reject"
    elif roi_level == "high" and reward_clarity == "high" and freshness_level in {"fresh", "aging"}:
        status = "pass"
    else:
        status = "watch"

    confidence = 0.58
    confidence += {"high": 0.16, "medium": 0.08, "low": -0.08}.get(source_trust, 0.0)
    confidence += {"high": 0.12, "medium": 0.04, "low": -0.08}.get(reward_clarity, 0.0)
    confidence += {"high": 0.08, "medium": 0.03, "low": -0.05}.get(roi_level, 0.0)
    confidence += {"fresh": 0.05, "aging": 0.02, "stale": -0.05, "critical": -0.08, "never": -0.06}.get(
        freshness_level,
        0.0,
    )
    confidence = round(max(0.2, min(0.92, confidence)), 2)

    reasons = [
        f"Reward clarity is {reward_clarity}",
        f"Estimated effort is {effort_level}",
        f"Source freshness is {freshness_level}",
    ]
    if should_deep_research:
        reasons.append("Stored evidence suggests deeper verification is warranted")

    if status == "pass":
        summary = "Stored activity content suggests a strong opportunity with clear reward mechanics."
        recommended_action = "queue_for_review"
    elif status == "reject":
        summary = "Stored activity content suggests weak trust or unclear economics for this opportunity."
        recommended_action = "deprioritize"
    else:
        summary = "Stored activity content is promising but still needs a human or deeper agent pass."
        recommended_action = "request_deep_research" if should_deep_research else "manual_review"

    structured = {
        "roi_level": roi_level,
        "effort_level": effort_level,
        "payout_speed": payout_speed,
        "reward_clarity": reward_clarity,
        "source_credibility": source_trust,
        "solo_fit": solo_fit,
        "urgency": context.metadata.get("deadline_level") or "unknown",
        "reward_estimate_present": bool(prize_amount),
        "trust_red_flags": [flag for flag in risk_flags if flag != "heuristic_fallback"],
        "should_deep_research": should_deep_research,
    }

    return ScreeningResult(
        status=status,
        summary=summary,
        reasons=_unique(reasons),
        risk_flags=_unique(risk_flags),
        recommended_action=recommended_action,
        confidence=confidence,
        structured=structured,
        evidence_summary="Screening used stored activity content only.",
        research_state="not_requested",
        needs_manual_review=status != "pass" or should_deep_research,
        model_name=model_name or "heuristic-screening",
    )
