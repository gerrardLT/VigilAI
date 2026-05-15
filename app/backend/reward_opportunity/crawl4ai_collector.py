"""Crawl4AI-backed collector primitives for reward-opportunity discovery."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from urllib.parse import urlparse
from typing import Any

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


def build_crawl4ai_config(
    mode: str,
    max_depth: int = 1,
    use_llm_extraction: bool = False,
) -> CrawlerRunConfig:
    extraction_strategy: Any = None
    if use_llm_extraction:
        from crawl4ai.extraction_strategy import LLMExtractionStrategy

        extraction_strategy = LLMExtractionStrategy(
            instruction="Extract reward, action, deadline, eligibility, FAQ, and rule-related content.",
            extraction_type="block",
        )

    deep_crawl_strategy = None
    if mode in {"list", "detail", "rule", "faq", "follow_up"}:
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
        )

    markdown_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.42),
    )

    return CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_strategy,
        extraction_strategy=extraction_strategy,
        markdown_generator=markdown_generator,
        page_timeout=45000,
        wait_until="networkidle",
        wait_for_images=False,
        remove_overlay_elements=True,
        remove_consent_popups=True,
        scan_full_page=mode in {"detail", "rule", "faq", "follow_up"},
        verbose=False,
    )


def normalize_raw_document(
    source_feed: dict[str, Any],
    payload: dict[str, Any],
    *,
    mode: str,
    crawl_job_id: str | None = None,
) -> dict[str, Any]:
    source_url = str(payload.get("source_url") or payload.get("url") or source_feed.get("entry_url") or "").strip()
    title = str(payload.get("title") or source_url or "Untitled reward source").strip()
    body = str(payload.get("body") or payload.get("content") or "").strip()
    metadata = dict(payload.get("metadata") or {})
    metadata.setdefault("mode", mode)
    metadata.setdefault("external_links", list(payload.get("external_links") or []))
    metadata.setdefault("internal_links", list(payload.get("internal_links") or []))
    return {
        "crawl_job_id": crawl_job_id,
        "source_feed_id": source_feed.get("id"),
        "source_platform": payload.get("source_platform") or source_feed.get("source_platform") or source_feed.get("source_type") or "web",
        "source_type": source_feed.get("source_type"),
        "source_url": source_url,
        "canonical_url": payload.get("canonical_url") or source_url,
        "title": title,
        "body": body,
        "summary": payload.get("summary") or (body[:240] if body else None),
        "published_at": payload.get("published_at"),
        "metadata": metadata,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def collect_documents(
    source_feed: dict[str, Any],
    *,
    mode: str = "list",
    target_urls: list[str] | None = None,
) -> list[dict[str, Any]]:
    from config import REWARD_AGENT_ALLOW_MOCK_DOCUMENTS

    config = dict(source_feed.get("config") or {})
    allow_mock_fallback = bool(config.get("allow_mock_fallback", REWARD_AGENT_ALLOW_MOCK_DOCUMENTS))
    documents = list(config.get("mock_documents") or [])
    if target_urls:
        filtered = [doc for doc in documents if str(doc.get("source_url") or doc.get("url") or "") in set(target_urls)]
        documents = filtered or documents

    urls = _build_target_urls(source_feed, mode=mode, target_urls=target_urls)
    crawled_documents: list[dict[str, Any]] = []
    if urls:
        try:
            crawled_documents = asyncio.run(_crawl_documents(source_feed, urls=urls, mode=mode))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                crawled_documents = loop.run_until_complete(_crawl_documents(source_feed, urls=urls, mode=mode))
            finally:
                loop.close()
        except Exception:
            crawled_documents = []

    if crawled_documents:
        return crawled_documents

    if documents and allow_mock_fallback:
        return [normalize_raw_document(source_feed, payload, mode=mode) for payload in documents]

    target_url = (urls or target_urls or [source_feed.get("entry_url") or ""])[0]
    return [
        normalize_raw_document(
            source_feed,
            {
                "source_url": target_url,
                "title": source_feed.get("name") or "Reward source",
                "body": "",
                "external_links": [],
                "internal_links": [],
            },
            mode=mode,
        )
    ]


def _build_target_urls(source_feed: dict[str, Any], *, mode: str, target_urls: list[str] | None) -> list[str]:
    if target_urls:
        return list(dict.fromkeys(url for url in target_urls if url))
    entry_url = str(source_feed.get("entry_url") or "").strip()
    if not entry_url:
        return []
    if mode == "list":
        return [entry_url]
    return [entry_url]


async def _crawl_documents(source_feed: dict[str, Any], *, urls: list[str], mode: str) -> list[dict[str, Any]]:
    browser_config = BrowserConfig(headless=True, verbose=False)
    max_depth = 1 if mode == "list" else 0
    crawl_config = build_crawl4ai_config(mode=mode, max_depth=max_depth, use_llm_extraction=False)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(urls, config=crawl_config)

    normalized: list[dict[str, Any]] = []
    for result in results:
        if not getattr(result, "success", False):
            continue

        markdown = getattr(result, "markdown", None)
        body = (
            getattr(markdown, "fit_markdown", None)
            or getattr(markdown, "raw_markdown", None)
            or ""
        ).strip()
        links = getattr(result, "links", {}) or {}
        internal_links = [item.get("href") for item in links.get("internal", []) if item.get("href")]
        external_links = [item.get("href") for item in links.get("external", []) if item.get("href")]
        title = (
            (getattr(result, "metadata", {}) or {}).get("title")
            or _derive_title_from_markdown(body)
            or str(getattr(result, "url", "")).strip()
        )
        normalized.append(
            normalize_raw_document(
                source_feed,
                {
                    "source_platform": source_feed.get("source_platform") or source_feed.get("source_type") or "web",
                    "source_url": getattr(result, "url", None),
                    "canonical_url": getattr(result, "url", None),
                    "title": title,
                    "body": body,
                    "summary": body[:240] if body else None,
                    "external_links": external_links,
                    "internal_links": internal_links,
                    "metadata": {
                        "crawler_mode": mode,
                        "result_metadata": getattr(result, "metadata", {}) or {},
                    },
                },
                mode=mode,
            )
        )

        if mode == "list":
            detail_links = _select_reward_like_links(
                base_url=str(getattr(result, "url", "") or ""),
                candidate_links=internal_links + external_links,
                max_links=int((source_feed.get("config") or {}).get("max_detail_urls", 4)),
            )
            if detail_links:
                normalized.extend(await _crawl_documents(source_feed, urls=detail_links, mode="detail"))
    return normalized


def _select_reward_like_links(*, base_url: str, candidate_links: list[str], max_links: int) -> list[str]:
    base_domain = urlparse(base_url).netloc.lower()
    keywords = ("reward", "bonus", "bounty", "airdrop", "invite", "campaign", "quest", "task", "referral", "faq", "rule")
    selected: list[str] = []
    for link in candidate_links:
        parsed = urlparse(link)
        netloc = parsed.netloc.lower()
        text = f"{parsed.path} {parsed.query}".lower()
        if base_domain and netloc and netloc != base_domain and not any(word in text for word in keywords):
            continue
        if any(word in text for word in keywords) and link not in selected:
            selected.append(link)
        if len(selected) >= max_links:
            break
    return selected


def _derive_title_from_markdown(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return "Untitled reward source"
