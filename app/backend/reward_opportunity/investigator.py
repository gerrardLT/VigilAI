"""Investigation decision helpers for reward-opportunity candidates."""

from __future__ import annotations


def decide_next_investigation_actions(
    candidate: dict[str, object],
    evidence_bundle: dict[str, object],
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []

    if not evidence_bundle.get("time_snippets"):
        actions.append(
            {
                "action_type": "search_query",
                "query": f"{candidate['title']} rules deadline reward",
                "reason": "time evidence missing",
            }
        )

    if not evidence_bundle.get("rule_snippets"):
        actions.append(
            {
                "action_type": "open_rule_page",
                "target_url": candidate["source_url"],
                "reason": "rule detail missing",
            }
        )

    return actions

