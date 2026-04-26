"""
Shared agent platform API tests.
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


def test_create_agent_session_returns_session_id(client):
    response = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["domain_type"] == "opportunity"
    assert payload["entry_mode"] == "chat"
    assert payload["status"] == "active"


def test_post_turn_returns_assistant_reply_and_turns(client):
    session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()

    response = client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "Find me solo-friendly grants worth following up"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_turn"]["role"] == "assistant"
    assert "reward size, deadline, or solo execution" in payload["assistant_turn"]["content"]
    assert len(payload["turns"]) == 2
    assert payload["turns"][0]["role"] == "user"
    assert payload["turns"][1]["role"] == "assistant"


def test_get_turns_and_artifacts_for_session(client):
    session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "Find me solo-friendly grants worth following up"},
    )

    turns_response = client.get(f"/api/agent/sessions/{session['id']}/turns")
    artifacts_response = client.get(f"/api/agent/sessions/{session['id']}/artifacts")

    assert turns_response.status_code == 200
    assert len(turns_response.json()) == 2
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()[0]["artifact_type"] == "checklist"
