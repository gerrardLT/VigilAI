"""
Opportunity-domain agent tool tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_platform.conversation_engine import ConversationEngine  # noqa: E402
from agent_platform.models import AgentSession, AgentTurn  # noqa: E402
from agent_platform.tool_router import ToolRouter  # noqa: E402
from api import app  # noqa: E402
from data_manager import DataManager  # noqa: E402
from models import Activity, ActivityDates, Category, Prize  # noqa: E402
from opportunity_domain.tools import build_opportunity_tool_registry  # noqa: E402


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
    title: str,
    url: str,
    description: str,
    category: Category = Category.GRANT,
    prize_amount: float = 5000,
    deadline_days: int = 7,
    source_index: int = 0,
) -> Activity:
    source = data_manager.get_sources_status()[source_index]
    now = datetime.now()
    return Activity(
        id=Activity.generate_id(source.id, url),
        title=title,
        description=description,
        source_id=source.id,
        source_name=source.name,
        url=url,
        category=category,
        prize=Prize(amount=prize_amount, currency="USD", description="Cash reward"),
        dates=ActivityDates(deadline=now + timedelta(days=deadline_days)),
        created_at=now,
        updated_at=now,
    )


def build_router(data_manager: DataManager) -> ToolRouter:
    return ToolRouter(
        tool_registry=build_opportunity_tool_registry(data_manager),
        registry_key=data_manager.db_path,
    )


def build_session() -> AgentSession:
    now = datetime.now()
    return AgentSession(
        id=uuid.uuid4().hex,
        domain_type="opportunity",
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


def test_conversation_engine_executes_registered_opportunity_search_tool(data_manager):
    activity = create_activity(
        data_manager,
        title="Solo AI Builder Grant",
        url="https://example.com/grant-solo-ai",
        description="AI tooling grant for solo builders with clear reward.",
        category=Category.GRANT,
    )
    data_manager.add_activity(activity)

    engine = ConversationEngine(build_router(data_manager))
    reply = engine.reply(
        session=build_session(),
        user_turn=build_user_turn("Find solo-friendly grants worth following up"),
    )

    assert reply.tool_calls[0]["tool_name"] == "opportunity_search"
    assert reply.tool_calls[0]["status"] == "completed"
    assert reply.artifacts[0].artifact_type == "checklist"
    assert any(artifact.artifact_type == "shortlist" for artifact in reply.artifacts)
    assert "reward size, deadline, or solo execution" in reply.assistant_turn
    assert "Solo AI Builder Grant" in reply.assistant_turn


def test_opportunity_search_tool_returns_filtered_existing_activities(data_manager):
    grant_activity = create_activity(
        data_manager,
        title="AI Infra Grant",
        url="https://example.com/ai-grant",
        description="Grant for AI infra and agent tooling projects.",
        category=Category.GRANT,
    )
    bounty_activity = create_activity(
        data_manager,
        title="Mobile QA Bounty",
        url="https://example.com/mobile-bounty",
        description="Bounty for mobile QA fixes.",
        category=Category.BOUNTY,
        source_index=1,
    )
    data_manager.add_activity(grant_activity)
    data_manager.add_activity(bounty_activity)

    search_tool = build_opportunity_tool_registry(data_manager)["opportunity_search"]
    result = search_tool.run(session=build_session(), user_message="Find AI-related grants")

    assert result["applied_filters"]["category"] == "grant"
    assert result["items"]
    assert any(item["id"] == grant_activity.id for item in result["items"])
    assert all(item["category"] == "grant" for item in result["items"])


def test_opportunity_explain_and_next_action_use_detail_and_tracking(data_manager):
    activity = create_activity(
        data_manager,
        title="Remote Solo Grant",
        url="https://example.com/remote-solo-grant",
        description="Remote-friendly solo grant with clear application flow.",
        category=Category.GRANT,
        deadline_days=2,
    )
    data_manager.add_activity(activity)
    data_manager.upsert_tracking_item(
        activity.id,
        {
          "status": "tracking",
          "notes": "Need a one-page project brief",
          "next_action": "Finish the first-pass application draft this week",
        },
    )

    with data_manager._get_connection() as conn:
        conn.execute(
            """
            UPDATE activities
            SET analysis_status = ?,
                analysis_summary = ?,
                analysis_summary_reasons = ?,
                analysis_recommended_action = ?,
                analysis_risk_flags = ?
            WHERE id = ?
            """,
            (
                "passed",
                "High signal because reward clarity and solo-friendliness are both strong.",
                json.dumps(["reward clarity high", "solo-friendly execution"]),
                "Validate eligibility, then package the application materials.",
                json.dumps(["deadline is close"]),
                activity.id,
            ),
        )

    tool_registry = build_opportunity_tool_registry(data_manager)
    explain_result = tool_registry["opportunity_explain"].run(
        session=build_session(),
        user_message=activity.id,
    )
    next_action_result = tool_registry["opportunity_next_action"].run(
        session=build_session(),
        user_message=activity.id,
    )

    assert explain_result["matched"] is True
    assert explain_result["activity_id"] == activity.id
    assert explain_result["analysis"]["summary"].startswith("High signal")
    assert explain_result["analysis"]["reasons"] == ["reward clarity high", "solo-friendly execution"]
    assert explain_result["tracking"]["status"] == "tracking"

    assert next_action_result["matched"] is True
    assert next_action_result["activity_id"] == activity.id
    assert next_action_result["next_action"] == "Finish the first-pass application draft this week"
    assert next_action_result["action_source"] == "tracking"
    assert next_action_result["tracking_status"] == "tracking"
    assert next_action_result["urgency"] == "high"


def test_agent_turn_api_returns_shortlist_artifact_for_opportunity_query(client, data_manager):
    activity = create_activity(
        data_manager,
        title="Open Source Grant",
        url="https://example.com/open-source-grant",
        description="Grant for open source automation tools.",
        category=Category.GRANT,
    )
    data_manager.add_activity(activity)

    session = client.post(
        "/api/agent/sessions",
        json={"domain_type": "opportunity", "entry_mode": "chat"},
    ).json()
    response = client.post(
        f"/api/agent/sessions/{session['id']}/turns",
        json={"content": "Find grants worth following up"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifacts"][0]["artifact_type"] == "checklist"
    assert any(item["artifact_type"] == "shortlist" for item in payload["artifacts"])
    assert payload["tool_calls"][0]["tool_name"] == "opportunity_search"
    assert payload["tool_calls"][0]["status"] == "completed"
