"""
Shared live-search helpers for product-selection marketplace adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from config import (
    PRODUCT_SELECTION_BROWSER_COOKIES_PATH,
    PRODUCT_SELECTION_LIVE_COOKIE_DOMAINS,
    PRODUCT_SELECTION_LIVE_ENABLED,
    PRODUCT_SELECTION_LIVE_RESULT_LIMIT,
    PRODUCT_SELECTION_LIVE_TIMEOUT_SECONDS,
    USER_AGENTS,
)
from utils.api_key_pool import ApiKeyPool

logger = logging.getLogger(__name__)

try:
    from firecrawl import FirecrawlApp

    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False


SELLER_NAME_PATTERNS = (
    re.compile("(?:\u5e97\u94fa|\u5356\u5bb6|\u5546\u5bb6)[:\uff1a\\s]+([^\\s|,\uff0c]{2,40})"),
    re.compile("(\u65d7\u8230\u5e97|\u5b98\u65b9\u5e97|\u54c1\u724c\u5e97|\u4e13\u8425\u5e97|\u4e13\u5356\u5e97)"),
)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]{2,160})\]\((https?://[^)]+)\)")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
GENERIC_TITLE_RE = re.compile(r"(goofish|search|taobao|xianyu)", re.IGNORECASE)
SHELL_MARKERS = ("boneClass_cardListWrapper", "__ICE_APP_CONTEXT__", 'renderMode":"CSR', "p_search-index.js")
CAPTCHA_MARKERS = (
    "action=captcha",
    "punish?x5secdata=",
    "x5secdata=",
    "j_middleware_frame_widget",
    "purecaptcha",
)
GENERIC_LISTING_TEXT_RE = re.compile(
    "^(?:view details|details|buy now|open|click|item|listing|shop now|\u7acb\u5373\u8d2d\u4e70|\u67e5\u770b\u8be6\u60c5|\u5546\u54c1\u8be6\u60c5|\u8fdb\u5165\u5e97\u94fa)$",
    re.IGNORECASE,
)
ENTERPRISE_MARKERS = (
    "\u4f01\u4e1a\u5e97",
    "\u65d7\u8230\u5e97",
    "\u5b98\u65b9",
    "\u5929\u732b",
    "\u54c1\u724c\u5e97",
    "\u4e13\u8425\u5e97",
    "\u4e13\u5356\u5e97",
)
PERSONAL_MARKERS = ("\u4e2a\u4eba", "\u81ea\u7528", "\u95f2\u7f6e", "\u8f6c\u8ba9")


@dataclass
class LiveListing:
    title: str
    url: str
    snippet: str
    price_low: float | None = None
    price_mid: float | None = None
    price_high: float | None = None
    sales_volume: int | None = None
    seller_count: int | None = None
    seller_type: str | None = None
    seller_name: str | None = None


class LiveMarketplaceAdapter:
    platform = ""
    search_url_template = ""
    result_limit = PRODUCT_SELECTION_LIVE_RESULT_LIMIT

    def __init__(self, *, live_enabled: bool | None = None) -> None:
        self.live_enabled = PRODUCT_SELECTION_LIVE_ENABLED if live_enabled is None else live_enabled
        self._api_key_pool = ApiKeyPool.get_instance()
        self._last_failure_reason: str | None = None
        self._last_extraction_stats: dict[str, Any] = {}
        self.browser_cookies_path = PRODUCT_SELECTION_BROWSER_COOKIES_PATH
        self.live_cookie_domains = PRODUCT_SELECTION_LIVE_COOKIE_DOMAINS

    def search_marketplace(
        self,
        query_text: str,
        *,
        query_type: str,
        rendered_snapshot_html: str | None = None,
        request_cookies: dict[str, str] | None = None,
        cookie_file: str | None = None,
    ) -> dict[str, Any]:
        if not query_text.strip():
            return self._empty_result(
                query_type=query_type,
                failure_reason="empty_query",
                notes=["Query text was empty after normalization."],
                source="empty_query",
            )

        listings = self._search_live(
            query_text,
            rendered_snapshot_html=rendered_snapshot_html,
            request_cookies=request_cookies,
            cookie_file=cookie_file,
        )
        if listings:
            return {
                "platform": self.platform,
                "mode": "live",
                "items": [
                    self._listing_to_candidate(query_text, listing, rank, source_mode="live")
                    for rank, listing in enumerate(listings, start=1)
                ],
                "diagnostics": {
                    "platform": self.platform,
                    "query_type": query_type,
                    "live_enabled": self.live_enabled,
                    "live_result_count": len(listings),
                    "fallback_reason": None,
                    "notes": ["Live marketplace extraction succeeded."],
                    "extraction_stats": self._last_extraction_stats,
                },
            }

        failure_reason = self._last_failure_reason or "live_results_unavailable"
        return {
            "platform": self.platform,
            "mode": "failed",
            "items": [],
            "diagnostics": {
                "platform": self.platform,
                "query_type": query_type,
                "live_enabled": self.live_enabled,
                "live_result_count": 0,
                "fallback_reason": failure_reason,
                "notes": self._failure_notes(failure_reason),
                "extraction_stats": self._last_extraction_stats,
            },
        }

    def search_products(
        self,
        query_text: str,
        *,
        query_type: str,
        rendered_snapshot_html: str | None = None,
        request_cookies: dict[str, str] | None = None,
        cookie_file: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.search_marketplace(
            query_text,
            query_type=query_type,
            rendered_snapshot_html=rendered_snapshot_html,
            request_cookies=request_cookies,
            cookie_file=cookie_file,
        )["items"]

    def _search_live(
        self,
        query_text: str,
        *,
        rendered_snapshot_html: str | None = None,
        request_cookies: dict[str, str] | None = None,
        cookie_file: str | None = None,
    ) -> list[LiveListing]:
        self._last_failure_reason = None
        self._last_extraction_stats = self._empty_extraction_stats(source="not_started")
        search_url = self.search_url_template.format(query=quote(query_text))

        try:
            if rendered_snapshot_html:
                listings = self._extract_listings(
                    rendered_snapshot_html,
                    query_text,
                    base_url=search_url,
                    source="rendered_snapshot",
                )
                if listings:
                    return listings[: self.result_limit]
                if self._last_failure_reason:
                    return []

            if not self.live_enabled:
                self._last_failure_reason = "live_disabled"
                self._last_extraction_stats["source"] = "live_disabled"
                return []

            html = self._fetch_http(
                search_url,
                request_cookies=request_cookies,
                cookie_file=cookie_file,
            )
            listings = self._extract_listings(html, query_text, base_url=search_url, source="http")
            if listings:
                return listings[: self.result_limit]

            firecrawl_payload = self._fetch_firecrawl(search_url)
            if firecrawl_payload:
                listings = self._extract_listings(
                    f"{firecrawl_payload.get('markdown') or ''}\n{firecrawl_payload.get('html') or ''}",
                    query_text,
                    base_url=search_url,
                    source="firecrawl",
                )
                if listings:
                    return listings[: self.result_limit]

            if self._last_failure_reason is None:
                self._last_failure_reason = "no_structured_results_extracted"
        except Exception:
            logger.exception("Live %s search failed for query '%s'", self.platform, query_text)
            self._last_failure_reason = "live_fetch_failed"

        return []

    def _fetch_http(
        self,
        url: str,
        *,
        request_cookies: dict[str, str] | None = None,
        cookie_file: str | None = None,
    ) -> str:
        cookies = self._resolve_request_cookies(url, request_cookies=request_cookies, cookie_file=cookie_file)
        response = httpx.get(
            url,
            timeout=PRODUCT_SELECTION_LIVE_TIMEOUT_SECONDS,
            follow_redirects=True,
            cookies=cookies or None,
            headers={
                "user-agent": USER_AGENTS[0] if USER_AGENTS else "Mozilla/5.0",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        response.raise_for_status()
        return response.text

    def _fetch_firecrawl(self, url: str) -> dict[str, Any] | None:
        if not FIRECRAWL_AVAILABLE or not self._api_key_pool.has_keys:
            return None

        api_key = self._api_key_pool.get_next_key()
        if not api_key:
            return None

        app = FirecrawlApp(api_key=api_key)
        result = app.scrape(url, formats=["markdown", "html"])
        if isinstance(result, dict):
            return result
        return {
            "markdown": getattr(result, "markdown", "") or "",
            "html": getattr(result, "html", "") or "",
        }

    def _extract_listings(
        self,
        text: str,
        query_text: str,
        *,
        base_url: str,
        source: str,
    ) -> list[LiveListing]:
        query_terms = self._query_terms(query_text)
        candidates: list[LiveListing] = []
        seen_urls: set[str] = set()
        stats = self._empty_extraction_stats(source=source)

        platform_candidates = self._extract_platform_specific_listings(text, query_text, base_url=base_url)
        stats["platform_candidates_seen"] = len(platform_candidates)
        for listing in platform_candidates:
            if listing.url in seen_urls:
                stats["rejected_duplicate_url"] += 1
                continue
            seen_urls.add(listing.url)
            candidates.append(listing)
            self._track_candidate_quality(stats, listing)
            if len(candidates) >= self.result_limit:
                self._last_extraction_stats = stats
                return candidates

        for title, url in MARKDOWN_LINK_RE.findall(text):
            stats["http_candidates_seen"] += 1
            normalized_url = self._normalize_result_url(url, base_url=base_url)
            if not normalized_url or not self._is_listing_url(normalized_url):
                stats["rejected_non_listing_url"] += 1
                continue
            if normalized_url in seen_urls:
                stats["rejected_duplicate_url"] += 1
                continue
            snippet = self._snippet_around_link(text, title, url)
            clean_title = self._clean_text(title)
            if not clean_title or self._is_noise_title(clean_title):
                stats["rejected_noise_title"] += 1
                continue
            if not self._matches_query(clean_title, snippet, query_terms, query_text=query_text):
                stats["rejected_query_miss"] += 1
                continue
            listing = self._build_listing(clean_title, normalized_url, snippet)
            seen_urls.add(normalized_url)
            candidates.append(listing)
            self._track_candidate_quality(stats, listing)
            if len(candidates) >= self.result_limit:
                self._last_extraction_stats = stats
                return candidates

        soup = BeautifulSoup(text, "lxml")
        for anchor in soup.find_all("a", href=True):
            stats["http_candidates_seen"] += 1
            normalized_url = self._normalize_result_url(anchor["href"], base_url=base_url)
            if not normalized_url or not self._is_listing_url(normalized_url):
                stats["rejected_non_listing_url"] += 1
                continue
            if normalized_url in seen_urls:
                stats["rejected_duplicate_url"] += 1
                continue
            clean_title = self._clean_text(anchor.get_text(" ", strip=True))
            snippet = self._clean_text(anchor.parent.get_text(" ", strip=True))[:240]
            if not clean_title or self._is_noise_title(clean_title):
                stats["rejected_noise_title"] += 1
                continue
            if not self._matches_query(clean_title, snippet, query_terms, query_text=query_text):
                stats["rejected_query_miss"] += 1
                continue
            listing = self._build_listing(clean_title, normalized_url, snippet)
            seen_urls.add(normalized_url)
            candidates.append(listing)
            self._track_candidate_quality(stats, listing)
            if len(candidates) >= self.result_limit:
                break

        self._last_extraction_stats = stats
        if candidates:
            if self._has_weak_listing_evidence(candidates):
                self._last_failure_reason = "weak_listing_evidence"
                return []
            return candidates

        if self._looks_like_captcha_page(text):
            self._last_failure_reason = "captcha_challenge"
            return []

        if self._looks_like_shell_page(text):
            self._last_failure_reason = "search_shell_only"
            return []

        title_match = TITLE_RE.search(text)
        if title_match:
            title = self._clean_text(title_match.group(1))
            if (
                title
                and not GENERIC_TITLE_RE.search(title)
                and self._matches_query(title, title, query_terms, query_text=query_text)
            ):
                self._last_failure_reason = "weak_page_level_match_only"
                return []
        return []

    def _extract_platform_specific_listings(
        self,
        text: str,
        query_text: str,
        *,
        base_url: str,
    ) -> list[LiveListing]:
        return []

    def _build_listing(self, title: str, url: str, snippet: str) -> LiveListing:
        price_band = self._price_band(snippet)
        sales_volume = self._extract_sales_volume(snippet)
        seller_count = self._extract_seller_count(snippet)
        seller_type = self._extract_seller_type(title, snippet)
        seller_name = self._extract_seller_name(snippet)
        return LiveListing(
            title=title,
            url=url,
            snippet=snippet,
            price_low=price_band["price_low"],
            price_mid=price_band["price_mid"],
            price_high=price_band["price_high"],
            sales_volume=sales_volume,
            seller_count=seller_count,
            seller_type=seller_type,
            seller_name=seller_name,
        )

    def _listing_to_candidate(
        self,
        query_text: str,
        listing: LiveListing,
        rank: int,
        *,
        source_mode: str,
    ) -> dict[str, Any]:
        seed = self._seed(f"{query_text}:{listing.url}")
        demand_score = max(45.0, 88.0 - rank * 6 + seed % 5)
        competition_score = min(88.0, 34.0 + rank * 8 + seed % 9)
        price_fit_score = 58.0 + (seed % 14)
        risk_score = 18.0 + rank * 5 + (seed % 6)

        risk_tags = ["live_marketplace_data"]
        if listing.price_low is None:
            risk_tags.append("price_not_extracted")
        if listing.seller_type == "enterprise":
            risk_tags.append("enterprise_seller")
        elif listing.seller_type == "personal":
            risk_tags.append("personal_seller")

        source_diagnostics = {
            "platform": self.platform,
            "listing_url": listing.url,
            "listing_snippet": listing.snippet,
            "rank": rank,
            "fallback_reason": None,
        }
        if listing.seller_name:
            source_diagnostics["seller_name"] = listing.seller_name

        return {
            "platform": self.platform,
            "platform_item_id": self._seed_id(listing.url),
            "title": listing.title,
            "image_url": None,
            "category_path": self._category_path(query_text),
            "price_low": listing.price_low,
            "price_mid": listing.price_mid,
            "price_high": listing.price_high,
            "sales_volume": listing.sales_volume,
            "seller_count": listing.seller_count,
            "seller_type": listing.seller_type,
            "seller_name": listing.seller_name,
            "demand_score": round(demand_score, 2),
            "competition_score": round(competition_score, 2),
            "price_fit_score": round(price_fit_score, 2),
            "risk_score": round(min(80.0, risk_score), 2),
            "risk_tags": risk_tags,
            "source_urls": [listing.url],
            "source_mode": source_mode,
            "source_diagnostics": source_diagnostics,
            "signals": [
                {
                    "platform": self.platform,
                    "signal_type": "live_search_listing",
                    "value_json": {
                        "query_text": query_text,
                        "rank": rank,
                        "snippet": listing.snippet,
                        "sales_volume": listing.sales_volume,
                        "seller_count": listing.seller_count,
                        "seller_type": listing.seller_type,
                    },
                    "sample_size": max(1, self.result_limit - rank + 1),
                    "freshness": "fresh",
                    "reliability": 0.76,
                }
            ],
        }

    def _empty_result(
        self,
        *,
        query_type: str,
        failure_reason: str,
        notes: list[str],
        source: str,
    ) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "mode": "failed",
            "items": [],
            "diagnostics": {
                "platform": self.platform,
                "query_type": query_type,
                "live_enabled": self.live_enabled,
                "live_result_count": 0,
                "fallback_reason": failure_reason,
                "notes": notes,
                "extraction_stats": self._empty_extraction_stats(source=source),
            },
        }

    def _failure_notes(self, failure_reason: str) -> list[str]:
        note_map = {
            "live_disabled": ["Live marketplace mode is disabled in backend configuration."],
            "live_fetch_failed": ["The marketplace search page could not be fetched or rendered reliably."],
            "no_structured_results_extracted": [
                "The marketplace page loaded, but stable listing fields could not be extracted."
            ],
            "search_shell_only": [
                "The marketplace returned a search shell or navigation page without stable listing records."
            ],
            "captcha_challenge": [
                "The marketplace returned an anti-bot or captcha challenge instead of accessible listing data."
            ],
            "weak_listing_evidence": [
                "The marketplace exposed only weak listing evidence, so the result was rejected."
            ],
            "weak_page_level_match_only": [
                "The page only exposed a weak title-level match, not usable listing data."
            ],
            "live_results_unavailable": ["Live marketplace results were unavailable for this query."],
            "empty_query": ["No usable query text was provided."],
        }
        return note_map.get(failure_reason, ["Live marketplace extraction failed and no production-safe results were stored."])

    def _category_path(self, query_text: str) -> str:
        lowered = query_text.lower()
        if "\u5ba0\u7269" in query_text or "pet" in lowered:
            return "Pets"
        if "\u6536\u7eb3" in query_text or "storage" in lowered:
            return "Home Storage"
        if "\u8f66" in query_text or "car" in lowered:
            return "Automotive"
        return "General Merchandise"

    def _is_listing_url(self, url: str) -> bool:
        return True

    @staticmethod
    def _seed(value: str) -> int:
        return int(hashlib.md5(value.encode("utf-8")).hexdigest()[:6], 16) % 10000

    def _seed_id(self, value: str) -> str:
        return f"{self.platform}-{self._seed(value)}"

    @staticmethod
    def _query_terms(query_text: str) -> list[str]:
        normalized = (query_text or "").strip().lower()
        if not normalized:
            return []

        terms: list[str] = []
        seen: set[str] = set()
        segments = [token for token in re.split("[\\s,\uFF0C\u3001|;\uFF1B:\uFF1A()\\[\\]{}<>_\\-/\\\\]+", normalized) if token]
        compact = "".join(segments)

        def add_term(value: str) -> None:
            cleaned = value.strip()
            if len(cleaned) < 2 or cleaned in seen:
                return
            seen.add(cleaned)
            terms.append(cleaned)

        add_term(compact)
        for segment in segments:
            add_term(segment)
            if re.search(r"[\u4e00-\u9fff]", segment):
                for width in (2, 3):
                    for index in range(0, max(0, len(segment) - width + 1)):
                        add_term(segment[index : index + width])

        return terms

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    @staticmethod
    def _normalize_result_url(url: str, *, base_url: str) -> str | None:
        cleaned = (url or "").strip()
        if not cleaned:
            return None
        if cleaned.startswith("//"):
            return f"https:{cleaned}"
        if cleaned.startswith("/"):
            parsed = httpx.URL(base_url)
            return str(parsed.copy_with(path=cleaned, query=None))
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
        return None

    @staticmethod
    def _snippet_around_link(text: str, title: str, url: str) -> str:
        anchor = f"[{title}]({url})"
        idx = text.find(anchor)
        if idx < 0:
            return ""
        return re.sub(r"\s+", " ", text[idx : idx + 240]).strip()

    @staticmethod
    def _matches_query(title: str, snippet: str, query_terms: list[str], *, query_text: str) -> bool:
        haystack = f"{title} {snippet}".lower()
        normalized_query = re.sub(r"\s+", "", query_text.lower())
        normalized_haystack = re.sub(r"\s+", "", haystack)
        if normalized_query and normalized_query in normalized_haystack:
            return True
        if not query_terms:
            return True
        matched_terms = {term for term in query_terms if term in haystack}
        if len(query_terms) == 1:
            return bool(matched_terms)
        return len(matched_terms) >= min(2, len(query_terms))

    @staticmethod
    def _looks_like_shell_page(text: str) -> bool:
        lowered = (text or "").lower()
        return any(marker.lower() in lowered for marker in SHELL_MARKERS)

    @staticmethod
    def _looks_like_captcha_page(text: str) -> bool:
        lowered = (text or "").lower()
        return any(marker in lowered for marker in CAPTCHA_MARKERS)

    @staticmethod
    def _price_band(snippet: str) -> dict[str, float | None]:
        normalized = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", snippet or "")
        prices: list[float] = []
        currency_symbols = "".join(re.escape(ch) for ch in ("$", chr(165), chr(65509)))

        for match in re.finditer(
            rf"(?:[{currency_symbols}]|rmb|cny|usd)\s*(\d+(?:\.\d+)?)",
            normalized,
            re.IGNORECASE,
        ):
            try:
                prices.append(float(match.group(1)))
            except ValueError:
                continue

        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(元|块|万|w|usd)", normalized, re.IGNORECASE):
            try:
                parsed = float(match.group(1))
            except ValueError:
                continue
            unit = match.group(2).lower()
            if unit in {"万", "w"}:
                parsed *= 10000
            prices.append(parsed)

        if not prices:
            return {"price_low": None, "price_mid": None, "price_high": None}
        low = min(prices)
        high = max(prices)
        mid = round((low + high) / 2, 2)
        return {"price_low": low, "price_mid": mid, "price_high": high}

    @staticmethod
    def _extract_sales_volume(snippet: str) -> int | None:
        text = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", snippet or "")
        for pattern in (
            re.compile(r"(?:月销|已售|卖出|sold)\s*(\d+(?:\.\d+)?)(万|w)?", re.IGNORECASE),
            re.compile(r"(\d+(?:\.\d+)?)\s*(人想要|人付款)", re.IGNORECASE),
        ):
            match = pattern.search(text)
            if not match:
                continue
            value = float(match.group(1))
            unit = match.group(2) if len(match.groups()) > 1 else None
            if unit and unit.lower() in {"万", "w"}:
                value *= 10000
            return int(value)
        return None

    @staticmethod
    def _extract_seller_count(snippet: str) -> int | None:
        for pattern in (
            re.compile(r"(\d+(?:\.\d+)?)\s*(?:家在卖|个卖家|卖家数)", re.IGNORECASE),
            re.compile(r"(\d+(?:\.\d+)?)\s*sellers?\b", re.IGNORECASE),
        ):
            match = pattern.search(snippet or "")
            if match:
                return int(float(match.group(1)))
        return None

    @staticmethod
    def _extract_seller_type(title: str, snippet: str) -> str | None:
        combined = f"{title} {snippet}"
        if any(marker in combined for marker in ENTERPRISE_MARKERS):
            return "enterprise"
        if any(marker in combined for marker in PERSONAL_MARKERS):
            return "personal"
        return None

    @staticmethod
    def _extract_seller_name(snippet: str) -> str | None:
        text = snippet or ""
        for pattern in SELLER_NAME_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _is_noise_title(title: str) -> bool:
        compact = re.sub(r"\s+", " ", title.strip().lower())
        return bool(GENERIC_LISTING_TEXT_RE.match(compact))

    @staticmethod
    def _has_weak_listing_evidence(candidates: list[LiveListing]) -> bool:
        if len(candidates) >= 2:
            return False
        if not candidates:
            return True
        return candidates[0].price_low is None

    @staticmethod
    def _empty_extraction_stats(*, source: str) -> dict[str, Any]:
        return {
            "http_candidates_seen": 0,
            "platform_candidates_seen": 0,
            "accepted_candidates": 0,
            "accepted_with_price": 0,
            "accepted_without_price": 0,
            "rejected_non_listing_url": 0,
            "rejected_noise_title": 0,
            "rejected_query_miss": 0,
            "rejected_duplicate_url": 0,
            "source": source,
        }

    @staticmethod
    def _track_candidate_quality(stats: dict[str, Any], listing: LiveListing) -> None:
        stats["accepted_candidates"] += 1
        if listing.price_low is None:
            stats["accepted_without_price"] += 1
        else:
            stats["accepted_with_price"] += 1

    def _resolve_request_cookies(
        self,
        url: str,
        *,
        request_cookies: dict[str, str] | None = None,
        cookie_file: str | None = None,
    ) -> dict[str, str]:
        resolved: dict[str, str] = {}
        if request_cookies:
            resolved.update(request_cookies)

        cookie_source = cookie_file or self.browser_cookies_path
        if cookie_source:
            resolved.update(self._load_cookie_map(cookie_source, url=url))
        return resolved

    def _load_cookie_map(self, cookie_file: str, *, url: str) -> dict[str, str]:
        path = Path(cookie_file)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to parse browser cookie file: %s", cookie_file)
            return {}

        hostname = httpx.URL(url).host or ""
        allowed_domains = tuple(domain.lower() for domain in self.live_cookie_domains)
        rows: list[dict[str, Any]]
        if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
            rows = [item for item in payload["cookies"] if isinstance(item, dict)]
        elif isinstance(payload, list):
            rows = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            return {str(key): str(value) for key, value in payload.items()}
        else:
            return {}

        cookie_map: dict[str, str] = {}
        for row in rows:
            name = str(row.get("name") or "").strip()
            value = str(row.get("value") or "").strip()
            domain = str(row.get("domain") or "").lstrip(".").lower()
            if not name or not value:
                continue
            if domain:
                if allowed_domains and not any(domain.endswith(allowed) for allowed in allowed_domains):
                    continue
                if hostname and not hostname.endswith(domain):
                    continue
            cookie_map[name] = value
        return cookie_map
