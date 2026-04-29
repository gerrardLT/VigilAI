"""
Product-selection agent tool tests.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sys
import uuid

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_platform.conversation_engine import ConversationEngine  # noqa: E402
from agent_platform.models import AgentSession, AgentTurn  # noqa: E402
from agent_platform.tool_router import ToolRouter, build_default_registry  # noqa: E402
from api import app  # noqa: E402
from data_manager import DataManager  # noqa: E402
from product_selection.adapters.taobao import TaobaoAdapter  # noqa: E402
from product_selection.adapters.xianyu import XianyuAdapter  # noqa: E402
from product_selection.repository import ProductSelectionRepository  # noqa: E402
from product_selection.service import ProductSelectionService  # noqa: E402
from product_selection.tools import SelectionQueryTool  # noqa: E402


class DummyScheduler:
    async def refresh_source(self, source_id: str) -> bool:
        return True

    async def refresh_all(self) -> None:
        return None


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


@pytest.fixture
def client(data_manager):
    app.state.data_manager = data_manager
    app.state.scheduler = DummyScheduler()
    with TestClient(app) as test_client:
        yield test_client


def build_router(data_manager: DataManager) -> ToolRouter:
    return ToolRouter(
        tool_registry=build_default_registry(data_manager=data_manager),
        registry_key=data_manager.db_path,
    )


def build_session() -> AgentSession:
    now = datetime.now()
    return AgentSession(
        id=uuid.uuid4().hex,
        domain_type="product_selection",
        entry_mode="chat",
        status="active",
        title=None,
        created_at=now,
        updated_at=now,
        last_turn_at=None,
    )


def build_user_turn(content: str) -> AgentTurn:
    return AgentTurn(
        id=uuid.uuid4().hex,
        session_id=uuid.uuid4().hex,
        role="user",
        content=content,
        sequence_no=1,
        tool_name=None,
        tool_payload={},
        created_at=datetime.now(),
    )


def extract_goofish_listing_fragment(html: str, item_id: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    anchor = soup.select_one(f"a[href*='goofish.com/item?id={item_id}']")
    assert anchor is not None
    return f"<html><body>{str(anchor)}</body></html>"


def test_router_uses_selection_query_tool_for_selection_session(data_manager):
    router = build_router(data_manager)

    selected = router.resolve_tools(
        domain_type="product_selection",
        user_message="淘宝上的宠物饮水机还值得做吗",
    )

    assert "selection_query" in selected


def test_router_uses_selection_compare_tool_for_compare_prompt(data_manager):
    router = build_router(data_manager)

    selected = router.resolve_tools(
        domain_type="product_selection",
        user_message="对比淘宝和闲鱼上的宠物饮水机，哪个更值得做",
    )

    assert selected == ["selection_compare"]


def test_conversation_engine_returns_selection_shortlist_and_comparison_artifacts(data_manager):
    engine = ConversationEngine(build_router(data_manager))

    reply = engine.reply(
        session=build_session(),
        user_turn=build_user_turn("对比淘宝和闲鱼上的宠物饮水机，哪个更值得做"),
    )

    assert reply.tool_calls[0]["tool_name"] == "selection_compare"
    assert reply.tool_calls[0]["status"] == "completed"
    assert reply.artifacts[0].artifact_type == "checklist"
    assert not any(artifact.artifact_type == "shortlist" for artifact in reply.artifacts)
    assert not any(artifact.artifact_type == "comparison" for artifact in reply.artifacts)
    assert "margin, sell-through speed, or after-sales risk" in reply.assistant_turn
    assert "I did not find a strong shortlist yet." in reply.assistant_turn


def test_agent_turn_api_returns_shortlist_artifact_for_product_selection_query(client):
    session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "product_selection", "entry_mode": "chat"},
    ).json()

    response = client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "淘宝宠物饮水机还值得做吗"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["domain_type"] == "product_selection"
    assert payload["artifacts"][0]["artifact_type"] == "checklist"
    assert not any(item["artifact_type"] == "shortlist" for item in payload["artifacts"])
    assert payload["tool_calls"][0]["tool_name"] == "selection_query"
    assert payload["tool_calls"][0]["status"] == "completed"
    assert "I did not find a strong shortlist yet." in payload["assistant_turn"]["content"]


def test_live_adapter_classifies_shell_page_as_failed(monkeypatch):
    adapter = TaobaoAdapter(live_enabled=True)

    monkeypatch.setattr(
        adapter,
        "_fetch_http",
        lambda url, **kwargs: """
            <html>
              <head><title>淘宝搜索</title></head>
              <body><div class='boneClass_cardListWrapper'></div></body>
            </html>
        """,
    )
    monkeypatch.setattr(adapter, "_fetch_firecrawl", lambda url: None)

    result = adapter.search_marketplace("宠物饮水机", query_type="keyword")

    assert result["mode"] == "failed"
    assert result["diagnostics"]["fallback_reason"] == "search_shell_only"
    assert result["items"] == []


def test_live_adapter_rejects_single_weak_listing_without_storing_fallback(monkeypatch):
    adapter = TaobaoAdapter(live_enabled=True)

    monkeypatch.setattr(
        adapter,
        "_fetch_http",
        lambda url, **kwargs: """
            <html>
              <body>
                <div class="card">
                  <a href="https://item.taobao.com/item.htm?id=1">宠物饮水机静音款</a>
                </div>
              </body>
            </html>
        """,
    )
    monkeypatch.setattr(adapter, "_fetch_firecrawl", lambda url: None)

    result = adapter.search_marketplace("宠物饮水机", query_type="keyword")

    assert result["mode"] == "failed"
    assert result["diagnostics"]["fallback_reason"] == "weak_listing_evidence"
    assert result["items"] == []


def test_live_adapter_extracts_multiple_chinese_listings_with_prices(monkeypatch):
    adapter = TaobaoAdapter(live_enabled=True)

    monkeypatch.setattr(
        adapter,
        "_fetch_http",
        lambda url, **kwargs: """
            <html>
              <body>
                <div>
                  <a href="https://item.taobao.com/item.htm?id=101">宠物饮水机静音循环款</a>
                  <span>PetLab旗舰店 券后 ￥89 月销 300+</span>
                </div>
                <div>
                  <a href="https://item.taobao.com/item.htm?id=102">宠物饮水机过滤升级款</a>
                  <span>到手 129元 14家在卖 好评率高</span>
                </div>
              </body>
            </html>
        """,
    )
    monkeypatch.setattr(adapter, "_fetch_firecrawl", lambda url: None)

    result = adapter.search_marketplace("宠物 饮水机", query_type="keyword")

    assert result["mode"] == "live"
    assert result["diagnostics"]["live_result_count"] == 2
    assert len(result["items"]) == 2
    assert all(item["source_mode"] == "live" for item in result["items"])
    assert result["items"][0]["price_low"] == 89.0
    assert result["items"][1]["price_low"] == 129.0
    assert result["items"][0]["sales_volume"] == 300


def test_live_adapter_reports_extraction_stats_for_failed_run(monkeypatch):
    adapter = TaobaoAdapter(live_enabled=True)

    monkeypatch.setattr(
        adapter,
        "_fetch_http",
        lambda url, **kwargs: """
            <html>
              <body>
                <a href="/shops/demo">查看详情</a>
                <a href="https://item.taobao.com/item.htm?id=9">无关收纳盒</a>
              </body>
            </html>
        """,
    )
    monkeypatch.setattr(adapter, "_fetch_firecrawl", lambda url: None)

    result = adapter.search_marketplace("宠物饮水机", query_type="keyword")

    assert result["mode"] == "failed"
    stats = result["diagnostics"]["extraction_stats"]
    assert stats["http_candidates_seen"] >= 2
    assert stats["rejected_non_listing_url"] >= 1
    assert stats["rejected_query_miss"] >= 1
    assert stats["accepted_candidates"] == 0


def test_taobao_platform_specific_selector_extracts_live_listing(monkeypatch):
    adapter = TaobaoAdapter(live_enabled=True)

    monkeypatch.setattr(
        adapter,
        "_fetch_http",
        lambda url, **kwargs: """
            <html>
              <body>
                <div class="item">
                  <a href="https://item.taobao.com/item.htm?id=301">宠物饮水机静音循环款</a>
                  <span>官方旗舰店 到手￥99 月销99</span>
                </div>
              </body>
            </html>
        """,
    )
    monkeypatch.setattr(adapter, "_fetch_firecrawl", lambda url: None)

    result = adapter.search_marketplace("宠物饮水机", query_type="keyword")

    assert result["mode"] == "live"
    stats = result["diagnostics"]["extraction_stats"]
    assert stats["platform_candidates_seen"] >= 1
    assert stats["accepted_with_price"] >= 1
    assert result["items"][0]["seller_type"] == "enterprise"
    assert result["items"][0]["sales_volume"] == 99


def test_xianyu_platform_specific_selector_extracts_live_listing(monkeypatch):
    adapter = XianyuAdapter(live_enabled=True)

    monkeypatch.setattr(
        adapter,
        "_fetch_http",
        lambda url, **kwargs: """
            <html>
              <body>
                <div class="feeds-item">
                  <a href="https://www.goofish.com/item/detail?id=401">露营桌折叠便携款</a>
                  <span>个人闲置 现价 58元 自提优先</span>
                </div>
              </body>
            </html>
        """,
    )
    monkeypatch.setattr(adapter, "_fetch_firecrawl", lambda url: None)

    result = adapter.search_marketplace("露营桌", query_type="keyword")

    assert result["mode"] == "live"
    stats = result["diagnostics"]["extraction_stats"]
    assert stats["platform_candidates_seen"] >= 1
    assert result["items"][0]["price_low"] == 58.0
    assert result["items"][0]["seller_type"] == "personal"


def test_real_taobao_shell_fixture_stays_fallback():
    adapter = TaobaoAdapter(live_enabled=True)
    fixture = Path(__file__).parent / "fixtures" / "product_selection" / "taobao_search_pet_water_fountain.html"
    html = fixture.read_text(encoding="utf-8", errors="ignore")

    listings = adapter._extract_listings(
        html,
        "宠物饮水机",
        base_url=adapter.search_url_template.format(query="宠物饮水机"),
        source="fixture",
    )

    assert listings == []
    assert adapter._last_failure_reason == "search_shell_only"
    assert adapter._last_extraction_stats["accepted_candidates"] == 0


def test_real_taobao_rendered_fixture_is_classified_as_captcha_challenge():
    adapter = TaobaoAdapter(live_enabled=True)
    fixture = Path(__file__).parent / "fixtures" / "product_selection" / "taobao_logged_in_rendered_search.html"
    html = fixture.read_text(encoding="utf-8", errors="ignore")

    listings = adapter._extract_listings(
        html,
        "瀹犵墿楗按鏈?",
        base_url=adapter.search_url_template.format(query="瀹犵墿楗按鏈?"),
        source="fixture",
    )

    assert listings == []
    assert adapter._last_failure_reason == "captcha_challenge"
    assert adapter._last_extraction_stats["accepted_candidates"] == 0
    assert adapter._last_extraction_stats["http_candidates_seen"] > 0


def test_service_marks_query_failed_when_no_live_candidates_are_available(data_manager):
    service = ProductSelectionService(ProductSelectionRepository(data_manager.db_path))
    service.taobao_adapter.live_enabled = True

    result = service.start_research_job(
        query_type="keyword",
        query_text="pet water fountain",
        platform_scope="taobao",
        rendered_snapshot_html="<html><body><div class='boneClass_cardListWrapper'></div></body></html>",
    )

    assert result["job"]["status"] == "failed"
    assert result["total"] == 0
    assert result["items"] == []
    assert result["source_summary"]["overall_mode"] == "failed"
    assert "search_shell_only" in result["source_summary"]["fallback_reasons"]


def test_real_goofish_shell_fixture_stays_fallback():
    adapter = XianyuAdapter(live_enabled=True)
    fixture = Path(__file__).parent / "fixtures" / "product_selection" / "goofish_search_camping_table.html"
    html = fixture.read_text(encoding="utf-8", errors="ignore")

    listings = adapter._extract_listings(
        html,
        "露营桌",
        base_url=adapter.search_url_template.format(query="露营桌"),
        source="fixture",
    )

    assert listings == []
    assert adapter._last_failure_reason == "search_shell_only"
    assert adapter._last_extraction_stats["accepted_candidates"] == 0


def test_real_goofish_logged_in_fixture_extracts_live_listings():
    adapter = XianyuAdapter(live_enabled=True)
    fixture = Path(__file__).parent / "fixtures" / "product_selection" / "goofish_logged_in_huawei_search.html"
    html = fixture.read_text(encoding="utf-8", errors="ignore")

    listings = adapter._extract_listings(
        html,
        "huawei",
        base_url=adapter.search_url_template.format(query="huawei"),
        source="fixture",
    )

    assert len(listings) >= 3
    assert adapter._last_extraction_stats["accepted_candidates"] >= 3
    assert any(listing.price_low is not None for listing in listings)
    assert all("goofish.com/item?id=" in listing.url for listing in listings[:3])


def test_real_goofish_detail_fixture_extracts_detail_fields():
    adapter = XianyuAdapter(live_enabled=True)
    fixture = Path(__file__).parent / "fixtures" / "product_selection" / "goofish_detail_huawei_item.html"
    html = fixture.read_text(encoding="utf-8", errors="ignore")

    detail = adapter.extract_detail_snapshot_fields(html)

    assert detail["title"]
    assert "Mate X6" in str(detail["title"])
    assert detail["item_id"] == "1046552914070"
    assert detail["price_low"] == 7599.0
    assert detail["sales_volume"] == 907
    assert detail["seller_name"] == "崇左手机电脑上门回收维修"
    assert detail["seller_type"] == "personal"


def test_real_goofish_detail_fixture_enriches_matching_live_listing():
    adapter = XianyuAdapter(live_enabled=True)
    search_fixture = Path(__file__).parent / "fixtures" / "product_selection" / "goofish_logged_in_huawei_search.html"
    detail_fixture = Path(__file__).parent / "fixtures" / "product_selection" / "goofish_detail_huawei_item.html"
    search_html = search_fixture.read_text(encoding="utf-8", errors="ignore")
    detail_html = detail_fixture.read_text(encoding="utf-8", errors="ignore")
    rendered_fragment = extract_goofish_listing_fragment(search_html, "1046552914070")

    listings = adapter.search_marketplace(
        "Mate X6",
        query_type="keyword",
        rendered_snapshot_html=rendered_fragment,
    )["items"]
    target = next(item for item in listings if "id=1046552914070" in item["source_urls"][0])

    enriched = adapter.enrich_candidate_with_detail_snapshot(target, detail_html)

    assert enriched["price_low"] == 7599.0
    assert enriched["sales_volume"] == 907
    assert enriched["seller_type"] == "personal"
    assert enriched["source_diagnostics"]["detail_snapshot_enriched"] is True
    assert any(signal["signal_type"] == "detail_snapshot_listing" for signal in enriched["signals"])


def test_service_resolves_detail_snapshot_manifest_path(data_manager, tmp_path):
    fixture_root = Path(__file__).parent / "fixtures" / "product_selection"
    search_html = (fixture_root / "goofish_logged_in_huawei_search.html").read_text(encoding="utf-8", errors="ignore")
    detail_html = (fixture_root / "goofish_detail_huawei_item.html").read_text(encoding="utf-8", errors="ignore")
    rendered_fragment = extract_goofish_listing_fragment(search_html, "1046552914070")

    detail_dir = tmp_path / "goofish_detail_pages"
    detail_dir.mkdir(parents=True, exist_ok=True)
    detail_path = detail_dir / "1046552914070.html"
    detail_path.write_text(detail_html, encoding="utf-8")
    manifest_path = tmp_path / "goofish_detail_pages.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "item_id": "1046552914070",
                        "url": "https://www.goofish.com/item?id=1046552914070&categoryId=126862528",
                        "path": str(detail_path),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = ProductSelectionService(ProductSelectionRepository(data_manager.db_path))
    service.xianyu_adapter.live_enabled = True

    result = service.start_research_job(
        query_type="keyword",
        query_text="Mate X6",
        platform_scope="xianyu",
        rendered_snapshot_html=rendered_fragment,
        detail_snapshot_manifest_path=str(manifest_path),
    )

    target = next(item for item in result["items"] if "id=1046552914070" in item["source_urls"][0])
    assert target["price_low"] == 7599.0
    assert target["sales_volume"] == 907
    assert target["source_diagnostics"]["detail_snapshot_enriched"] is True


def test_selection_query_tool_loads_local_snapshot_and_manifest_paths(data_manager, tmp_path):
    fixture_root = Path(__file__).parent / "fixtures" / "product_selection"
    search_html = (fixture_root / "goofish_logged_in_huawei_search.html").read_text(encoding="utf-8", errors="ignore")
    detail_html = (fixture_root / "goofish_detail_huawei_item.html").read_text(encoding="utf-8", errors="ignore")
    rendered_fragment = extract_goofish_listing_fragment(search_html, "1046552914070")

    snapshot_path = tmp_path / "goofish-rendered-search.html"
    snapshot_path.write_text(rendered_fragment, encoding="utf-8")
    detail_dir = tmp_path / "goofish_detail_pages"
    detail_dir.mkdir(parents=True, exist_ok=True)
    detail_path = detail_dir / "1046552914070.html"
    detail_path.write_text(detail_html, encoding="utf-8")
    manifest_path = tmp_path / "goofish_detail_pages.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "item_id": "1046552914070",
                        "url": "https://www.goofish.com/item?id=1046552914070&categoryId=126862528",
                        "path": str(detail_path),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = ProductSelectionService(ProductSelectionRepository(data_manager.db_path))
    service.xianyu_adapter.live_enabled = True
    tool = SelectionQueryTool(service)

    result = tool.run(
        session=build_session(),
        user_message=f"用闲鱼 {snapshot_path} 和 {manifest_path} 看一下 Mate X6 还值不值得做",
    )

    assert result["local_inputs"]["rendered_snapshot_path"] == str(snapshot_path.resolve())
    assert result["local_inputs"]["detail_snapshot_manifest_path"] == str(manifest_path.resolve())
    assert "Mate X6" in result["query_text"]
    assert str(snapshot_path) not in result["query_text"]
    assert str(manifest_path) not in result["query_text"]
    target = next(item for item in result["items"] if "id=1046552914070" in item["source_urls"][0])
    assert target["price_low"] == 7599.0
    assert target["source_diagnostics"]["detail_snapshot_enriched"] is True


def test_live_adapter_accepts_rendered_snapshot_input():
    adapter = TaobaoAdapter(live_enabled=True)
    snapshot_html = """
        <html>
          <body>
            <div class="item">
              <a href="https://item.taobao.com/item.htm?id=501">宠物饮水机旗舰店循环款</a>
              <span>官方旗舰店 ￥109 月销 420 16家在卖</span>
            </div>
            <div class="item">
              <a href="https://item.taobao.com/item.htm?id=502">宠物饮水机静音基础款</a>
              <span>个人闲置 79元</span>
            </div>
          </body>
        </html>
    """

    result = adapter.search_marketplace(
        "宠物饮水机",
        query_type="keyword",
        rendered_snapshot_html=snapshot_html,
    )

    assert result["mode"] == "live"
    assert result["diagnostics"]["extraction_stats"]["source"] == "rendered_snapshot"
    assert result["items"][0]["sales_volume"] == 420
    assert result["items"][0]["seller_count"] == 16


def test_live_adapter_loads_cookie_map_from_browser_export(tmp_path):
    adapter = TaobaoAdapter(live_enabled=True)
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        """
        {
          "cookies": [
            {"name": "sessionid", "value": "abc123", "domain": ".taobao.com"},
            {"name": "ignored", "value": "zzz", "domain": ".example.com"}
          ]
        }
        """,
        encoding="utf-8",
    )

    cookies = adapter._load_cookie_map(
        str(cookie_file),
        url="https://s.taobao.com/search?q=test",
    )

    assert cookies == {"sessionid": "abc123"}
