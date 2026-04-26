"""
Deterministic Taobao adapter for MVP product-selection research.
"""

from __future__ import annotations

import hashlib
from typing import Any


class TaobaoAdapter:
    platform = "taobao"

    def search_products(self, query_text: str, *, query_type: str) -> list[dict[str, Any]]:
        seed = self._seed(query_text)
        category_path = self._category_path(query_text)
        titles = [
            f"{query_text} 高转化基础款",
            f"{query_text} 升级组合款",
        ]
        products: list[dict[str, Any]] = []
        for index, title in enumerate(titles, start=1):
            price_low = 29 + (seed % 7) * 3 + index * 4
            price_mid = price_low + 20 + index * 6
            price_high = price_mid + 22
            demand_score = 68 + (seed % 11) + index * 4
            competition_score = 38 + (seed % 9) + index * 7
            price_fit_score = 62 + (seed % 13) + index * 3
            risk_score = 22 + (seed % 8) + index * 6
            risk_tags = ["售后复杂"] if index == 2 else ["同款偏多"]
            products.append(
                {
                    "platform": self.platform,
                    "platform_item_id": f"tb-{seed}-{index}",
                    "title": title,
                    "image_url": None,
                    "category_path": category_path,
                    "price_low": float(price_low),
                    "price_mid": float(price_mid),
                    "price_high": float(price_high),
                    "demand_score": float(min(demand_score, 95)),
                    "competition_score": float(min(competition_score, 90)),
                    "price_fit_score": float(min(price_fit_score, 90)),
                    "risk_score": float(min(risk_score, 80)),
                    "risk_tags": risk_tags,
                    "source_urls": [f"https://item.taobao.com/item.htm?id={seed}{index:02d}"],
                    "signals": [
                        {
                            "platform": self.platform,
                            "signal_type": "search_heat",
                            "value_json": {"query_text": query_text, "score": demand_score},
                            "sample_size": 1200 + index * 250,
                            "freshness": "fresh",
                            "reliability": 0.8,
                        },
                        {
                            "platform": self.platform,
                            "signal_type": "price_band",
                            "value_json": {"low": price_low, "mid": price_mid, "high": price_high},
                            "sample_size": 60 + index * 8,
                            "freshness": "fresh",
                            "reliability": 0.74,
                        },
                    ],
                }
            )
        return products

    @staticmethod
    def _seed(query_text: str) -> int:
        return int(hashlib.md5(query_text.encode("utf-8")).hexdigest()[:6], 16) % 10000

    @staticmethod
    def _category_path(query_text: str) -> str:
        lowered = query_text.lower()
        if "宠物" in query_text or "pet" in lowered:
            return "宠物用品/喂食饮水"
        if "收纳" in query_text or "storage" in lowered:
            return "家居收纳/整理用品"
        if "车" in query_text or "car" in lowered:
            return "汽车用品/内饰配件"
        return "创意百货/日用杂货"
