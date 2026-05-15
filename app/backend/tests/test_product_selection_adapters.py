"""
Product-selection adapter tests.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from product_selection.adapters import TaobaoAdapter, XianyuAdapter  # noqa: E402


def test_taobao_adapter_skips_live_fetch_when_disabled(monkeypatch):
    adapter = TaobaoAdapter(live_fetch_enabled=False)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("live fetch should not be called")

    monkeypatch.setattr(adapter, "_search_live_products", fail_if_called)

    items = adapter.search_products("宠物饮水机", query_type="keyword")

    assert len(items) >= 2
    assert all(item["platform"] == "taobao" for item in items)
    assert all(
        any(signal["value_json"].get("mode") == "synthetic" for signal in item["signals"])
        for item in items
    )


def test_taobao_adapter_falls_back_when_live_fetch_fails(monkeypatch):
    adapter = TaobaoAdapter(live_fetch_enabled=True)

    def raise_live_failure(*args, **kwargs):
        raise RuntimeError("upstream blocked")

    monkeypatch.setattr(adapter, "_search_live_products", raise_live_failure)

    items = adapter.search_products("桌面收纳", query_type="keyword")

    assert len(items) >= 2
    assert items[0]["platform"] == "taobao"
    assert items[0]["source_urls"][0].startswith("https://item.taobao.com/item.htm?id=")


def test_xianyu_adapter_prefers_live_results_when_available(monkeypatch):
    adapter = XianyuAdapter(live_fetch_enabled=True)
    live_item = {
        "platform": "xianyu",
        "platform_item_id": "live-1",
        "title": "宠物饮水机 实时候选",
        "image_url": None,
        "category_path": "宠物/用品设备",
        "price_low": 59.0,
        "price_mid": 72.0,
        "price_high": 86.0,
        "demand_score": 82.0,
        "competition_score": 44.0,
        "price_fit_score": 74.0,
        "risk_score": 29.0,
        "risk_tags": ["需人工复核实时库存"],
        "source_urls": ["https://www.goofish.com/item?id=123"],
        "signals": [
            {
                "platform": "xianyu",
                "signal_type": "data_source",
                "value_json": {"mode": "live", "channel": "firecrawl"},
                "sample_size": 1,
                "freshness": "live",
                "reliability": 0.8,
            }
        ],
    }

    monkeypatch.setattr(adapter, "_search_live_products", lambda *args, **kwargs: [live_item])
    monkeypatch.setattr(
        adapter,
        "_search_fallback_products",
        lambda *args, **kwargs: pytest.fail("fallback should not be used when live results exist"),
    )

    items = adapter.search_products("宠物饮水机", query_type="keyword")

    assert items == [live_item]
