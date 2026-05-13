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
    response = client.get("/api/reward-opportunities/operations")
    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
    assert "recent_jobs" in payload
