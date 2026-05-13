"""Crawl4AI-backed collector primitives for reward-opportunity discovery."""

from __future__ import annotations

from typing import Any

from crawl4ai import CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy


def build_crawl4ai_config(
    mode: str,
    max_depth: int = 1,
    use_llm_extraction: bool = False,
) -> CrawlerRunConfig:
    extraction_strategy: Any = None
    if use_llm_extraction:
        from crawl4ai.extraction_strategy import LLMExtractionStrategy

        extraction_strategy = LLMExtractionStrategy(
            instruction="Extract reward, action, deadline, eligibility, and rule-related content.",
            extraction_type="block",
        )

    deep_crawl_strategy = None
    if mode in {"list", "detail"}:
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
        )

    return CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_strategy,
        extraction_strategy=extraction_strategy,
    )

