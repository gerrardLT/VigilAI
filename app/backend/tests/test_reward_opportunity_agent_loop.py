"""Investigation loop tests for the reward-opportunity bounded context."""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reward_opportunity.agent_loop import run_investigation_cycle  # noqa: E402


def test_investigation_cycle_requests_follow_up_when_time_missing():
    result = run_investigation_cycle(
        candidate={
            "title": "Invite 3 friends and get $25",
            "source_url": "https://example.com/post/1",
        },
        evidence_bundle={
            "reward_snippets": ["receive a $25 cash reward"],
            "action_snippets": ["invite three friends"],
            "time_snippets": [],
        },
        max_rounds=2,
        evaluator_client=lambda _bundle, evidence: {
            "is_target_opportunity": True,
            "opportunity_type": "invite_reward",
            "reward_type": "cash",
            "stage_label": "needs_more_evidence",
            "confidence": 0.8,
            "evidence_sufficiency": "partial",
            "missing_evidence": ["time_or_deadline"],
            "risk_flags": ["deadline_missing"],
            "required_next_actions": ["search_deadline"],
            "quoted_evidence_ids": [evidence[0]["id"]],
            "reasoning_brief": "Reward and action evidence are present.",
        },
    )

    assert result["status"] in {"classified", "needs_follow_up"}
    assert len(result["actions"]) >= 1
    assert result["actions"][0]["action_type"] in {"search_query", "open_link", "open_rule_page"}
