"""Repository tests for the reward-opportunity bounded context."""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reward_opportunity.repository import RewardOpportunityRepository  # noqa: E402


def test_repository_creates_reward_opportunity_tables(tmp_path):
    repository = RewardOpportunityRepository(str(tmp_path / "reward.db"))
    repository.ensure_schema()

    stats = repository.get_overview_stats()

    assert stats["source_count"] == 0
    assert stats["opportunity_count"] == 0


def test_repository_persists_candidate_and_investigation(tmp_path):
    repository = RewardOpportunityRepository(str(tmp_path / "reward.db"))
    repository.ensure_schema()

    candidate_id = repository.create_recall_candidate(
        {
            "source_platform": "x",
            "source_url": "https://example.com/post/1",
            "title": "Invite friends and earn $20",
            "recall_label": "suspected_invite_reward",
            "recall_reason": "matched invite + reward pattern",
        }
    )
    run_id = repository.create_investigation_run(
        {
            "candidate_id": candidate_id,
            "status": "running",
            "current_round": 1,
        }
    )
    repository.append_investigation_action(
        run_id,
        {
            "action_type": "open_link",
            "target_url": "https://example.com/promo",
            "status": "completed",
        },
    )

    loaded = repository.get_investigation_run(run_id)

    assert loaded["candidate_id"] == candidate_id
    assert loaded["actions"][0]["action_type"] == "open_link"

