"""
Shared live-first marketplace adapter helpers for product selection.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import (
    SELECTION_LIVE_FETCH_ENABLED,
    SELECTION_LIVE_FIRECRAWL_ENABLED,
    SELECTION_LIVE_HTTP_ENABLED,
    SELECTION_LIVE_MAX_ITEMS_PER_PLATFORM,
    SELECTION_LIVE_TIMEOUT_SECONDS,
    USER_AGENTS,
)
from utils.api_key_pool import ApiKeyPool

logger = logging.getLogger(__name__)

try:
    from firecrawl import FirecrawlApp
except ImportError:  # pragma: no cover
    FirecrawlApp = None


@dataclass(frozen=True)
class LiveSearchDocument:
    url: str
    html: str = ""
    markdown: str = ""
    source_channel: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.html.strip() or self.markdown.strip())


@dataclass(frozen=True)
class ExtractedListing:
    title: str
    url: str
    price: float | None
    source_channel: str
    snippet: str = ""


class MarketplaceSearchAdapter(ABC):
    platform = ""
    supported_hosts: tuple[str, ...] = ()
    product_url_patterns: tuple[str, ...] = ()
    search_url_template = ""

    def __init__(
        self,
        *,
        live_fetch_enabled: bool | None = None,
        firecrawl_enabled: bool | None = None,
        http_enabled: bool | None = None,
        max_live_items: int | None = None,
        request_timeout: float | None = None,
    ) -> None:
        self.live_fetch_enabled = (
            SELECTION_LIVE_FETCH_ENABLED if live_fetch_enabled is None else live_fetch_enabled
        )
        self.firecrawl_enabled = (
            SELECTION_LIVE_FIRECRAWL_ENABLED if firecrawl_enabled is None else firecrawl_enabled
        )
        self.http_enabled = SELECTION_LIVE_HTTP_ENABLED if http_enabled is None else http_enabled
        self.max_live_items = max(1, max_live_items or SELECTION_LIVE_MAX_ITEMS_PER_PLATFORM)
        self.request_timeout = request_timeout or SELECTION_LIVE_TIMEOUT_SECONDS
        self._api_key_pool = ApiKeyPool.get_instance()

    def search_products(
        self,
        query_text: str,
        *,
        query_type: str,
        rendered_snapshot_html: str | None = None,
        rendered_snapshot_path: str | None = None,
        detail_snapshot_htmls: list[str] | None = None,
        detail_snapshot_manifest_path: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.live_fetch_enabled:
            try:
                live_results = self._search_live_products(query_text, query_type=query_type)
            except Exception as exc:
                logger.warning(
                    "%s live fetch failed for %r (%s): %s",
                    self.platform,
                    query_text,
                    query_type,
                    exc,
                )
            else:
                if live_results:
                    return live_results

        return self._search_fallback_products(query_text, query_type=query_type)

    def _search_live_products(self, query_text: str, *, query_type: str) -> list[dict[str, Any]]:
        target_url = self._resolve_target_url(query_text, query_type=query_type)
        if not target_url:
            return []

        document = self._fetch_live_document(target_url)
        if document is None:
            return []

        candidates = self._extract_candidates(document, default_url=target_url)
        if not candidates:
            return []

        listings: list[dict[str, Any]] = []
        candidate_count = len(candidates)
        for rank, candidate in enumerate(candidates[: self.max_live_items], start=1):
            listings.append(
                self._build_live_product(
                    candidate,
                    query_text=query_text,
                    query_type=query_type,
                    rank=rank,
                    candidate_count=candidate_count,
                )
            )
        return listings

    def _resolve_target_url(self, query_text: str, *, query_type: str) -> str:
        normalized_query = query_text.strip()
        if not normalized_query:
            return ""

        if query_type == "listing_url":
            return normalized_query if self._looks_like_supported_url(normalized_query) else ""

        return self.search_url_template.format(query=quote_plus(normalized_query))

    def _fetch_live_document(self, target_url: str) -> LiveSearchDocument | None:
        fetchers = []
        if self.firecrawl_enabled:
            fetchers.append(self._fetch_via_firecrawl)
        if self.http_enabled:
            fetchers.append(self._fetch_via_http)

        for fetcher in fetchers:
            try:
                document = fetcher(target_url)
            except Exception as exc:
                logger.info("%s fetcher %s failed for %s: %s", self.platform, fetcher.__name__, target_url, exc)
                continue
            if document and document.has_content:
                return document

        return None

    def _fetch_via_firecrawl(self, target_url: str) -> LiveSearchDocument | None:
        if FirecrawlApp is None or not self._api_key_pool.has_keys:
            return None

        api_key = self._api_key_pool.get_next_key()
        if not api_key:
            return None

        try:
            client = FirecrawlApp(api_key=api_key)
            result = client.scrape(target_url, formats=["markdown", "html"])
            self._api_key_pool.report_success(api_key)
        except Exception as exc:
            self._api_key_pool.report_error(api_key, str(exc))
            raise

        html = ""
        markdown = ""
        if isinstance(result, dict):
            html = str(result.get("html") or "")
            markdown = str(result.get("markdown") or "")
        else:
            html = str(getattr(result, "html", "") or "")
            markdown = str(getattr(result, "markdown", "") or "")

        return LiveSearchDocument(
            url=target_url,
            html=html,
            markdown=markdown,
            source_channel="firecrawl",
        )

    def _fetch_via_http(self, target_url: str) -> LiveSearchDocument | None:
        headers = {
            "User-Agent": random.choice(USER_AGENTS) if USER_AGENTS else "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        with httpx.Client(
            headers=headers,
            timeout=self.request_timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(target_url)
            response.raise_for_status()
            html = response.text or ""

        return LiveSearchDocument(
            url=str(response.url),
            html=html,
            markdown="",
            source_channel="http",
        )

    def _extract_candidates(
        self,
        document: LiveSearchDocument,
        *,
        default_url: str,
    ) -> list[ExtractedListing]:
        candidates: list[ExtractedListing] = []
        seen_urls: set[str] = set()

        def add_candidate(title: str, raw_url: str, price: float | None, snippet: str = "") -> None:
            normalized_url = self._normalize_candidate_url(raw_url, default_url=default_url)
            if not normalized_url or normalized_url in seen_urls or not self._is_product_url(normalized_url):
                return

            cleaned_title = self._clean_candidate_text(title)
            cleaned_snippet = self._clean_candidate_text(snippet)
            if not cleaned_title and not cleaned_snippet:
                return
            if cleaned_title and self._looks_like_noise(cleaned_title):
                return

            seen_urls.add(normalized_url)
            candidates.append(
                ExtractedListing(
                    title=cleaned_title,
                    url=normalized_url,
                    price=price,
                    source_channel=document.source_channel,
                    snippet=cleaned_snippet,
                )
            )

        if document.html:
            soup = BeautifulSoup(document.html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                context_node = anchor.parent if anchor.parent is not None else anchor
                context_text = context_node.get_text(" ", strip=True)
                add_candidate(
                    title=anchor.get_text(" ", strip=True),
                    raw_url=anchor["href"],
                    price=self._extract_price(context_text),
                    snippet=context_text,
                )

        if document.markdown:
            for title, url in re.findall(r"\[([^\]]{2,200})\]\(([^)]+)\)", document.markdown):
                add_candidate(
                    title=title,
                    raw_url=url,
                    price=self._extract_price(title),
                    snippet=title,
                )

            for url in re.findall(r"https?://[^\s)>\"]+", document.markdown):
                add_candidate(
                    title="",
                    raw_url=url,
                    price=self._extract_price(document.markdown),
                    snippet=document.markdown[:200],
                )

        if not candidates and self._is_product_url(default_url):
            add_candidate(
                title=self._extract_page_title(document),
                raw_url=default_url,
                price=self._extract_price(f"{document.html}\n{document.markdown}"),
                snippet=document.markdown[:200] or document.html[:200],
            )

        return candidates

    def _build_live_product(
        self,
        candidate: ExtractedListing,
        *,
        query_text: str,
        query_type: str,
        rank: int,
        candidate_count: int,
    ) -> dict[str, Any]:
        observed_price = candidate.price
        price_mid = round(observed_price or self._estimate_mid_price(query_text, rank), 2)
        price_low = round(max(1.0, price_mid * 0.82), 2)
        price_high = round(price_mid * 1.18, 2)

        demand_score = 64.0 + max(0, 4 - rank) * 5 + min(8.0, candidate_count * 1.5)
        if query_type == "listing_url":
            demand_score += 4

        competition_score = 34.0 + min(30.0, candidate_count * 3.5)
        price_fit_score = 58.0 + (10.0 if 20 <= price_mid <= 199 else 6.0)
        risk_score = 24.0
        risk_tags: list[str] = ["需人工复核实时库存"]

        if observed_price is None:
            risk_score += 10
            risk_tags.append("价格信号弱")
        if candidate.source_channel == "http":
            risk_score += 4
            risk_tags.append("页面结构可能变化")
        if not candidate.title:
            risk_score += 5
            risk_tags.append("标题提取不完整")

        reliability = 0.82 if candidate.source_channel == "firecrawl" else 0.68
        if observed_price is None:
            reliability -= 0.12

        return {
            "platform": self.platform,
            "platform_item_id": self._extract_item_id(candidate.url),
            "title": candidate.title or self._build_default_live_title(query_text, rank),
            "image_url": None,
            "category_path": self._category_path(candidate.title or query_text),
            "price_low": price_low,
            "price_mid": price_mid,
            "price_high": price_high,
            "demand_score": round(min(demand_score, 90.0), 2),
            "competition_score": round(min(competition_score, 88.0), 2),
            "price_fit_score": round(min(price_fit_score, 89.0), 2),
            "risk_score": round(min(risk_score, 82.0), 2),
            "risk_tags": risk_tags,
            "source_urls": [candidate.url],
            "signals": [
                {
                    "platform": self.platform,
                    "signal_type": "live_search_rank",
                    "value_json": {
                        "query_text": query_text,
                        "rank": rank,
                        "candidate_count": candidate_count,
                        "channel": candidate.source_channel,
                    },
                    "sample_size": max(candidate_count, 1),
                    "freshness": "live",
                    "reliability": round(max(reliability, 0.45), 2),
                },
                {
                    "platform": self.platform,
                    "signal_type": "live_price_snapshot",
                    "value_json": {
                        "observed_price": observed_price,
                        "price_low": price_low,
                        "price_mid": price_mid,
                        "price_high": price_high,
                    },
                    "sample_size": 1,
                    "freshness": "live",
                    "reliability": round(max(reliability - 0.04, 0.4), 2),
                },
                {
                    "platform": self.platform,
                    "signal_type": "data_source",
                    "value_json": {"mode": "live", "channel": candidate.source_channel},
                    "sample_size": 1,
                    "freshness": "live",
                    "reliability": round(max(reliability, 0.45), 2),
                },
            ],
        }

    @staticmethod
    def _seed(value: str) -> int:
        return int(hashlib.md5(value.encode("utf-8")).hexdigest()[:8], 16) % 10000

    def _estimate_mid_price(self, query_text: str, rank: int) -> float:
        seed = self._seed(f"{self.platform}:{query_text}:{rank}")
        return float(29 + (seed % 18) * 5)

    def _normalize_candidate_url(self, raw_url: str, *, default_url: str) -> str:
        raw = (raw_url or "").strip()
        if not raw:
            return ""
        if raw.startswith("//"):
            raw = f"https:{raw}"
        normalized = urljoin(default_url, raw)
        parsed = urlparse(normalized)
        query = parse_qs(parsed.query)
        for key in ("url", "target", "redirect", "redirectUrl"):
            target = query.get(key, [None])[0]
            if target and target.startswith("http"):
                normalized = target
                break
        return normalized

    def _extract_item_id(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        item_id = query.get("id", [None])[0]
        if item_id:
            return item_id

        for segment in reversed([part for part in parsed.path.split("/") if part]):
            cleaned = re.sub(r"[^A-Za-z0-9_-]", "", segment)
            if cleaned and any(char.isdigit() for char in cleaned):
                return cleaned

        return f"{self.platform}-{hashlib.md5(url.encode('utf-8')).hexdigest()[:12]}"

    def _looks_like_supported_url(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(token in host for token in self.supported_hosts)

    def _is_product_url(self, url: str) -> bool:
        if not self._looks_like_supported_url(url):
            return False
        return any(re.search(pattern, url, flags=re.IGNORECASE) for pattern in self.product_url_patterns)

    def _extract_page_title(self, document: LiveSearchDocument) -> str:
        if document.html:
            soup = BeautifulSoup(document.html, "html.parser")
            if soup.title and soup.title.string:
                return self._clean_candidate_text(soup.title.string)
        if document.markdown:
            for line in document.markdown.splitlines():
                if line.strip().startswith("#"):
                    return self._clean_candidate_text(line.strip("# ").strip())
        return ""

    def _build_default_live_title(self, query_text: str, rank: int) -> str:
        return f"{query_text} 实时候选 {rank}"

    @staticmethod
    def _clean_candidate_text(value: str) -> str:
        cleaned = unescape((value or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip(" -|丨/·•[]()<>:：;；,，")
        return cleaned[:120]

    @staticmethod
    def _looks_like_noise(value: str) -> bool:
        normalized = value.lower()
        noise_tokens = (
            "login",
            "sign in",
            "open app",
            "download",
            "taobao",
            "goofish",
            "闲鱼",
            "淘宝",
            "搜索",
            "打开",
        )
        return len(normalized) < 4 or any(token == normalized for token in noise_tokens)

    @staticmethod
    def _extract_price(value: str) -> float | None:
        text = value or ""
        for pattern in (
            r"(?:¥|￥|RMB|CNY)\s*([0-9]+(?:\.[0-9]{1,2})?)",
            r"([0-9]+(?:\.[0-9]{1,2})?)\s*元",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @abstractmethod
    def _search_fallback_products(self, query_text: str, *, query_type: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def _category_path(query_text: str) -> str:
        raise NotImplementedError
