"""Broad recall logic for reward-opportunity candidates."""

from __future__ import annotations


REWARD_PATTERNS = [
    ("suspected_invite_reward", ("invite", "reward")),
    ("suspected_registration_reward", ("register", "reward")),
    ("suspected_task_reward", ("task", "reward")),
]


def recall_candidate_from_document(document: dict[str, str]) -> dict[str, str] | None:
    haystack = f"{document.get('title', '')} {document.get('body', '')}".lower()
    for label, (left, right) in REWARD_PATTERNS:
        if left in haystack and right in haystack:
            return {
                "source_platform": document["source_platform"],
                "source_url": document["source_url"],
                "title": document["title"],
                "recall_label": label,
                "recall_reason": f"matched pattern: {left}+{right}",
            }
    return None

