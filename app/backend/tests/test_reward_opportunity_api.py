"""API tests for the reward-opportunity bounded context."""

from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app  # noqa: E402
from data_manager import DataManager  # noqa: E402
from reward_opportunity.repository import RewardOpportunityRepository  # noqa: E402
import reward_opportunity.service as reward_service_module  # noqa: E402


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
    if hasattr(app.state, "reward_opportunity_repository"):
        delattr(app.state, "reward_opportunity_repository")
    if hasattr(app.state, "reward_opportunity_service"):
        delattr(app.state, "reward_opportunity_service")
    with TestClient(app) as test_client:
        yield test_client


def test_reward_overview_endpoint_returns_counts(client):
    response = client.get("/api/reward-opportunities/overview")
    assert response.status_code == 200
    payload = response.json()
    assert "source_count" in payload
    assert "opportunity_count" in payload


def test_reward_opportunities_list_endpoint_returns_items(client):
    response = client.get("/api/reward-opportunities")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload


def test_reward_operations_endpoint_returns_sources_and_jobs(client):
    repository = RewardOpportunityRepository(app.state.data_manager.db_path)
    feed_id = repository.upsert_source_feed(
        {
            "id": "source-ops-1",
            "name": "Ops Feed",
            "source_type": "web",
            "entry_url": "https://example.com/rewards",
            "status": "error",
            "last_error_message": "timeout",
        }
    )
    repository.create_crawl_job({"source_feed_id": feed_id, "status": "failed", "mode": "manual"})
    repository.update_crawl_job(
        repository.create_crawl_job({"source_feed_id": feed_id, "status": "completed", "mode": "manual"}),
        {
            "status": "completed",
            "document_count": 3,
            "candidate_count": 1,
            "opportunity_count": 1,
            "completed_at": "2026-05-01T10:10:00+00:00",
        },
    )
    response = client.get("/api/reward-opportunities/operations")
    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
    assert "recent_jobs" in payload
    assert payload["sources"][0]["health_score"] >= 0
    assert "health_level" in payload["sources"][0]


def test_reward_a2a_agent_cards_endpoint_returns_private_agents(client):
    response = client.get("/a2a/RewardVerdictAgent/.well-known/agent-card.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "RewardVerdictAgent"
    assert payload["metadata"]["discovery"] == "private"


def test_reward_a2a_browser_agent_uses_real_browser_collection(client):
    response = client.post(
        "/a2a/RewardBrowserInvestigatorAgent",
        json={
            "id": "task-browser-1",
            "params": {
                "data": {
                    "url": "data:text/html,<html><title>Reward FAQ</title><body>Reward FAQ Terms</body></html>",
                    "objective": "collect reward FAQ text",
                }
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["artifacts"][0]["parts"][0]["data"]
    assert data["ok"] is True
    assert "Reward FAQ" in data["data"]["text"]


def test_reward_discovery_endpoint_returns_candidates(client, monkeypatch):
    monkeypatch.setattr(
        reward_service_module,
        "discover_source_candidates",
        lambda _feeds, query_templates=None: [
            {
                "name": "github.com / example",
                "entry_url": "https://github.com/example/bounties",
                "source_platform": "github",
                "source_type": "web",
                "discovery_queries": ["task reward bounty campaign"],
                "reasons": ["matched scout query"],
                "score": 6,
            }
        ],
    )

    response = client.get("/api/reward-opportunities/discovery")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["source_platform"] == "github"


def test_reward_discovery_import_creates_source_feed(client):
    original_sync_single_source = reward_service_module.RewardOpportunityService.sync_single_source
    try:
        reward_service_module.RewardOpportunityService.sync_single_source = lambda self, source_feed_id, mode="manual": {
            "source_feed_id": source_feed_id,
            "job_id": "preview-job-1",
            "document_count": 2,
            "candidate_count": 1,
            "opportunity_count": 1,
            "error": None,
        }
        response = client.post(
            "/api/reward-opportunities/discovery/import",
            json={
                "name": "reddit.com / r",
                "entry_url": "https://reddit.com/r/airdrops",
                "source_type": "social",
                "source_platform": "reddit",
                "discovery_queries": ["reward referral"],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "reddit.com / r"
        assert payload["entry_url"] == "https://reddit.com/r/airdrops"
        assert payload["config"]["imported_from"] == "scout"
        assert payload["import_preview"]["job_id"] == "preview-job-1"
    finally:
        reward_service_module.RewardOpportunityService.sync_single_source = original_sync_single_source


def test_reward_discovery_settings_round_trip(client):
    response = client.put(
        "/api/reward-opportunities/discovery/settings",
        json={"query_templates": ["invite reward program", "task reward bounty campaign"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["query_templates"] == ["invite reward program", "task reward bounty campaign"]

    read_response = client.get("/api/reward-opportunities/discovery/settings")
    assert read_response.status_code == 200
    assert read_response.json()["query_templates"] == ["invite reward program", "task reward bounty campaign"]


def test_reward_single_source_sync_endpoint(client):
    repository = RewardOpportunityRepository(app.state.data_manager.db_path)
    feed_id = repository.upsert_source_feed(
        {
            "id": "source-sync-1",
            "name": "Sync Feed",
            "source_type": "web",
            "entry_url": "https://example.com/rewards",
        }
    )
    original_sync_single_source = reward_service_module.RewardOpportunityService.sync_single_source
    try:
        reward_service_module.RewardOpportunityService.sync_single_source = lambda self, source_feed_id, mode="manual": {
            "source_feed_id": source_feed_id,
            "job_id": "job-single-1",
            "document_count": 5,
            "candidate_count": 2,
            "opportunity_count": 1,
            "error": None,
        }
        response = client.post(f"/api/reward-opportunities/sync/{feed_id}")
        assert response.status_code == 200
        assert response.json()["job_id"] == "job-single-1"
    finally:
        reward_service_module.RewardOpportunityService.sync_single_source = original_sync_single_source


def test_reward_source_pause_and_resume_endpoints(client):
    repository = RewardOpportunityRepository(app.state.data_manager.db_path)
    feed_id = repository.upsert_source_feed(
        {
            "id": "source-pause-1",
            "name": "Pause Feed",
            "source_type": "web",
            "entry_url": "https://example.com/rewards",
        }
    )

    pause_response = client.post(f"/api/reward-opportunities/sources/{feed_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["is_paused"] is True

    resume_response = client.post(f"/api/reward-opportunities/sources/{feed_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["is_paused"] is False
