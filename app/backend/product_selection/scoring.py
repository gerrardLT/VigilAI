"""
Scoring helpers for product-selection opportunities.
"""

from __future__ import annotations

from typing import Any


def score_product_opportunity(
    candidate: dict[str, Any],
    *,
    cross_platform_signal_score: float,
) -> dict[str, Any]:
    demand = float(candidate.get("demand_score") or 0)
    competition = float(candidate.get("competition_score") or 0)
    price_fit = float(candidate.get("price_fit_score") or 0)
    risk = float(candidate.get("risk_score") or 0)

    low_competition = max(0.0, 100.0 - competition)
    opportunity_score = round(
        0.35 * demand
        + 0.25 * low_competition
        + 0.20 * price_fit
        + 0.10 * float(cross_platform_signal_score)
        - 0.10 * risk,
        2,
    )

    signals = candidate.get("signals") or []
    reliabilities = [float(item.get("reliability") or 0.65) for item in signals]
    average_reliability = sum(reliabilities) / len(reliabilities) if reliabilities else 0.65
    confidence_score = round(
        min(95.0, max(35.0, average_reliability * 100 * 0.7 + float(cross_platform_signal_score) * 0.3)),
        2,
    )

    return {
        **candidate,
        "cross_platform_signal_score": round(float(cross_platform_signal_score), 2),
        "opportunity_score": opportunity_score,
        "confidence_score": confidence_score,
    }
