"""
Deterministic Xianyu adapter for MVP product-selection research.
"""

from __future__ import annotations

import hashlib
from typing import Any


class XianyuAdapter:
    platform = "xianyu"

    def search_products(self, query_text: str, *, query_type: str) -> list[dict[str, Any]]:
        seed = self._seed(query_text)
        category_path = self._category_path(query_text)
        titles = [
            f"{query_text} 二手轻改款",
            f"{query_text} 闲鱼低门槛试卖款",
        ]
        products: list[dict[str, Any]] = []
        for index, title in enumerate(titles, start=1):
            price_low = 19 + (seed % 5) * 3 + index * 2
            price_mid = price_low + 18 + index * 5
            price_high = price_mid + 18
            demand_score = 60 + (seed % 9) + index * 5
            competition_score = 30 + (seed % 11) + index * 5
            price_fit_score = 58 + (seed % 10) + index * 4
            risk_score = 18 + (seed % 10) + index * 5
            risk_tags = ["成色标准不一"] if index == 1 else ["售后预期管理"]
            products.append(
                {
                    "platform": self.platform,
                    "platform_item_id": f"xy-{seed}-{index}",
                    "title": title,
                    "image_url": None,
                    "category_path": category_path,
                    "price_low": float(price_low),
                    "price_mid": float(price_mid),
                    "price_high": float(price_high),
                    "demand_score": float(min(demand_score, 92)),
                    "competition_score": float(min(competition_score, 88)),
                    "price_fit_score": float(min(price_fit_score, 88)),
                    "risk_score": float(min(risk_score, 78)),
                    "risk_tags": risk_tags,
                    "source_urls": [f"https://2.taobao.com/item.htm?id={seed}{index:02d}"],
                    "signals": [
                        {
                            "platform": self.platform,
                            "signal_type": "listing_velocity",
                            "value_json": {"query_text": query_text, "score": demand_score},
                            "sample_size": 180 + index * 35,
                            "freshness": "fresh",
                            "reliability": 0.72,
                        },
                        {
                            "platform": self.platform,
                            "signal_type": "seller_density",
                            "value_json": {"score": competition_score},
                            "sample_size": 90 + index * 12,
                            "freshness": "fresh",
                            "reliability": 0.7,
                        },
                    ],
                }
            )
        return products

    @staticmethod
    def _seed(query_text: str) -> int:
        return int(hashlib.md5(("xianyu:" + query_text).encode("utf-8")).hexdigest()[:6], 16) % 10000

    @staticmethod
    def _category_path(query_text: str) -> str:
        lowered = query_text.lower()
        if "宠物" in query_text or "pet" in lowered:
            return "宠物/用品设备"
        if "收纳" in query_text or "storage" in lowered:
            return "居家/收纳整理"
        if "车" in query_text or "car" in lowered:
            return "汽车用品/车载配件"
        return "家居百货/实用小物"
