"""Autonomous investigation loop for reward-opportunity evaluation."""

from __future__ import annotations

from reward_opportunity.evaluator import evaluate_evidence_bundle
from reward_opportunity.investigator import decide_next_investigation_actions


def run_investigation_cycle(
    candidate: dict[str, object],
    evidence_bundle: dict[str, object],
    max_rounds: int = 2,
) -> dict[str, object]:
    actions: list[dict[str, object]] = []
    evaluation = evaluate_evidence_bundle(evidence_bundle)

    if not evaluation["needs_investigation"]:
        return {"status": "classified", "evaluation": evaluation, "actions": actions}

    for _round in range(max_rounds):
        next_actions = decide_next_investigation_actions(candidate, evidence_bundle)
        if not next_actions:
            break
        actions.extend(next_actions)
        return {"status": "needs_follow_up", "evaluation": evaluation, "actions": actions}

    return {"status": "classified", "evaluation": evaluation, "actions": actions}

