"""
Product-selection API tests.
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app  # noqa: E402
from data_manager import DataManager  # noqa: E402


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


def create_research_job(client: TestClient, query_text: str = "宠物饮水机") -> dict:
    response = client.post(
        "/api/product-selection/research-jobs",
        json={
            "query_type": "keyword",
            "query_text": query_text,
            "platform_scope": "both",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_research_job_returns_query_and_seeded_items(client):
    payload = create_research_job(client)

    assert payload["job"]["query_type"] == "keyword"
    assert payload["job"]["platform_scope"] == "both"
    assert payload["job"]["status"] == "completed"
    assert payload["total"] >= 4
    assert {item["platform"] for item in payload["items"]} == {"taobao", "xianyu"}


def test_list_opportunities_filters_by_platform(client):
    create_research_job(client, query_text="收纳盒")

    response = client.get("/api/product-selection/opportunities", params={"platform": "taobao"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert all(item["platform"] == "taobao" for item in payload["items"])


def test_opportunity_detail_and_tracking_round_trip(client):
    job_payload = create_research_job(client, query_text="车载收纳")
    opportunity_id = job_payload["items"][0]["id"]

    detail_response = client.get(f"/api/product-selection/opportunities/{opportunity_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["signals"]
    assert detail_payload["query"]["id"] == job_payload["job"]["id"]
    assert detail_payload["tracking"] is None

    tracking_response = client.post(
        f"/api/product-selection/tracking/{opportunity_id}",
        json={
            "is_favorited": True,
            "status": "tracking",
            "notes": "先对比竞品评论",
            "next_action": "整理 20 个竞品样本",
        },
    )
    assert tracking_response.status_code == 200
    assert tracking_response.json()["status"] == "tracking"

    refreshed_detail = client.get(f"/api/product-selection/opportunities/{opportunity_id}")
    assert refreshed_detail.status_code == 200
    assert refreshed_detail.json()["tracking"]["next_action"] == "整理 20 个竞品样本"


def test_workspace_and_tracking_list_summarize_selection_state(client):
    job_payload = create_research_job(client, query_text="桌面风扇")
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
