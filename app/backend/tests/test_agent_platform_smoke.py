"""
Smoke coverage for the shared agent platform across both domains.
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


def test_agent_platform_supports_opportunity_and_selection_domains(client):
    opportunity = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    )
    selection = client.post(
        "/api/agent/sessions",
        json={"domain_type": "product_selection", "entry_mode": "chat"},
    )

    assert opportunity.status_code == 200
    assert selection.status_code == 200

    opportunity_session = opportunity.json()
    selection_session = selection.json()

    opportunity_turn = client.post(
        f"/api/agent/sessions/{opportunity_session['id']}/turns",
        json={"content": "Find solo-friendly grants worth following up"},
    )
    selection_turn = client.post(
        f"/api/agent/sessions/{selection_session['id']}/turns",
        json={"content": "Taobao pet water fountain"},
    )

    assert opportunity_turn.status_code == 200
    assert selection_turn.status_code == 200

    opportunity_payload = opportunity_turn.json()
    selection_payload = selection_turn.json()

    assert opportunity_payload["session"]["domain_type"] == "opportunity"
    assert selection_payload["session"]["domain_type"] == "product_selection"
    assert opportunity_payload["assistant_turn"]["role"] == "assistant"
    assert selection_payload["assistant_turn"]["role"] == "assistant"
    assert opportunity_payload["artifacts"][0]["artifact_type"] == "checklist"
    assert selection_payload["artifacts"][0]["artifact_type"] == "checklist"
    assert opportunity_payload["tool_calls"]
    assert any(item["artifact_type"] == "shortlist" for item in selection_payload["artifacts"])
