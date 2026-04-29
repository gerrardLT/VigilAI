"""
Taobao marketplace adapter with live-search support and deterministic fallback.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .live import LiveListing, LiveMarketplaceAdapter


class TaobaoAdapter(LiveMarketplaceAdapter):
    platform = "taobao"
    search_url_template = "https://s.taobao.com/search?q={query}"

    def _is_listing_url(self, url: str) -> bool:
        lowered = url.lower()
        return "taobao.com" in lowered and ("item" in lowered or "auction" in lowered)

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
            "[data-category='auctions'] a[href*='item.taobao.com']",
            ".item a[href*='item.taobao.com']",
            ".ctx-box a[href*='item.taobao.com']",
        ]
        seen: set[str] = set()
        query_terms = self._query_terms(query_text)

        for selector in selectors:
            for anchor in soup.select(selector):
                href = anchor.get("href")
                normalized_url = self._normalize_result_url(href or "", base_url=base_url)
                if not normalized_url or normalized_url in seen or not self._is_listing_url(normalized_url):
                    continue
                title = self._clean_text(anchor.get_text(" ", strip=True))
                if not title or self._is_noise_title(title):
                    continue
                container = anchor.find_parent(["div", "li", "article"]) or anchor.parent
                snippet = self._clean_text(container.get_text(" ", strip=True))[:240]
                if not self._matches_query(title, snippet, query_terms, query_text=query_text):
                    continue
                seen.add(normalized_url)
                listings.append(self._build_listing(title, normalized_url, snippet))
                if len(listings) >= self.result_limit:
                    return listings

        return listings

