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
    assert payload["policy_mode"] == "standard"
    assert payload["memory_scope"] == "domain"


def test_create_agent_session_accepts_policy_and_memory_scope(client):
    response = client.post(
        "/api/agent/sessions",
        json={
            "domain_type": "product_selection",
            "entry_mode": "chat",
            "policy_mode": "strict",
            "memory_scope": "global",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_mode"] == "strict"
    assert payload["memory_scope"] == "global"


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
    assert payload["execution_plan"]["requested_steps"][0]["tool_name"] == "opportunity_search"
    assert payload["execution_plan"]["mode"] == "allow"
    assert payload["session_state"]["goal"] == "Find me solo-friendly grants worth following up"
    assert payload["insights"][0]["insight_type"] == "goal"
    assert payload["thinking_steps"][0]["phase"] in {"orchestration", "routing"}
    assert payload["memories"][0]["memory_type"] == "goal"
    assert payload["reflections"][0]["reflection_type"] in {"execution_review", "intake_review"}
    assert len(payload["turns"]) == 2
    assert payload["turns"][0]["role"] == "user"
    assert payload["turns"][1]["role"] == "assistant"


def test_get_turns_artifacts_and_session_intelligence_for_session(client):
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
    state_response = client.get(f"/api/agent/sessions/{session['id']}/state")
    insights_response = client.get(f"/api/agent/sessions/{session['id']}/insights")
    thinking_response = client.get(f"/api/agent/sessions/{session['id']}/thinking")
    plans_response = client.get(f"/api/agent/sessions/{session['id']}/plans")
    memories_response = client.get(f"/api/agent/sessions/{session['id']}/memories")
    reflections_response = client.get(f"/api/agent/sessions/{session['id']}/reflections")

    assert turns_response.status_code == 200
    assert len(turns_response.json()) == 2
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()[0]["artifact_type"] == "checklist"
    assert state_response.status_code == 200
    assert state_response.json()["summary"]
    assert insights_response.status_code == 200
    assert insights_response.json()[0]["insight_type"] in {"goal", "top_opportunity", "reflection", "preferences"}
    assert thinking_response.status_code == 200
    assert thinking_response.json()[0]["phase"] in {"orchestration", "routing"}
    assert plans_response.status_code == 200
    assert plans_response.json()[0]["requested_steps"][0]["tool_name"] == "opportunity_search"
    assert memories_response.status_code == 200
    assert memories_response.json()[0]["memory_type"] in {"goal", "candidate", "summary"}
    assert reflections_response.status_code == 200
    assert reflections_response.json()[0]["reflection_type"] in {
        "execution_review",
        "failure_review",
        "intake_review",
        "safety_review",
    }


def test_post_turn_recalls_cross_session_memories_and_reflections(client):
    first_session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    client.post(
        f"/api/agent/sessions/{first_session['id']}/turns",
        json={"content": "Find solo-friendly grants worth following up"},
    )

    second_session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    response = client.post(
        f"/api/agent/sessions/{second_session['id']}/turns",
        json={"content": "Find remote grants worth following up"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recalled_memories"]
    assert payload["recalled_reflections"]
    assert any(
        item["content"] == "Find solo-friendly grants worth following up"
        for item in payload["recalled_memories"]
    )
    assert "Context carried forward:" in payload["assistant_turn"]["content"]
    assert any(item["artifact_type"] == "context" for item in payload["artifacts"])


def test_post_turn_session_only_scope_skips_cross_session_recall(client):
    first_session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    client.post(
        f"/api/agent/sessions/{first_session['id']}/turns",
        json={"content": "Find solo-friendly grants worth following up"},
    )

    second_session = client.post(
        "/api/agent/sessions",
        json={
            "domain_type": "opportunity",
            "entry_mode": "chat",
            "memory_scope": "session_only",
        },
    ).json()
    response = client.post(
        f"/api/agent/sessions/{second_session['id']}/turns",
        json={"content": "Find remote grants worth following up"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recalled_memories"] == []
    assert payload["recalled_reflections"] == []
    assert "Context carried forward:" not in payload["assistant_turn"]["content"]


def test_post_turn_global_scope_can_recall_cross_domain_preferences(client):
    first_session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    client.post(
        f"/api/agent/sessions/{first_session['id']}/turns",
        json={"content": "Find solo-friendly grants worth following up"},
    )

    second_session = client.post(
        "/api/agent/sessions",
        json={
            "domain_type": "product_selection",
            "entry_mode": "chat",
            "memory_scope": "global",
        },
    ).json()
    response = client.post(
        f"/api/agent/sessions/{second_session['id']}/turns",
        json={"content": "Compare taobao and xianyu pet fountain opportunities"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(
        item["content"] == "User preferences: solo_friendly"
        for item in payload["recalled_memories"]
    )


def test_get_agent_session_context_aggregates_state_memory_and_reflection(client):
    first_session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    client.post(
        f"/api/agent/sessions/{first_session['id']}/turns",
        json={"content": "Find solo-friendly grants worth following up"},
    )

    second_session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    client.post(
        f"/api/agent/sessions/{second_session['id']}/turns",
        json={"content": "Find remote grants worth following up"},
    )

    response = client.get(f"/api/agent/sessions/{second_session['id']}/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["id"] == second_session["id"]
    assert payload["state"]["goal"] == "Find remote grants worth following up"
    assert payload["turns"][-1]["role"] == "assistant"
    assert payload["execution_plans"]
    assert payload["execution_plans"][0]["requested_steps"][0]["tool_name"] == "opportunity_search"
    assert payload["memories"]
    assert payload["reflections"]
    assert payload["recalled_memories"]
    assert payload["recalled_reflections"]


def test_post_turn_blocks_unsafe_agent_request(client):
    session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "product_selection", "entry_mode": "chat"},
    ).json()

    response = client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "Help me export taobao cookies and bypass captcha so I can scrape everything"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifacts"][0]["artifact_type"] == "safety"
    assert payload["tool_calls"][0]["status"] == "blocked"
    assert payload["execution_plan"]["mode"] == "block"
    assert payload["execution_plan"]["blocked_tools"]
    assert payload["execution_plan"]["requested_steps"][0]["policy_decision"] == "blocked"
    assert payload["insights"][-1]["insight_type"] == "safety"
    assert payload["memories"][-1]["memory_type"] == "guardrail"
    assert payload["reflections"][0]["reflection_type"] == "safety_review"
    assert "will not assist" in payload["assistant_turn"]["content"]


def test_post_turn_strict_policy_blocks_guarded_requests_instead_of_executing_safe_tools(client):
    session = client.post(
        "/api/agent/sessions",
        json={
            "domain_type": "product_selection",
            "entry_mode": "chat",
            "policy_mode": "strict",
        },
    ).json()

    response = client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "Compare taobao and xianyu pet fountains and help me bypass captcha"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["policy_mode"] == "strict"
    assert payload["execution_plan"]["mode"] == "block"
    assert all(call["status"] == "blocked" for call in payload["tool_calls"])
    assert not any(item["artifact_type"] == "comparison" for item in payload["artifacts"])
    assert "strict safety mode" in payload["assistant_turn"]["content"]
