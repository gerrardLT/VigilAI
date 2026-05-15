"""Scout discovery tests for reward-opportunity source expansion."""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reward_opportunity.scout import discover_source_candidates  # noqa: E402


def test_discover_source_candidates_dedupes_existing_feeds():
    existing = [
        {
            "name": "Existing Reddit Feed",
            "entry_url": "https://reddit.com/r/airdrops",
        }
    ]

    def fake_search(query: str) -> list[str]:
        if "reddit" in query:
            return ["https://reddit.com/r/airdrops", "https://github.com/example/bounties"]
        return ["https://discord.com/channels/example/rewards"]

    result = discover_source_candidates(existing, search_fn=fake_search)

    assert all(item["entry_url"] != "https://reddit.com/r/airdrops" for item in result)
    assert any(item["source_platform"] == "github" for item in result)
    assert any(item["source_platform"] == "discord" for item in result)


def test_discover_source_candidates_merges_same_domain_path_pattern():
    def fake_search(_query: str) -> list[str]:
        return [
            "https://github.com/example/bounties",
            "https://github.com/example/bounties?tab=readme",
        ]

    result = discover_source_candidates([], search_fn=fake_search)

    assert len(result) == 1
    assert result[0]["dedupe_key"] == "github.com|example/bounties"
    assert len(result[0]["matched_urls"]) == 2
