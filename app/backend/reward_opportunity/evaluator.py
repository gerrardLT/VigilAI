"""Structured evaluation helpers for reward-opportunity evidence bundles."""

from __future__ import annotations


def evaluate_evidence_bundle(bundle: dict[str, object]) -> dict[str, object]:
    reward_snippets = bundle.get("reward_snippets") or []
    action_snippets = bundle.get("action_snippets") or []
    time_snippets = bundle.get("time_snippets") or []

    enough_evidence = bool(reward_snippets and action_snippets)
    label = "高价值" if enough_evidence and time_snippets else "待补证据"

    return {
        "ai_stage_2_label": label,
        "ai_confidence": 0.82 if enough_evidence else 0.51,
        "ai_summary": "奖励明确且动作明确" if enough_evidence else "存在奖励线索，但证据不足",
        "ai_missing_evidence": [] if enough_evidence and time_snippets else ["time_or_rule_detail"],
        "needs_investigation": not enough_evidence or not time_snippets,
    }

