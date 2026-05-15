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
    assert candidate["opportunity_type"] == "invite_reward"
    assert candidate["needs_detail_fetch"] is True


def test_evaluator_returns_high_value_for_clear_reward():
    result = evaluate_evidence_bundle(
        {
            "title": "Invite 3 friends and get $25",
            "reward_snippets": ["receive a $25 cash reward"],
            "action_snippets": ["invite three friends"],
            "time_snippets": ["Campaign ends May 31"],
            "rule_snippets": ["Full rules are listed on the campaign page."],
            "eligibility_snippets": ["New users in the US only."],
            "source_platform": "web",
        }
    )

    assert result["ai_stage_2_label"] == "高价值"
    assert result["is_target_opportunity"] is True
    assert result["reward_type"] == "cash"
    assert result["needs_investigation"] is False


def test_evaluator_returns_follow_up_when_key_evidence_missing():
    result = evaluate_evidence_bundle(
        {
            "title": "Complete missions to earn rewards",
            "reward_snippets": ["earn rewards after mission completion"],
            "action_snippets": ["complete three onboarding missions"],
            "time_snippets": [],
            "rule_snippets": [],
            "eligibility_snippets": [],
            "source_platform": "web",
            "external_links": ["https://example.com/rules"],
        }
    )

    assert result["ai_stage_2_label"] == "待补证据"
    assert "open_rule_page" in result["recommended_next_actions"]
    assert "find_eligibility" in result["recommended_next_actions"]
    assert result["needs_investigation"] is True
