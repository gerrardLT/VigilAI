"""
V2 foundation layer tests.
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
from models import Activity, ActivityDates, Prize, SourceStatus  # noqa: E402


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
    source_index: int = 0,
    title: str = "Ranked Opportunity",
    url: str = "https://example.com/opportunity",
    description: str = "A high-signal opportunity worth tracking.",
    location: str | None = "Remote",
    prize_amount: float | None = 1000,
    category: str = "hackathon",
    created_at: datetime | None = None,
    deadline: datetime | None = None,
) -> Activity:
    source = data_manager.get_sources_status()[source_index]
    created_at = created_at or datetime.now()
    deadline = deadline or (created_at + timedelta(days=2))

    return Activity(
        id=Activity.generate_id(source.id, url),
        title=title,
        description=description,
        full_content=f"{description} Full content for deeper review.",
        source_id=source.id,
        source_name=source.name,
        url=url,
        category=category,
        tags=["ai", "automation"],
        prize=Prize(amount=prize_amount, currency="USD", description="Cash prize") if prize_amount is not None else None,
        dates=ActivityDates(deadline=deadline),
        location=location,
        created_at=created_at,
        updated_at=created_at,
    )


def test_stats_include_recent_activities_and_last_update(data_manager):
    activity = create_activity(data_manager)
    data_manager.add_activity(activity)

    stats = data_manager.get_stats()

    assert stats.total_activities == 1
    assert stats.recent_activities == 1
    assert stats.last_update is not None


def test_activity_enrichment_round_trip_persists_v2_fields(data_manager):
    source = data_manager.get_sources_status()[0]
    data_manager.update_source_status(source.id, SourceStatus.SUCCESS, activity_count=3)

    activity = create_activity(data_manager)
    data_manager.add_activity(activity)

    loaded = data_manager.get_activity_by_id(activity.id)

    assert loaded.summary == activity.description
    assert loaded.deadline_level == "urgent"
    assert loaded.trust_level == "high"
    assert loaded.score is not None
    assert loaded.score > 0
    assert loaded.score_reason
    assert loaded.updated_fields == []


def test_updated_fields_captured_when_existing_activity_changes(data_manager):
    activity = create_activity(
        data_manager,
        title="Original Title",
        url="https://example.com/updated",
        description="Original description",
    )
    data_manager.add_activity(activity)

    updated = create_activity(
        data_manager,
        title="Updated Title",
        url="https://example.com/updated",
        description="Updated description",
    )
    data_manager.add_activity(updated)

    loaded = data_manager.get_activity_by_id(activity.id)

    assert set(loaded.updated_fields) >= {"title", "description", "full_content"}


def test_tracking_crud_round_trip(data_manager):
    activity = create_activity(data_manager, url="https://example.com/tracking")
    data_manager.add_activity(activity)

    created = data_manager.upsert_tracking_item(
        activity.id,
        {
            "is_favorited": True,
            "status": "tracking",
            "notes": "Investigate requirements",
            "next_action": "Submit application",
            "remind_at": (datetime.now() + timedelta(days=1)).isoformat(),
        },
    )
    fetched = data_manager.get_tracking_item(activity.id)
    items = data_manager.get_tracking_items()

    assert created.activity_id == activity.id
    assert fetched["status"] == "tracking"
    assert fetched["is_favorited"] is True
    assert items[0]["activity"]["id"] == activity.id

    updated = data_manager.upsert_tracking_item(
        activity.id,
        {
            "status": "done",
            "notes": "Submitted",
        },
    )

    assert updated.status == "done"
    assert data_manager.delete_tracking_item(activity.id) is True
    assert data_manager.get_tracking_item(activity.id) is None


def test_generate_digest_reuses_existing_digest_for_same_day(data_manager):
    now = datetime.now()
    activity = create_activity(
        data_manager,
        url="https://example.com/digest-a",
        created_at=now,
        deadline=now + timedelta(days=1),
    )
    data_manager.add_activity(activity)

    digest = data_manager.generate_digest(now.date().isoformat())
    same_digest = data_manager.generate_digest(now.date().isoformat())

    assert digest.id == same_digest.id
    assert activity.id in digest.item_ids
    assert data_manager.get_digest_by_id(digest.id).id == digest.id
    assert any(item.id == digest.id for item in data_manager.get_digests())


def test_digest_candidates_are_persisted_and_preferred_in_generated_digest(data_manager):
    now = datetime.now()
    preferred = create_activity(
        data_manager,
        url="https://example.com/digest-candidate",
        title="Candidate Opportunity",
        created_at=now,
        deadline=now + timedelta(days=1),
    )
    other = create_activity(
        data_manager,
        source_index=1,
        url="https://example.com/digest-other",
        title="Other Opportunity",
        created_at=now,
        deadline=now + timedelta(days=2),
    )
    data_manager.add_activity(preferred)
    data_manager.add_activity(other)

    data_manager.add_digest_candidate(preferred.id, now.date().isoformat())
    data_manager.add_digest_candidate(preferred.id, now.date().isoformat())

    candidates = data_manager.get_digest_candidates(now.date().isoformat())
    digest = data_manager.generate_digest(now.date().isoformat())

    assert [candidate.id for candidate in candidates] == [preferred.id]
    assert digest.item_ids == [preferred.id]
    assert "Candidate Opportunity" in digest.content


def test_workspace_aggregation_has_expected_sections(data_manager):
    now = datetime.now()
    first = create_activity(
        data_manager,
        url="https://example.com/workspace-1",
        created_at=now,
        deadline=now + timedelta(days=1),
    )
    second = create_activity(
        data_manager,
        source_index=1,
        title="Needs Attention",
        url="https://example.com/workspace-2",
        created_at=now - timedelta(days=1),
        deadline=now + timedelta(days=3),
    )
    data_manager.add_activity(first)
    data_manager.add_activity(second)
    source = data_manager.get_sources_status()[1]
    data_manager.update_source_status(source.id, SourceStatus.ERROR, error_message="source failed")
    data_manager.upsert_tracking_item(first.id, {"status": "tracking", "is_favorited": True})
    data_manager.generate_digest(now.date().isoformat())

    workspace = data_manager.get_workspace()

    assert set(workspace.keys()) == {
        "overview",
        "top_opportunities",
        "digest_preview",
        "trends",
        "alert_sources",
        "first_actions",
        "analysis_overview",
        "blocked_opportunities",
    }
    assert workspace["overview"]["total_activities"] >= 2
    assert workspace["top_opportunities"]
    assert workspace["digest_preview"] is not None
    assert workspace["trends"]
    assert workspace["alert_sources"]
    assert workspace["first_actions"]
    assert workspace["analysis_overview"]["total"] >= 2
    assert isinstance(workspace["blocked_opportunities"], list)


def test_stats_endpoint_returns_normalized_contract(client, data_manager):
    data_manager.add_activity(create_activity(data_manager, url="https://example.com/api-stats"))

    response = client.get("/api/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_activities"] == 1
    assert payload["recent_activities"] == 1
    assert payload["last_update"] is not None


def test_activity_detail_endpoint_returns_v2_fields(client, data_manager):
    primary = create_activity(data_manager, url="https://example.com/detail")
    related = create_activity(
        data_manager,
        url="https://example.com/detail-related",
        title="Related Opportunity",
    )
    data_manager.add_activity(primary)
    data_manager.add_activity(related)
    data_manager.upsert_tracking_item(primary.id, {"status": "tracking", "is_favorited": True})
    data_manager.add_digest_candidate(primary.id)

    response = client.get(f"/api/activities/{primary.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == primary.description
    assert payload["tracking"]["status"] == "tracking"
    assert payload["is_digest_candidate"] is True
    assert payload["timeline"]
    assert payload["related_items"]


def test_sources_endpoint_returns_health_fields(client, data_manager):
    healthy_source = data_manager.get_sources_status()[0]
    failing_source = data_manager.get_sources_status()[1]
    data_manager.update_source_status(healthy_source.id, SourceStatus.SUCCESS, activity_count=5)
    data_manager.update_source_status(failing_source.id, SourceStatus.ERROR, error_message="timeout")

    response = client.get("/api/sources")

    assert response.status_code == 200
    payload = response.json()
    healthy_item = next(item for item in payload if item["id"] == healthy_source.id)
    failing_item = next(item for item in payload if item["id"] == failing_source.id)
    assert healthy_item["health_score"] >= 80
    assert healthy_item["freshness_level"] == "fresh"
    assert healthy_item["needs_attention"] is False
    assert failing_item["health_score"] <= 40
    assert failing_item["needs_attention"] is True
    assert failing_item["freshness_level"] in {"critical", "never"}


def test_tracking_crud_endpoints_work(client, data_manager):
    activity = create_activity(data_manager, url="https://example.com/api-tracking")
    data_manager.add_activity(activity)

    created = client.post(
        f"/api/tracking/{activity.id}",
        json={"status": "saved", "is_favorited": True},
    )
    listed = client.get("/api/tracking")
    updated = client.patch(
        f"/api/tracking/{activity.id}",
        json={"status": "done", "notes": "Applied"},
    )
    deleted = client.delete(f"/api/tracking/{activity.id}")

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()[0]["activity"]["id"] == activity.id
    assert updated.json()["status"] == "done"
    assert deleted.status_code == 200


def test_digest_endpoints_work(client, data_manager):
    activity = create_activity(data_manager, url="https://example.com/api-digest")
    data_manager.add_activity(activity)

    generated = client.post("/api/digests/generate")
    digest_id = generated.json()["id"]
    listed = client.get("/api/digests")
    detail = client.get(f"/api/digests/{digest_id}")
    sent = client.post(f"/api/digests/{digest_id}/send", json={"send_channel": "manual"})

    assert generated.status_code == 200
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == digest_id
    assert detail.status_code == 200
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"


def test_digest_candidate_endpoints_work(client, data_manager):
    activity = create_activity(data_manager, url="https://example.com/api-digest-candidate")
    data_manager.add_activity(activity)

    created = client.post(f"/api/digests/candidates/{activity.id}")
    listed = client.get("/api/digests/candidates")
    deleted = client.delete(f"/api/digests/candidates/{activity.id}")

    assert created.status_code == 200
    assert created.json()["success"] is True
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == activity.id
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True


def test_workspace_endpoint_returns_aggregate_sections(client, data_manager):
    data_manager.add_activity(create_activity(data_manager, url="https://example.com/api-workspace"))

    response = client.get("/api/workspace")

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "overview",
        "top_opportunities",
        "digest_preview",
        "trends",
        "alert_sources",
        "first_actions",
        "analysis_overview",
        "blocked_opportunities",
    }


def test_activity_list_supports_tracking_and_priority_filters(data_manager):
    tracked = create_activity(
        data_manager,
        url="https://example.com/filter-tracked",
        deadline=datetime.now() + timedelta(hours=12),
    )
    other = create_activity(
        data_manager,
        source_index=1,
        title="Lower Priority",
        url="https://example.com/filter-other",
        deadline=datetime.now() + timedelta(days=14),
    )
    data_manager.add_activity(tracked)
    data_manager.add_activity(other)
    data_manager.update_source_status(tracked.source_id, SourceStatus.SUCCESS, activity_count=2)
    data_manager.update_source_status(other.source_id, SourceStatus.ERROR, error_message="down")
    data_manager.upsert_tracking_item(tracked.id, {"status": "tracking", "is_favorited": True})

    tracked_only, tracked_total = data_manager.get_activities(filters={"is_tracking": True})
    favorites_only, favorites_total = data_manager.get_activities(filters={"is_favorited": True})
    urgent_only, urgent_total = data_manager.get_activities(filters={"deadline_level": "urgent"})
    trusted_only, trusted_total = data_manager.get_activities(filters={"trust_level": "high"})

    assert tracked_total == 1
    assert tracked_only[0].id == tracked.id
    assert favorites_total == 1
    assert favorites_only[0].id == tracked.id
    assert urgent_total == 1
    assert urgent_only[0].id == tracked.id
    assert trusted_total == 1
    assert trusted_only[0].id == tracked.id


def test_activity_list_supports_extended_fixed_filters(data_manager):
    solo = create_activity(
        data_manager,
        url="https://example.com/filter-solo-remote",
        title="Solo Remote Hackathon",
        description="Individual developers can submit a small fix remotely and receive guaranteed reward payout within 7 days.",
        location="Remote",
        prize_amount=1500,
    )
    team = create_activity(
        data_manager,
        source_index=1,
        url="https://example.com/filter-team-offline",
        title="Team Offline Contest",
        description="Team required and long-form application review cycle with monthly payout.",
        location="Shanghai",
        prize_amount=200,
    )
    data_manager.add_activity(solo)
    data_manager.add_activity(team)

    matched, total = data_manager.get_activities(
        filters={
            "prize_range": "500-2000",
            "solo_friendliness": "solo_friendly",
            "reward_clarity": "high",
            "effort_level": "low",
            "remote_mode": "remote",
        }
    )

    assert total == 1
    assert matched[0].id == solo.id


def test_activity_list_endpoint_accepts_extended_fixed_filters(client, data_manager):
    activity = create_activity(
        data_manager,
        url="https://example.com/api-fixed-filters",
        title="Solo Remote Builder Sprint",
        description="Individual developers can join remotely for a small fix with guaranteed reward payout within 7 days.",
        location="Online / Remote",
        prize_amount=1000,
    )
    data_manager.add_activity(activity)

    response = client.get(
        "/api/activities",
        params={
            "prize_range": "500-2000",
            "solo_friendliness": "solo_friendly",
            "reward_clarity": "high",
            "effort_level": "low",
            "remote_mode": "remote",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == activity.id


def test_activity_list_endpoint_accepts_v2_filters(client, data_manager):
    tracked = create_activity(
        data_manager,
        url="https://example.com/api-filter-tracked",
        deadline=datetime.now() + timedelta(hours=12),
    )
    other = create_activity(
        data_manager,
        source_index=1,
        title="Other Opportunity",
        url="https://example.com/api-filter-other",
        deadline=datetime.now() + timedelta(days=10),
    )
    data_manager.add_activity(tracked)
    data_manager.add_activity(other)
    data_manager.update_source_status(tracked.source_id, SourceStatus.SUCCESS, activity_count=1)
    data_manager.upsert_tracking_item(tracked.id, {"status": "tracking", "is_favorited": True})

    response = client.get(
        "/api/activities",
        params={"is_tracking": "true", "deadline_level": "urgent", "sort_by": "score"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == tracked.id
