"""Investigation decision helpers for reward-opportunity candidates."""

from __future__ import annotations


def decide_next_investigation_actions(
    candidate: dict[str, object],
    evidence_bundle: dict[str, object],
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    title = str(candidate.get("title") or "").strip()
    source_url = str(candidate.get("source_url") or "").strip()
    external_links = list(evidence_bundle.get("external_links") or [])
    prioritized_links = list(evidence_bundle.get("priority_links") or [])
    rule_like_link = next((link for link in prioritized_links if link), source_url)
    faq_like_link = next((link for link in external_links if any(word in link.lower() for word in ("faq", "help", "support"))), source_url)

    if not evidence_bundle.get("time_snippets"):
        actions.append(
            {
                "action_type": "search_query",
                "query": f"{title} rules deadline reward".strip(),
                "reason": "time evidence missing",
                "status": "planned",
            }
        )

    if not evidence_bundle.get("rule_snippets"):
        actions.append(
            {
                "action_type": "open_rule_page",
                "target_url": rule_like_link,
                "reason": "rule detail missing",
                "status": "planned",
            }
        )

    if not evidence_bundle.get("reward_snippets"):
        actions.append(
            {
                "action_type": "open_faq",
                "target_url": faq_like_link,
                "reason": "reward detail missing",
                "status": "planned",
            }
        )

    if prioritized_links:
        actions.append(
            {
                "action_type": "follow_external_link",
                "target_url": prioritized_links[0],
                "reason": "source contains external reference",
                "status": "planned",
            }
        )

    return actions
