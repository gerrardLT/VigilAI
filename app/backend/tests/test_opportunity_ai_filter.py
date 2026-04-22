"""
Opportunity AI filter tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app  # noqa: E402
from data_manager import DataManager  # noqa: E402
from models import Activity, ActivityDates, Category, Prize  # noqa: E402
from analysis.opportunity_ai_filter import filter_opportunities_with_ai  # noqa: E402


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


def create_activity(
    data_manager: DataManager,
    *,
    url: str,
    title: str,
    description: str,
    location: str = "Remote",
) -> Activity:
    source = data_manager.get_sources_status()[0]
    now = datetime.now()
    return Activity(
        id=Activity.generate_id(source.id, url),
        title=title,
        description=description,
        full_content=description,
        source_id=source.id,
        source_name=source.name,
        url=url,
        category=Category.HACKATHON,
        tags=["ai"],
        prize=Prize(amount=1500, currency="USD", description="Guaranteed reward"),
        dates=ActivityDates(deadline=now + timedelta(days=5)),
        location=location,
        created_at=now,
        updated_at=now,
    )


def test_ai_filter_rejects_large_candidate_sets():
    with pytest.raises(ValueError, match="candidate limit"):
        filter_opportunities_with_ai(
            candidates=[{"id": str(index)} for index in range(201)],
            query="只保留适合独立开发者的机会",
        )


def test_ai_filter_returns_only_matched_items(monkeypatch):
    monkeypatch.setattr(
        "analysis.opportunity_ai_filter._call_ai_provider",
        lambda **_: {
            "parsed_intent_summary": "筛选适合单人开发的机会",
            "reason_summary": "优先保留单人友好且奖励明确的机会",
            "items": [
                {
                    "id": "activity-1",
                    "keep": True,
                    "reason": "适合单人开发，奖励明确",
                    "confidence": "high",
                    "uncertainties": [],
                },
                {
                    "id": "activity-2",
                    "keep": False,
                    "reason": "需要团队协作",
                    "confidence": "high",
                    "uncertainties": [],
                },
            ],
        },
    )

    result = filter_opportunities_with_ai(
        candidates=[
            {"id": "activity-1", "title": "Solo"},
            {"id": "activity-2", "title": "Team"},
        ],
        query="只保留适合独立开发者的机会",
    )

    assert result["matched_count"] == 1
    assert result["discarded_count"] == 1
    assert result["items"][0]["id"] == "activity-1"
    assert result["items"][0]["ai_match_reason"] == "适合单人开发，奖励明确"


def test_ai_filter_endpoint_returns_only_matched_items(client, data_manager, monkeypatch):
    kept = create_activity(
        data_manager,
        url="https://example.com/solo-remote",
        title="Solo Remote Hackathon",
        description="Individual developers can submit a small fix remotely and receive guaranteed reward payout within 7 days.",
    )
    dropped = create_activity(
        data_manager,
        url="https://example.com/team-offline",
        title="Team Offline Contest",
        description="Team required and long-form application review cycle.",
        location="Shanghai",
    )
    data_manager.add_activity(kept)
    data_manager.add_activity(dropped)

    monkeypatch.setattr(
        "api.filter_opportunities_with_ai",
        lambda *, candidates, query: {
            "query": query,
            "parsed_intent_summary": "筛选适合单人开发的机会",
            "reason_summary": "优先保留单人友好的机会",
            "candidate_count": len(candidates),
            "matched_count": 1,
            "discarded_count": len(candidates) - 1,
            "items": [
                {
                    "id": kept.id,
                    "ai_match_reason": "适合单人开发，且支持远程参与",
                    "ai_match_confidence": "high",
                    "uncertainties": [],
                }
            ],
        },
    )

    response = client.post(
        "/api/activities/ai-filter",
        json={
            "base_filters": {"category": "hackathon"},
            "query": "只保留适合独立开发者的机会",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_count"] == 1
    assert payload["discarded_count"] == 1
    assert payload["items"][0]["id"] == kept.id
    assert payload["items"][0]["ai_match_reason"] == "适合单人开发，且支持远程参与"


def test_ai_filter_endpoint_returns_chinese_error_when_candidate_limit_exceeded(
    client,
    data_manager,
    monkeypatch,
):
    for index in range(3):
        data_manager.add_activity(
            create_activity(
                data_manager,
                url=f"https://example.com/limit-{index}",
                title=f"Activity {index}",
                description="Individual developers can submit a small fix remotely and receive guaranteed reward payout within 7 days.",
            )
        )

    monkeypatch.setattr("api.AI_FILTER_MAX_CANDIDATES", 2)

    response = client.post(
        "/api/activities/ai-filter",
        json={
            "base_filters": {"category": "hackathon"},
            "query": "只保留适合独立开发者的机会",
        },
    )

    assert response.status_code == 400
    assert "当前候选机会过多" in response.json()["detail"]
