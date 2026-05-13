"""Opportunity merge helpers for reward-opportunity discovery."""

from __future__ import annotations


def merge_duplicate_candidates(candidate_ids: list[str]) -> dict[str, object]:
    return {
        "canonical_candidate_id": candidate_ids[0] if candidate_ids else None,
        "merged_ids": candidate_ids,
    }

