"""
Product-selection agent tool tests.
"""

from __future__ import annotations

from datetime import datetime
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_platform.conversation_engine import ConversationEngine  # noqa: E402
from agent_platform.models import AgentSession, AgentTurn  # noqa: E402
from agent_platform.tool_router import ToolRouter, build_default_registry  # noqa: E402
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


def build_router(data_manager: DataManager) -> ToolRouter:
    return ToolRouter(
        tool_registry=build_default_registry(data_manager=data_manager),
        registry_key=data_manager.db_path,
    )


def build_session() -> AgentSession:
    now = datetime.now()
    return AgentSession(
        id=uuid.uuid4().hex,
        domain_type="product_selection",
        entry_mode="chat",
        status="active",
        title=None,
        created_at=now,
        updated_at=now,
        last_turn_at=None,
    )


def build_user_turn(content: str) -> AgentTurn:
    return AgentTurn(
        id=uuid.uuid4().hex,
        session_id=uuid.uuid4().hex,
        role="user",
        content=content,
        sequence_no=1,
        tool_name=None,
        tool_payload={},
        created_at=datetime.now(),
    )


def test_router_uses_selection_query_tool_for_selection_session(data_manager):
    router = build_router(data_manager)

    selected = router.resolve_tools(
        domain_type="product_selection",
        user_message="淘宝上的宠物饮水机还值得做吗",
    )

    assert "selection_query" in selected


def test_router_uses_selection_compare_tool_for_compare_prompt(data_manager):
    router = build_router(data_manager)

    selected = router.resolve_tools(
        domain_type="product_selection",
        user_message="对比淘宝和闲鱼上的宠物饮水机，哪个更值得做",
    )

    assert selected == ["selection_compare"]


def test_conversation_engine_returns_selection_shortlist_and_comparison_artifacts(data_manager):
    engine = ConversationEngine(build_router(data_manager))

    reply = engine.reply(
        session=build_session(),
        user_turn=build_user_turn("对比淘宝和闲鱼上的宠物饮水机，哪个更值得做"),
    )

    assert reply.tool_calls[0]["tool_name"] == "selection_compare"
    assert reply.tool_calls[0]["status"] == "completed"
    assert reply.artifacts[0].artifact_type == "checklist"
    assert any(artifact.artifact_type == "shortlist" for artifact in reply.artifacts)
    assert any(artifact.artifact_type == "comparison" for artifact in reply.artifacts)
    assert "margin, sell-through speed, or after-sales risk" in reply.assistant_turn
    assert "Cross-platform comparison" in reply.assistant_turn


def test_agent_turn_api_returns_shortlist_artifact_for_product_selection_query(client):
    session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "product_selection", "entry_mode": "chat"},
    ).json()

    response = client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "淘宝宠物饮水机还值得做吗"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["domain_type"] == "product_selection"
    assert payload["artifacts"][0]["artifact_type"] == "checklist"
    assert any(item["artifact_type"] == "shortlist" for item in payload["artifacts"])
    assert payload["tool_calls"][0]["tool_name"] == "selection_query"
    assert payload["tool_calls"][0]["status"] == "completed"
