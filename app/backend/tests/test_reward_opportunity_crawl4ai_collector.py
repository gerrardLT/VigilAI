"""Tests for the Crawl4AI-backed reward-opportunity collector primitives."""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reward_opportunity.crawl4ai_collector import build_crawl4ai_config  # noqa: E402


def test_build_crawl4ai_config_for_detail_page():
    config = build_crawl4ai_config(
        mode="detail",
        max_depth=1,
        use_llm_extraction=False,
    )

    assert config is not None
    assert (
        getattr(config, "deep_crawl_strategy", None) is not None
        or getattr(config, "extraction_strategy", None) is not None
    )
