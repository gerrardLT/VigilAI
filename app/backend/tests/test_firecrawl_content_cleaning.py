"""
Firecrawl content cleaning regression tests.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LOW_SIGNAL_FIRECRAWL_SOURCES, SOURCES_CONFIG  # noqa: E402
from data_manager import DataManager  # noqa: E402
from models import Activity  # noqa: E402
from scrapers.universal_scraper import UniversalScraper  # noqa: E402
from utils.content_cleaning import build_description_from_text, clean_detail_content, looks_like_noisy_scraped_text  # noqa: E402


@pytest.fixture
def temp_db():
    temp_root = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(temp_root, exist_ok=True)
    db_path = os.path.join(temp_root, f"{uuid.uuid4().hex}.db")
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def data_manager(temp_db):
    return DataManager(db_path=temp_db)


def create_universal_scraper(source_id: str) -> UniversalScraper:
    return UniversalScraper(source_id, SOURCES_CONFIG[source_id])


def test_high_value_firecrawl_sources_enable_detail_fetch():
    assert SOURCES_CONFIG["cyzone"]["fetch_details"] is True
    assert SOURCES_CONFIG["segmentfault"]["fetch_details"] is True
    assert SOURCES_CONFIG["juejin_events"]["fetch_details"] is True
    assert SOURCES_CONFIG["lanqiao"]["fetch_details"] is True
    assert SOURCES_CONFIG["bugcrowd"]["fetch_details"] is True
    assert SOURCES_CONFIG["polygon_grants"]["fetch_details"] is True
    assert SOURCES_CONFIG["ethereum_grants"]["fetch_details"] is True


def test_low_signal_firecrawl_sources_are_disabled():
    assert LOW_SIGNAL_FIRECRAWL_SOURCES == {
        "v2ex",
        "zcool",
        "behance",
        "zealy",
        "defillama_airdrops",
    }
    for source_id in LOW_SIGNAL_FIRECRAWL_SOURCES:
        assert SOURCES_CONFIG[source_id]["enabled"] is False


def test_clean_detail_content_removes_markdown_artifacts_and_site_noise():
    scraper = create_universal_scraper("cyzone")
    raw_content = """
# 黄仁勋要发Token当工资！

今天 09:15
[原文链接](https://www.cyzone.cn/article/828032.html)
黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科。
面试第一问：公司能给我多少token？
![封面](https://static.cyzone.cn/article-cover.png)

### 关于我们
[联系我们](https://www.cyzone.cn/about/contact)
"""

    cleaned = scraper._clean_detail_content(raw_content)

    assert "面试第一问：公司能给我多少token？" in cleaned
    assert "https://www.cyzone.cn/article/828032.html" not in cleaned
    assert "![封面]" not in cleaned
    assert "关于我们" not in cleaned
    assert "联系我们" not in cleaned


def test_content_cleaning_strips_broken_markdown_tokens_and_asset_query_fragments():
    raw_content = """
)]( 开源生态大会暨 PostgreSQL 高峰论坛
rmat=webp&resize=400x300
[更多](https://example.com/more)
官方议程已经公布，适合数据库开发者现场交流。
"""

    cleaned = clean_detail_content(raw_content)
    description = build_description_from_text(raw_content, title="开源生态大会暨 PostgreSQL 高峰论坛")

    assert looks_like_noisy_scraped_text(raw_content) is True
    assert "开源生态大会暨 PostgreSQL 高峰论坛" in cleaned
    assert "官方议程已经公布" in cleaned
    assert "开源生态大会暨 PostgreSQL 高峰论坛" in description
    assert "官方议程已经公布" in description
    assert ")](" not in cleaned
    assert "](" not in cleaned
    assert "rmat=webp" not in cleaned
    assert "resize=400x300" not in cleaned
    assert "https://example.com/more" not in cleaned
    assert "更多" not in description


def test_enrich_activities_with_details_replaces_noisy_listing_description_with_detail_excerpt(monkeypatch):
    scraper = create_universal_scraper("cyzone")
    activity = scraper.create_activity(
        url="https://www.cyzone.cn/article/828032.html",
        title="黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科",
        description=(
            "w.cyzone.cn/label/%E5%B0%8F%E7%B1%B3) 今天 09:15 "
            "[黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科]"
            "(https://www.cyzone.cn/article/828032.html) "
            "[面试第一问：公司能给我多少token？](https://www.cyzone.cn/article/828032.html) "
            "[Token](https://www.cyzone.cn/label/Token) "
            "[算力](https://www.cyzone.cn/label/%E7%AE%97%E5%8A%9B) "
            "今天 08:37 ### Going Global [更多](https://www.cyzone.cn/topic/15) "
            "[TikTok英国测试“Trendy Beat”](https://www.cyzone.cn/article/828000.html)"
        ),
    )

    async def fake_fetch_detail_content(url: str) -> str:
        assert url == "https://www.cyzone.cn/article/828032.html"
        return (
            "黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科。\n\n"
            "面试第一问：公司能给我多少token？"
        )

    monkeypatch.setattr(scraper, "fetch_detail_content", fake_fetch_detail_content)

    enriched = asyncio.run(scraper.enrich_activities_with_details([activity], max_count=1, delay_between=0))
    cleaned_activity = enriched[0]

    assert cleaned_activity.full_content.startswith("黄仁勋要发Token当工资！")
    assert "Going Global" not in cleaned_activity.description
    assert "TikTok英国测试" not in cleaned_activity.description
    assert "%E5%B0%8F%E7%B1%B3" not in cleaned_activity.description
    assert "[" not in cleaned_activity.description


def test_data_manager_cleans_noisy_firecrawl_rows_on_read(data_manager):
    now = datetime.now()
    activity = Activity(
        id=Activity.generate_id("cyzone", "https://www.cyzone.cn/article/828032.html"),
        title="黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科",
        description=(
            "w.cyzone.cn/label/%E5%B0%8F%E7%B1%B3) 今天 09:15 "
            "[黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科]"
            "(https://www.cyzone.cn/article/828032.html) "
            "[面试第一问：公司能给我多少token？](https://www.cyzone.cn/article/828032.html) "
            "[Token](https://www.cyzone.cn/label/Token) "
            "今天 08:37 ### Going Global [更多](https://www.cyzone.cn/topic/15)"
        ),
        source_id="cyzone",
        source_name="创业邦",
        url="https://www.cyzone.cn/article/828032.html",
        category="news",
        tags=["token"],
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)

    loaded = data_manager.get_activity_by_id(activity.id)

    assert loaded is not None
    assert loaded.description == (
        "黄仁勋要发Token当工资！硅谷兴起刷量大赛，一人一周烧掉33个维基百科 "
        "面试第一问：公司能给我多少token？"
    )
    assert "Going Global" not in loaded.description
    assert "%E5%B0%8F%E7%B1%B3" not in loaded.description
    assert "[" not in loaded.description
    assert "Going Global" not in (loaded.summary or "")


@pytest.mark.parametrize(
    ("source_id", "markdown"),
    [
        (
            "zcool",
            "- [2025 Portfolio Recap](https://www.zcool.com.cn/work/ZNzMzNTE5MDQ=.html)\n"
            "Homepage recommendation\n"
            "![cover](https://img.zcool.cn/community/example.webp)\n",
        ),
        (
            "behance",
            "- [Link to project - SHINSEGAE 2026 | Media Facade Art](https://www.behance.net/gallery/245166933/example)\n",
        ),
        (
            "defillama_airdrops",
            "- [Airdrops3540 trackedTokenless protocols that may airdrop tokens to their users]"
            "(https://defillama.com/airdrops)\n",
        ),
    ],
)
def test_universal_scraper_skips_low_signal_firecrawl_listing_candidates(source_id, markdown):
    scraper = create_universal_scraper(source_id)

    activities = scraper._extract_list_items(markdown)

    assert activities == []


def test_data_manager_skips_invalid_firecrawl_activity_on_write(data_manager):
    now = datetime.now()
    activity = Activity(
        id=Activity.generate_id("zcool", "https://www.zcool.com.cn/work/ZNzMzNTE5MDQ=.html"),
        title="2025 Portfolio Recap",
        description="Homepage recommendation ![cover](https://img.zcool.cn/community/example.webp)",
        source_id="zcool",
        source_name="ZCOOL",
        url="https://www.zcool.com.cn/work/ZNzMzNTE5MDQ=.html",
        category="other_competition",
        tags=["design"],
        created_at=now,
        updated_at=now,
    )

    inserted = data_manager.add_activity(activity)
    items, total = data_manager.get_activities()

    assert inserted is False
    assert total == 0
    assert items == []
    assert data_manager.get_activity_by_id(activity.id) is None


def test_data_manager_hides_existing_invalid_firecrawl_rows_from_reads(data_manager):
    now = datetime.now().isoformat()
    activity_id = Activity.generate_id("zealy", "https://twitter.com/trustyfy")
    with data_manager._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activities (
                id, title, description, full_content, source_id, source_name, url, category, tags,
                prize_amount, prize_currency, prize_description,
                start_date, end_date, deadline, location, organizer, image_url,
                summary, score, score_reason, deadline_level, trust_level, updated_fields,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity_id,
                "1.6K",
                "[https://trustyfy.com](https://trustyfy.com/) 15 1.5K [1.6K](https://twitter.com/trustyfy)",
                None,
                "zealy",
                "Zealy",
                "https://twitter.com/trustyfy",
                "airdrop",
                "[]",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "[]",
                "upcoming",
                now,
                now,
            ),
        )

    items, total = data_manager.get_activities()
    stats = data_manager.get_stats()

    assert items == []
    assert total == 0
    assert data_manager.get_activity_by_id(activity_id) is None
    assert stats.total_activities == 0


def test_data_manager_hides_existing_raw_markdown_titles_from_reads(data_manager):
    now = datetime.now().isoformat()
    activity_id = Activity.generate_id("v2ex", "https://www.v2ex.com/member/Livid")
    with data_manager._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activities (
                id, title, description, full_content, source_id, source_name, url, category, tags,
                prize_amount, prize_currency, prize_description,
                start_date, end_date, deadline, location, organizer, image_url,
                summary, score, score_reason, deadline_level, trust_level, updated_fields,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity_id,
                "[senooo](https://www.v2ex.com/member/senooo)",
                "MLH黑客松: [senooo](https://www.v2ex.com/member/senooo)",
                None,
                "v2ex",
                "V2EX",
                "https://www.v2ex.com/member/Livid",
                "hackathon",
                "[]",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "[]",
                "upcoming",
                now,
                now,
            ),
        )

    items, total = data_manager.get_activities(filters={"source_id": "v2ex"})

    assert items == []
    assert total == 0
    assert data_manager.get_activity_by_id(activity_id) is None
