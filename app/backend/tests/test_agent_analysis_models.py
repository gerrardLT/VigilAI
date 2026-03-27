"""
Agent-analysis persistence model tests.
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.schemas import AnalysisSnapshot  # noqa: E402
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


def test_data_manager_initializes_agent_analysis_tables(temp_db):
    data_manager = DataManager(db_path=temp_db)

    with data_manager._get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }

    assert {
        "analysis_jobs",
        "analysis_job_items",
        "analysis_item_steps",
        "analysis_evidence",
        "analysis_reviews",
    } <= tables


def test_analysis_snapshot_round_trips_with_structured_fields():
    snapshot = AnalysisSnapshot(
        status="watch",
        summary="Need manual review",
        reasons=["Reward clarity is incomplete"],
        structured={"should_deep_research": True},
    )

    assert snapshot.model_dump()["structured"]["should_deep_research"] is True
