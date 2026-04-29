"""
Product-selection API tests.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import uuid

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app  # noqa: E402
from data_manager import DataManager  # noqa: E402
from product_selection.repository import ProductSelectionRepository  # noqa: E402
from product_selection.service import ProductSelectionService  # noqa: E402


def build_dual_platform_snapshot(query_text: str) -> str:
    return f"""
    <html>
      <body>
        <div class="item">
          <a href="https://item.taobao.com/item.htm?id=101">{query_text} Taobao Pro</a>
          <span>官方旗舰店 ￥109 月销 420 16家在卖</span>
        </div>
        <div class="feeds-item">
          <a href="https://www.goofish.com/item?id=202">{query_text} Xianyu Listing</a>
          <span>个人闲置 现价 58元 12人想要</span>
        </div>
      </body>
    </html>
    """


def extract_goofish_listing_fragment(html: str, item_id: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    anchor = soup.select_one(f"a[href*='goofish.com/item?id={item_id}']")
    assert anchor is not None
    return f"<html><body>{str(anchor)}</body></html>"


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


def create_research_job(client: TestClient, query_text: str = "pet water fountain") -> dict:
    response = client.post(
        "/api/product-selection/research-jobs",
        json={
            "query_type": "keyword",
            "query_text": query_text,
            "platform_scope": "both",
            "rendered_snapshot_html": build_dual_platform_snapshot(query_text),
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_research_job_returns_query_and_live_items(client):
    payload = create_research_job(client)

    assert payload["job"]["query_type"] == "keyword"
    assert payload["job"]["platform_scope"] == "both"
    assert payload["job"]["status"] == "completed"
    assert payload["total"] >= 2
    assert {item["platform"] for item in payload["items"]} == {"taobao", "xianyu"}
    assert payload["source_summary"]["overall_mode"] == "live"
    assert "mode_counts" in payload["source_summary"]
    assert "extraction_stats_summary" in payload["source_summary"]
    assert "seller_mix" in payload["source_summary"]
    assert all(item["source_mode"] == "live" for item in payload["items"])
    assert all(isinstance(item["source_diagnostics"], dict) for item in payload["items"])


def test_list_opportunities_filters_by_platform(client):
    create_research_job(client, query_text="storage box")

    response = client.get("/api/product-selection/opportunities", params={"platform": "taobao"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert all(item["platform"] == "taobao" for item in payload["items"])
    assert payload["source_summary"]["overall_mode"] == "live"


def test_list_opportunities_returns_no_fallback_rows_when_only_live_results_are_stored(client):
    create_research_job(client, query_text="desk lamp")

    live_response = client.get("/api/product-selection/opportunities", params={"source_mode": "live"})
    fallback_response = client.get(
        "/api/product-selection/opportunities",
        params={"source_mode": "fallback", "fallback_reason": "search_shell_only"},
    )

    assert live_response.status_code == 200
    assert fallback_response.status_code == 200

    live_payload = live_response.json()
    fallback_payload = fallback_response.json()

    assert all(item["source_mode"] == "live" for item in live_payload["items"])
    assert fallback_payload["total"] == 0
    assert fallback_payload["items"] == []


def test_opportunity_detail_and_tracking_round_trip(client):
    job_payload = create_research_job(client, query_text="car organizer")
    opportunity_id = job_payload["items"][0]["id"]

    detail_response = client.get(f"/api/product-selection/opportunities/{opportunity_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["signals"]
    assert detail_payload["query"]["id"] == job_payload["job"]["id"]
    assert detail_payload["tracking"] is None
    assert detail_payload["source_mode"] == "live"
    assert isinstance(detail_payload["source_diagnostics"], dict)
    assert "sales_volume" in detail_payload
    assert "seller_type" in detail_payload

    tracking_response = client.post(
        f"/api/product-selection/tracking/{opportunity_id}",
        json={
            "is_favorited": True,
            "status": "tracking",
            "notes": "Review competitor comments first.",
            "next_action": "Sample 20 competing SKUs.",
        },
    )
    assert tracking_response.status_code == 200
    assert tracking_response.json()["status"] == "tracking"

    refreshed_detail = client.get(f"/api/product-selection/opportunities/{opportunity_id}")
    assert refreshed_detail.status_code == 200
    assert refreshed_detail.json()["tracking"]["next_action"] == "Sample 20 competing SKUs."


def test_workspace_and_tracking_list_summarize_selection_state(client):
    job_payload = create_research_job(client, query_text="desk fan")
    tracked_id = job_payload["items"][0]["id"]

    client.post(
        f"/api/product-selection/tracking/{tracked_id}",
        json={"status": "tracking", "is_favorited": True},
    )

    tracking_response = client.get("/api/product-selection/tracking", params={"status": "tracking"})
    workspace_response = client.get("/api/product-selection/workspace")

    assert tracking_response.status_code == 200
    assert len(tracking_response.json()) == 1
    assert tracking_response.json()[0]["opportunity"]["id"] == tracked_id

    assert workspace_response.status_code == 200
    workspace_payload = workspace_response.json()
    assert workspace_payload["overview"]["query_count"] >= 1
    assert workspace_payload["overview"]["tracked_count"] == 1
    assert workspace_payload["overview"]["favorited_count"] == 1
    assert workspace_payload["top_opportunities"]
    assert workspace_payload["source_summary"]["overall_mode"] == "live"
    assert workspace_payload["top_opportunities_source_summary"]["overall_mode"] == "live"
    assert workspace_payload["tracking_queue_source_summary"]["overall_mode"] == "live"
    assert "extraction_stats_summary" in workspace_payload["source_summary"]
    assert "seller_mix" in workspace_payload["source_summary"]


def test_tracking_list_filters_return_empty_for_fallback_when_only_live_results_are_stored(client):
    job_payload = create_research_job(client, query_text="lamp shade")
    tracked_id = job_payload["items"][0]["id"]

    client.post(
        f"/api/product-selection/tracking/{tracked_id}",
        json={"status": "tracking", "is_favorited": True},
    )

    response = client.get(
        "/api/product-selection/tracking",
        params={"source_mode": "fallback", "fallback_reason": "search_shell_only"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_research_job_fails_closed_when_live_extraction_has_no_production_safe_results(client):
    response = client.post(
        "/api/product-selection/research-jobs",
        json={
            "query_type": "keyword",
            "query_text": "pet water fountain",
            "platform_scope": "taobao",
            "rendered_snapshot_html": "<html><body><div class='boneClass_cardListWrapper'></div></body></html>",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "failed"
    assert payload["total"] == 0
    assert payload["items"] == []
    assert payload["source_summary"]["overall_mode"] == "failed"
    assert "search_shell_only" in payload["source_summary"]["fallback_reasons"]


def test_research_job_accepts_rendered_and_detail_snapshots(client):
    fixture_root = Path(__file__).parent / "fixtures" / "product_selection"
    search_html = (fixture_root / "goofish_logged_in_huawei_search.html").read_text(encoding="utf-8", errors="ignore")
    detail_html = (fixture_root / "goofish_detail_huawei_item.html").read_text(encoding="utf-8", errors="ignore")
    rendered_fragment = extract_goofish_listing_fragment(search_html, "1046552914070")
    service = ProductSelectionService(ProductSelectionRepository(app.state.data_manager.db_path))
    service.taobao_adapter.live_enabled = True
    service.xianyu_adapter.live_enabled = True
    app.state.product_selection_repository = service.repository
    app.state.product_selection_service = service

    response = client.post(
        "/api/product-selection/research-jobs",
        json={
            "query_type": "keyword",
            "query_text": "Mate X6",
            "platform_scope": "xianyu",
            "rendered_snapshot_html": rendered_fragment,
            "detail_snapshot_htmls": [detail_html],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    target = next(item for item in payload["items"] if "id=1046552914070" in item["source_urls"][0])
    assert target["source_mode"] == "live"
    assert target["price_low"] == 7599.0
    assert target["sales_volume"] == 907
    assert target["seller_type"] == "personal"
    assert target["source_diagnostics"]["detail_snapshot_enriched"] is True


def test_research_job_accepts_detail_snapshot_manifest_path(client, tmp_path):
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
                "platform": "xianyu",
                "query_text": "Mate X6",
                "detail_count": 1,
                "items": [
                    {
                        "item_id": "1046552914070",
                        "url": "https://www.goofish.com/item?id=1046552914070&categoryId=126862528",
                        "path": str(detail_path),
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = ProductSelectionService(ProductSelectionRepository(app.state.data_manager.db_path))
    service.taobao_adapter.live_enabled = True
    service.xianyu_adapter.live_enabled = True
    app.state.product_selection_repository = service.repository
    app.state.product_selection_service = service

    response = client.post(
        "/api/product-selection/research-jobs",
        json={
            "query_type": "keyword",
            "query_text": "Mate X6",
            "platform_scope": "xianyu",
            "rendered_snapshot_html": rendered_fragment,
            "detail_snapshot_manifest_path": str(manifest_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    target = next(item for item in payload["items"] if "id=1046552914070" in item["source_urls"][0])
    assert target["price_low"] == 7599.0
    assert target["sales_volume"] == 907
    assert target["source_diagnostics"]["detail_snapshot_enriched"] is True


def test_research_job_accepts_rendered_snapshot_path(client, tmp_path):
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
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = ProductSelectionService(ProductSelectionRepository(app.state.data_manager.db_path))
    service.taobao_adapter.live_enabled = True
    service.xianyu_adapter.live_enabled = True
    app.state.product_selection_repository = service.repository
    app.state.product_selection_service = service

    response = client.post(
        "/api/product-selection/research-jobs",
        json={
            "query_type": "keyword",
            "query_text": "Mate X6",
            "platform_scope": "xianyu",
            "rendered_snapshot_path": str(snapshot_path),
            "detail_snapshot_manifest_path": str(manifest_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    target = next(item for item in payload["items"] if "id=1046552914070" in item["source_urls"][0])
    assert target["price_low"] == 7599.0
    assert target["sales_volume"] == 907
    assert target["source_diagnostics"]["detail_snapshot_enriched"] is True
