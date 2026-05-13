"""Recall and evaluator tests for the reward-opportunity bounded context."""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reward_opportunity.evaluator import evaluate_evidence_bundle  # noqa: E402
from reward_opportunity.recall import recall_candidate_from_document  # noqa: E402


def test_recall_flags_invite_reward_copy():
    candidate = recall_candidate_from_document(
        {
            "title": "Invite 3 friends and get $25",
            "body": "Register today, invite three friends, and receive a $25 cash reward.",
            "source_url": "https://example.com/post/1",
            "source_platform": "web",
        }
    )

    assert candidate is not None
    assert candidate["recall_label"] == "suspected_invite_reward"


def test_evaluator_returns_high_value_for_clear_reward():
    result = evaluate_evidence_bundle(
        {
            "title": "Invite 3 friends and get $25",
            "reward_snippets": ["receive a $25 cash reward"],
            "action_snippets": ["invite three friends"],
            "time_snippets": ["Campaign ends May 31"],
            "source_platform": "web",
        }
    )

    assert result["ai_stage_2_label"] in {"高价值", "可跟"}
    assert result["needs_investigation"] is False
