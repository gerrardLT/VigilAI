"""
Xianyu marketplace adapter with live-search support.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .live import LiveListing, LiveMarketplaceAdapter


class XianyuAdapter(LiveMarketplaceAdapter):
    platform = "xianyu"
    search_url_template = "https://www.goofish.com/search?keyword={query}"
    _DETAIL_ITEM_ID_RE = re.compile(r"(?:itemId|[?&]id=)(\d{6,})", re.IGNORECASE)
    _DETAIL_SALES_RE = re.compile(r"卖出\s*(\d+)\s*件宝贝")
    _META_SPLIT_RE = re.compile(
        r"\s*(?:¥|\d+\s*人想要|回复超快|卖家信用|百分百好评|发货极快|\d+小时前发布|\d+分钟前发布|[省市区县]\s).*",
        re.IGNORECASE,
    )

    def _is_listing_url(self, url: str) -> bool:
        lowered = url.lower()
        return ("goofish.com" in lowered or "2.taobao.com" in lowered) and ("item" in lowered or "detail" in lowered)

    def _extract_platform_specific_listings(
        self,
        text: str,
        query_text: str,
        *,
        base_url: str,
    ) -> list[LiveListing]:
        soup = BeautifulSoup(text, "lxml")
        listings: list[LiveListing] = []
        selectors = [
            "a[class*='feeds-item-wrap'][href*='goofish.com/item?id=']",
            "[data-testid='search-item'] a[href*='goofish.com']",
            ".feeds-item a[href*='goofish.com']",
            ".card-wrapper a[href*='goofish.com']",
            "a[href*='2.taobao.com/item.htm']",
        ]
        seen: set[str] = set()
        query_terms = self._query_terms(query_text)

        for selector in selectors:
            for anchor in soup.select(selector):
                href = anchor.get("href")
                normalized_url = self._normalize_result_url(href or "", base_url=base_url)
                if not normalized_url or normalized_url in seen or not self._is_listing_url(normalized_url):
                    continue
                title_text = self._clean_text(anchor.get_text(" ", strip=True))
                title = self._title_from_anchor_text(title_text)
                if not title or self._is_noise_title(title):
                    continue
                snippet = self._snippet_from_anchor(anchor)
                if not self._matches_query(title, snippet, query_terms, query_text=query_text):
                    continue
                seen.add(normalized_url)
                listings.append(self._build_listing(title, normalized_url, snippet))
                if len(listings) >= self.result_limit:
                    return listings

        return listings

    def _title_from_anchor_text(self, title_text: str) -> str:
        normalized = self._clean_text(title_text)
        if not normalized:
            return ""
        trimmed = self._META_SPLIT_RE.sub("", normalized).strip(" -|,")
        return trimmed or normalized[:120]

    def _snippet_from_anchor(self, anchor) -> str:
        title_text = self._clean_text(anchor.get_text(" ", strip=True))
        title_attr = self._clean_text(anchor.get("title") or "")
        classes = anchor.get("class") or []
        if any("feeds-item-wrap" in value for value in classes):
            return (title_text or title_attr)[:800]
        container = anchor.find_parent(["div", "li", "article"]) or anchor.parent
        return self._clean_text(container.get_text(" ", strip=True))[:240]

    def extract_detail_snapshot_fields(self, html: str) -> dict[str, object | None]:
        soup = BeautifulSoup(html, "lxml")

        title = ""
        main_info = soup.select_one("div[class*='item-main-info']")
        if main_info:
            main_text = self._clean_text(main_info.get_text(" ", strip=True))
            price_split = re.split(r"(?:\u00a5|\uffe5)\s*\d+(?:\.\d+)?", main_text, maxsplit=1)
            if len(price_split) > 1:
                title = self._clean_text(price_split[1].split("品 牌", 1)[0].split("聊一聊", 1)[0])
        if not title and soup.title and soup.title.get_text(strip=True):
            title = soup.title.get_text(strip=True).replace("_闲鱼", "").strip()

        item_id = self._extract_detail_item_id(html)
        seller_name = None
        seller_type = None
        sales_volume = None
        seller_container = soup.select_one("div[class*='item-user-container']")
        if seller_container:
            nick = seller_container.select_one("div[class*='item-user-info-nick']")
            if nick:
                seller_name = self._clean_text(nick.get_text(" ", strip=True)) or None
            if not seller_name:
                seller_text_blocks = [
                    self._clean_text(node.get_text(" ", strip=True))
                    for node in seller_container.select("div, p, span")
                ]
                seller_name = next(
                    (
                        text
                        for text in seller_text_blocks
                        if text and "卖出" not in text and "闲鱼" not in text and "好评率" not in text and len(text) >= 2
                    ),
                    None,
                )
            seller_text = self._clean_text(seller_container.get_text(" ", strip=True))
            sales_match = self._DETAIL_SALES_RE.search(seller_text)
            if sales_match:
                sales_volume = int(sales_match.group(1))
            if "personal?userId=" in str(seller_container):
                seller_type = "personal"
            inferred = self._extract_seller_type(title, seller_text)
            if inferred:
                seller_type = inferred
            elif seller_type is None:
                seller_type = "personal"

        price_low = None
        price_mid = None
        price_high = None
        if main_info:
            main_text = self._clean_text(main_info.get_text(" ", strip=True))
            band = self._price_band(main_text)
            price_low = band["price_low"]
            price_mid = band["price_mid"]
            price_high = band["price_high"]

        return {
            "item_id": item_id,
            "title": title or None,
            "price_low": price_low,
            "price_mid": price_mid,
            "price_high": price_high,
            "sales_volume": sales_volume,
            "seller_name": seller_name,
            "seller_type": seller_type,
        }

    def enrich_candidate_with_detail_snapshot(
        self,
        candidate: dict[str, Any],
        detail_html: str,
    ) -> dict[str, Any]:
        if candidate.get("platform") != self.platform:
            return candidate

        listing_url = self._candidate_listing_url(candidate)
        listing_item_id = self._extract_item_id_from_url(listing_url)
        detail = self.extract_detail_snapshot_fields(detail_html)
        detail_item_id = str(detail.get("item_id") or "").strip() or None
        if detail_item_id and listing_item_id and detail_item_id != listing_item_id:
            return candidate

        enriched = dict(candidate)
        for field in ("title", "price_low", "price_mid", "price_high", "sales_volume", "seller_name", "seller_type"):
            if detail.get(field) is not None:
                enriched[field] = detail[field]

        risk_tags = [str(tag) for tag in enriched.get("risk_tags") or [] if str(tag) != "price_not_extracted"]
        if "detail_snapshot_enriched" not in risk_tags:
            risk_tags.append("detail_snapshot_enriched")
        enriched["risk_tags"] = risk_tags

        diagnostics = dict(enriched.get("source_diagnostics") or {})
        diagnostics["detail_snapshot_enriched"] = True
        diagnostics["detail_item_id"] = detail_item_id or listing_item_id
        if detail.get("seller_name"):
            diagnostics["seller_name"] = detail["seller_name"]
        enriched["source_diagnostics"] = diagnostics

        signals = list(enriched.get("signals") or [])
        signals.append(
            {
                "platform": self.platform,
                "signal_type": "detail_snapshot_listing",
                "value_json": {
                    "item_id": detail_item_id or listing_item_id,
                    "sales_volume": detail.get("sales_volume"),
                    "seller_name": detail.get("seller_name"),
                    "seller_type": detail.get("seller_type"),
                    "price_low": detail.get("price_low"),
                },
                "sample_size": 1,
                "freshness": "fresh",
                "reliability": 0.89,
            }
        )
        enriched["signals"] = signals
        return enriched

    @classmethod
    def _extract_item_id_from_url(cls, url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        item_id = (query.get("id") or query.get("itemId") or [None])[0]
        if item_id:
            return str(item_id)
        match = cls._DETAIL_ITEM_ID_RE.search(url)
        return match.group(1) if match else None

    def _extract_detail_item_id(self, html: str) -> str | None:
        direct_match = re.search(r"itemId=(\d{6,})", html, re.IGNORECASE)
        if direct_match:
            return direct_match.group(1)
        match = self._DETAIL_ITEM_ID_RE.search(html)
        return match.group(1) if match else None

    @staticmethod
    def _candidate_listing_url(candidate: dict[str, Any]) -> str:
        source_urls = candidate.get("source_urls") or []
        if source_urls:
            return str(source_urls[0])
        diagnostics = candidate.get("source_diagnostics") or {}
        return str(diagnostics.get("listing_url") or "")
