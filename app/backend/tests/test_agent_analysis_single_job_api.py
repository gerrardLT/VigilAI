"""
Task 6 tests for manual single-item agent-analysis job orchestration.
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
from models import Activity, ActivityDates, Category, Prize, SourceStatus  # noqa: E402


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


@pytest.fixture
def seeded_activity(data_manager):
    source = data_manager.get_sources_status()[0]
    data_manager.update_source_status(source.id, SourceStatus.SUCCESS, activity_count=8)
    now = datetime.now()
    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/manual-single-job"),
        title="Solo bug bounty with reward ambiguity",
        description="Official organizer offers reward payout, but the exact cap needs verification.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/manual-single-job",
        category=Category.BOUNTY,
        prize=Prize(amount=500, currency="USD", description="Reward pool"),
        dates=ActivityDates(deadline=now + timedelta(days=7)),
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)
    loaded = data_manager.get_activity_by_id(activity.id)
    assert loaded is not None
    return loaded


def test_manual_single_job_runs_screening_research_verdict_and_safety(client, seeded_activity):
    response = client.post(
        "/api/agent-analysis/jobs",
        json={"scope_type": "single", "trigger_type": "manual", "activity_ids": [seeded_activity.id]},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["scope_type"] == "single"
    assert body["trigger_type"] == "manual"
    assert body["item_count"] == 1
    assert body["items"][0]["activity_id"] == seeded_activity.id
    assert body["items"][0]["draft"]["status"] in {"pass", "watch", "reject", "insufficient_evidence"}
    assert {step["step_type"] for step in body["items"][0]["steps"]} >= {"screening", "verdict"}
    assert "raw_chain_of_thought" not in body["items"][0]["draft"]

    detail_response = client.get(f"/api/agent-analysis/jobs/{body['id']}")
    item_response = client.get(f"/api/agent-analysis/items/{body['items'][0]['id']}")

    assert detail_response.status_code == 200
    assert item_response.status_code == 200
    assert detail_response.json()["id"] == body["id"]
    assert item_response.json()["id"] == body["items"][0]["id"]
    assert item_response.json()["draft"]["status"] == body["items"][0]["draft"]["status"]
