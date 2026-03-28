"""
Task 8 tests for scheduled batch jobs and job listing APIs.
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
def seeded_batch_activities(data_manager):
    source = data_manager.get_sources_status()[0]
    data_manager.update_source_status(source.id, SourceStatus.SUCCESS, activity_count=12)
    now = datetime.now()
    created = []
    for index in range(3):
        activity = Activity(
            id=Activity.generate_id(source.id, f"https://example.com/batch-job-{index}"),
            title=f"Batch candidate {index}",
            description="Reward mentioned but exact payout still needs verification.",
            source_id=source.id,
            source_name=source.name,
            url=f"https://example.com/batch-job-{index}",
            category=Category.BOUNTY,
            prize=Prize(amount=250 + index * 50, currency="USD", description="Reward pool"),
            dates=ActivityDates(deadline=now + timedelta(days=10 + index)),
            created_at=now - timedelta(hours=index * 4),
            updated_at=now - timedelta(hours=index),
        )
        data_manager.add_activity(activity)
        created.append(activity)
    return created


def test_scheduled_batch_job_selects_new_updated_and_stale_items(client, seeded_batch_activities):
    response = client.post(
        "/api/agent-analysis/jobs",
        json={"scope_type": "batch", "trigger_type": "scheduled"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["scope_type"] == "batch"
    assert body["item_count"] >= 1
    assert any(item["needs_research"] for item in body["items"])


def test_job_list_endpoint_returns_batch_health(client, seeded_batch_activities):
    created = client.post(
        "/api/agent-analysis/jobs",
        json={"scope_type": "batch", "trigger_type": "scheduled"},
    )
    assert created.status_code == 200

    response = client.get("/api/agent-analysis/jobs")

    assert response.status_code == 200
    assert "items" in response.json()
    assert response.json()["items"][0]["scope_type"] == "batch"
