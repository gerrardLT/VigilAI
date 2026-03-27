"""
Deterministic AI-like enrichment for analysis fields.
"""

from __future__ import annotations

from typing import Any, Dict


def _as_text(activity: Dict[str, Any]) -> str:
    return " ".join(
        str(part)
        for part in (
            activity.get("title"),
            activity.get("description"),
            activity.get("category"),
            activity.get("prize_amount"),
        )
        if part
    ).lower()


def _confidence(level: str) -> str:
    return level


def enrich_activity_for_analysis(activity: Dict[str, Any]) -> Dict[str, Any]:
    text = _as_text(activity)
    prize_amount = activity.get("prize_amount") or 0

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
