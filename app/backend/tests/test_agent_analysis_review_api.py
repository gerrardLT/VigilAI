"""
Task 7 tests for review and writeback workflow.
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
def completed_job_item(client, data_manager):
    source = data_manager.get_sources_status()[0]
    data_manager.update_source_status(source.id, SourceStatus.SUCCESS, activity_count=8)
    now = datetime.now()
    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/review-job"),
        title="Solo bug bounty with reviewable draft",
        description="Official organizer offers reward payout, but the exact cap needs verification.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/review-job",
        category=Category.BOUNTY,
        prize=Prize(amount=500, currency="USD", description="Reward pool"),
        dates=ActivityDates(deadline=now + timedelta(days=7)),
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)

    created = client.post(
        "/api/agent-analysis/jobs",
        json={"scope_type": "single", "trigger_type": "manual", "activity_ids": [activity.id]},
    )
    assert created.status_code == 200
    item = created.json()["items"][0]
    return item


def test_approve_item_writes_draft_snapshot_back_to_activity(client, completed_job_item):
    response = client.post(
        f"/api/agent-analysis/items/{completed_job_item['id']}/approve",
        json={"review_note": "Looks good"},
    )

    body = response.json()
    refreshed = client.get(f"/api/activities/{completed_job_item['activity_id']}").json()

    assert response.status_code == 200
    assert body["review_action"] == "approved"
    assert refreshed["analysis_status"] == body["snapshot"]["status"]
    assert refreshed["analysis_current_run_id"] == completed_job_item["job_id"]


def test_reject_item_keeps_activity_snapshot_unchanged(client, completed_job_item):
    before = client.get(f"/api/activities/{completed_job_item['activity_id']}").json()

    response = client.post(
        f"/api/agent-analysis/items/{completed_job_item['id']}/reject",
        json={"review_note": "Need a human rewrite first"},
    )

    body = response.json()
    refreshed = client.get(f"/api/activities/{completed_job_item['activity_id']}").json()

    assert response.status_code == 200
    assert body["review_action"] == "rejected"
    assert refreshed["analysis_status"] == before["analysis_status"]
    assert refreshed["analysis_current_run_id"] == before["analysis_current_run_id"]
