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
    assert "agent_jobs_v2" in table_names
