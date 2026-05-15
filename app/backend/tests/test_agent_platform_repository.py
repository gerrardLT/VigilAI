"""
Shared agent platform repository tests.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_platform.repository import AgentPlatformRepository  # noqa: E402
from data_manager import DataManager  # noqa: E402


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


def test_create_agent_session_persists_default_status(temp_db):
    repo = AgentPlatformRepository(temp_db)

    session = repo.create_session(domain_type="opportunity", entry_mode="chat")

    assert session.id
    assert session.domain_type == "opportunity"
    assert session.entry_mode == "chat"
    assert session.status == "active"
    assert session.policy_mode == "standard"
    assert session.memory_scope == "domain"


def test_create_agent_session_persists_policy_and_memory_scope(temp_db):
    repo = AgentPlatformRepository(temp_db)

    session = repo.create_session(
        domain_type="product_selection",
        entry_mode="chat",
        policy_mode="strict",
        memory_scope="global",
    )

    assert session.policy_mode == "strict"
    assert session.memory_scope == "global"


def test_append_turn_and_list_turns_for_session(temp_db):
    repo = AgentPlatformRepository(temp_db)
    session = repo.create_session(domain_type="opportunity", entry_mode="chat")

    created_turn = repo.append_turn(session.id, role="user", content="Find solo-friendly grants")
    turns = repo.list_turns(session.id)

    assert created_turn.session_id == session.id
    assert created_turn.role == "user"
    assert created_turn.content == "Find solo-friendly grants"
    assert len(turns) == 1
    assert turns[0].id == created_turn.id
    assert turns[0].role == "user"
    assert turns[0].content == "Find solo-friendly grants"


def test_persist_session_state_insights_and_thinking_steps(temp_db):
    repo = AgentPlatformRepository(temp_db)
    session = repo.create_session(domain_type="product_selection", entry_mode="chat")
    turn = repo.append_turn(session.id, role="user", content="Compare taobao pet fountain margins")

    state = repo.upsert_session_state(
        session.id,
        goal="Compare taobao pet fountain margins",
        preferences=["margin", "platform_taobao"],
        working_memory=["taobao: pet fountain"],
        current_focus="pet fountain",
        next_question="Tell me whether margin or after-sales risk matters most.",
        summary="Generated an initial product-selection pass.",
        last_tool_names=["selection_compare"],
        state_payload={"completed_tool_count": 1},
    )
    insight = repo.create_insight(
        session.id,
        source_turn_id=turn.id,
        insight_type="goal",
        content="Compare taobao pet fountain margins",
        importance=0.9,
    )
    thinking_step = repo.create_thinking_step(
        session.id,
        source_turn_id=turn.id,
        phase="routing",
        summary="Resolved selection_compare for product_selection.",
        tool_name="selection_compare",
    )

    fetched_state = repo.get_session_state(session.id)
    insights = repo.list_insights(session.id)
    thinking_steps = repo.list_thinking_steps(session.id)

    assert state.session_id == session.id
    assert fetched_state is not None
    assert fetched_state.goal == "Compare taobao pet fountain margins"
    assert fetched_state.last_tool_names == ["selection_compare"]
    assert insights[0].id == insight.id
    assert insights[0].source_turn_id == turn.id
    assert thinking_steps[0].id == thinking_step.id
    assert thinking_steps[0].tool_name == "selection_compare"


def test_persist_and_list_execution_plans(temp_db):
    repo = AgentPlatformRepository(temp_db)
    session = repo.create_session(domain_type="product_selection", entry_mode="chat")
    turn = repo.append_turn(session.id, role="user", content="Compare taobao pet fountain margins")

    plan = repo.create_execution_plan(
        session.id,
        source_turn_id=turn.id,
        mode="guarded",
        summary="Guarded orchestration plan for product_selection: selection_compare.",
        requested_steps=[
            {
                "tool_name": "selection_compare",
                "intent": "cross_platform_comparison",
                "rationale": "The message asks for cross-platform comparison.",
                "priority": 1,
                "stage": "analysis",
                "access_mode": "read_only",
                "policy_decision": "guarded",
                "metadata": {"domain_type": "product_selection"},
            }
        ],
        runnable_tools=["selection_compare"],
        blocked_tools=[],
        risk_flags=["bypass_or_scraping_abuse"],
        reasoning="The session used a guarded read-only comparison path.",
        payload={"requested_tool_count": 1},
    )

    plans = repo.list_execution_plans(session.id)

    assert plans[0].id == plan.id
    assert plans[0].source_turn_id == turn.id
    assert plans[0].requested_steps[0].tool_name == "selection_compare"
    assert plans[0].requested_steps[0].policy_decision == "guarded"
    assert plans[0].risk_flags == ["bypass_or_scraping_abuse"]


def test_persist_memories_and_reflections(temp_db):
    repo = AgentPlatformRepository(temp_db)
    session = repo.create_session(domain_type="product_selection", entry_mode="chat")
    turn = repo.append_turn(session.id, role="user", content="Find taobao pet fountain candidates")

    memory = repo.create_memory(
        session.id,
        source_turn_id=turn.id,
        memory_type="goal",
        content="Find taobao pet fountain candidates",
        importance=0.9,
        payload={"domain_type": "product_selection"},
    )
    reflection = repo.create_reflection(
        session.id,
        source_turn_id=turn.id,
        reflection_type="execution_review",
        summary="Completed 1 tool call and produced a shortlist.",
        action_item="Tell me whether margin or after-sales risk matters most.",
        score=0.8,
        payload={"completed_tools": ["selection_query"]},
    )

    memories = repo.list_memories(session.id)
    reflections = repo.list_reflections(session.id)

    assert memories[0].id == memory.id
    assert memories[0].memory_type == "goal"
    assert memories[0].source_turn_id == turn.id
    assert reflections[0].id == reflection.id
    assert reflections[0].reflection_type == "execution_review"
    assert reflections[0].action_item == "Tell me whether margin or after-sales risk matters most."


def test_list_domain_memories_and_reflections_across_sessions(temp_db):
    repo = AgentPlatformRepository(temp_db)
    first_session = repo.create_session(domain_type="opportunity", entry_mode="chat")
    second_session = repo.create_session(domain_type="opportunity", entry_mode="chat")
    third_session = repo.create_session(domain_type="product_selection", entry_mode="chat")

    first_turn = repo.append_turn(first_session.id, role="user", content="Find solo grants")
    third_turn = repo.append_turn(third_session.id, role="user", content="Compare taobao pet fountains")

    repo.create_memory(
        first_session.id,
        source_turn_id=first_turn.id,
        memory_type="goal",
        content="Find solo grants",
        importance=0.9,
    )
    repo.create_memory(
        third_session.id,
        source_turn_id=third_turn.id,
        memory_type="goal",
        content="Compare taobao pet fountains",
        importance=0.95,
    )
    repo.create_reflection(
        first_session.id,
        source_turn_id=first_turn.id,
        reflection_type="execution_review",
        summary="Opportunity search worked well for solo grants.",
        score=0.8,
    )
    repo.create_reflection(
        third_session.id,
        source_turn_id=third_turn.id,
        reflection_type="execution_review",
        summary="Selection compare worked well for pet fountains.",
        score=0.85,
    )

    domain_memories = repo.list_domain_memories("opportunity", exclude_session_id=second_session.id)
    domain_reflections = repo.list_domain_reflections("opportunity", exclude_session_id=second_session.id)

    assert any(item.content == "Find solo grants" for item in domain_memories)
    assert all(item.content != "Compare taobao pet fountains" for item in domain_memories)
    assert any(item.summary == "Opportunity search worked well for solo grants." for item in domain_reflections)
    assert all(item.summary != "Selection compare worked well for pet fountains." for item in domain_reflections)


def test_create_update_and_list_agent_jobs(temp_db):
    repo = AgentPlatformRepository(temp_db)

    created = repo.create_job(
        domain_type="product_selection",
        job_type="selection_automation",
        requested_by="scheduler",
        input_payload={"query_limit": 2},
    )
    updated = repo.update_job(
        created.id,
        status="completed",
        result_payload={"tracked_count": 2},
    )
    listed = repo.list_jobs(domain_type="product_selection", job_type="selection_automation")

    assert created.status == "running"
    assert updated.status == "completed"
    assert updated.result_payload["tracked_count"] == 2
    assert updated.finished_at is not None
    assert listed[0].id == created.id


def test_data_manager_initializes_agent_platform_tables(temp_db):
    DataManager(db_path=temp_db)

    conn = sqlite3.connect(temp_db)
    try:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
    finally:
        conn.close()

    assert "agent_sessions" in table_names
    assert "agent_turns" in table_names
    assert "agent_artifacts" in table_names
    assert "agent_execution_plans" in table_names
    assert "agent_jobs_v2" in table_names
    assert "agent_session_states" in table_names
    assert "agent_insights" in table_names
    assert "agent_thinking_steps" in table_names
    assert "agent_memories" in table_names
    assert "agent_reflections" in table_names
