"""Product-selection repository tests."""

from __future__ import annotations

import os
import sqlite3
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import DataManager  # noqa: E402
from product_selection.repository import ProductSelectionRepository  # noqa: E402
from product_selection.service import ProductSelectionService  # noqa: E402


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


def test_create_selection_query_persists_platform_scope(temp_db):
    repo = ProductSelectionRepository(temp_db)

    query = repo.create_query(
        query_type="keyword",
        query_text="bluetooth tracker",
        platform_scope="both",
    )

    assert query.id
    assert query.query_type.value == "keyword"
    assert query.query_text == "bluetooth tracker"
    assert query.platform_scope.value == "both"
    assert query.status.value == "running"


def test_store_selection_opportunity_links_to_query(temp_db):
    repo = ProductSelectionRepository(temp_db)
    query = repo.create_query(
        query_type="keyword",
        query_text="bluetooth tracker",
        platform_scope="both",
    )

    item = repo.create_opportunity(
        query_id=query.id,
        platform="taobao",
        platform_item_id="tb-001",
        title="Bluetooth Smart Tracker",
        opportunity_score=72,
        confidence_score=68,
    )

    assert item.id
    assert item.query_id == query.id
    assert item.platform == "taobao"
    assert repo.get_opportunity(item.id).title == "Bluetooth Smart Tracker"


def test_data_manager_initializes_product_selection_tables(temp_db):
    DataManager(db_path=temp_db)

    conn = sqlite3.connect(temp_db)
    try:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
    finally:
        conn.close()

    assert "selection_queries" in table_names
    assert "selection_opportunities" in table_names
    assert "selection_opportunity_signals" in table_names
    assert "selection_tracking_items" in table_names


def test_rerun_recent_queries_replays_saved_selection_queries(temp_db):
    repo = ProductSelectionRepository(temp_db)
    service = ProductSelectionService(repository=repo)

    initial = service.start_research_job(
        query_type="keyword",
        query_text="pet fountain",
        platform_scope="both",
    )
    replay = service.rerun_recent_queries(limit=1)
    latest_queries = repo.list_queries(limit=2)

    assert initial["job"]["id"]
    assert replay["triggered"] == 1
    assert replay["jobs"][0]["item_count"] >= 1
    assert len(latest_queries) == 2
    assert latest_queries[0].query_text == "pet fountain"


def test_run_automation_cycle_promotes_top_candidates_and_creates_agent_job(temp_db):
    repo = ProductSelectionRepository(temp_db)
    service = ProductSelectionService(repository=repo)

    service.start_research_job(
        query_type="keyword",
        query_text="pet fountain",
        platform_scope="both",
    )
    automation = service.run_automation_cycle(
        query_limit=1,
        max_tracked_items=2,
        min_opportunity_score=0,
        min_confidence_score=0,
        requested_by="manual",
    )
    jobs = service.list_automation_runs(limit=5)
    tracked = repo.list_tracking(status="tracking")

    assert automation["job"]["job_type"] == "selection_automation"
    assert automation["job"]["status"] == "completed"
    assert automation["tracked_count"] >= 1
    assert jobs[0]["id"] == automation["job"]["id"]
    assert tracked


def test_run_operations_cycle_updates_due_tracking_and_creates_agent_job(temp_db):
    repo = ProductSelectionRepository(temp_db)
    service = ProductSelectionService(repository=repo)

    initial = service.start_research_job(
        query_type="keyword",
        query_text="desk fan",
        platform_scope="both",
    )
    opportunity_id = initial["items"][0]["id"]
    repo.upsert_tracking(
        opportunity_id,
        {
            "status": "tracking",
            "is_favorited": False,
            "next_action": "Check sourcing stability",
        },
    )

    conn = sqlite3.connect(temp_db)
    try:
        conn.execute(
            "UPDATE selection_tracking_items SET remind_at = ? WHERE opportunity_id = ?",
            ("2024-01-01T00:00:00+00:00", opportunity_id),
        )
        conn.commit()
    finally:
        conn.close()

    operations = service.run_operations_cycle(
        max_items=2,
        stale_after_hours=48,
        remind_after_hours=12,
        requested_by="manual",
    )
    jobs = service.list_operations_runs(limit=5)
    refreshed = repo.get_tracking(opportunity_id)

    assert operations["job"]["job_type"] == "selection_tracking_ops"
    assert operations["job"]["status"] == "completed"
    assert operations["processed_count"] == 1
    assert operations["processed_items"][0]["follow_up_reason"] == "reminder_due"
    assert jobs[0]["id"] == operations["job"]["id"]
    assert refreshed is not None
    assert refreshed.remind_at is not None
