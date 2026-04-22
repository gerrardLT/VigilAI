"""
Agent-analysis persistence model tests.
"""

from __future__ import annotations

from datetime import datetime
import os
import sqlite3
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.schemas import AnalysisSnapshot  # noqa: E402
from data_manager import DataManager  # noqa: E402
from models import Activity, Category  # noqa: E402


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


def _create_legacy_activities_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            full_content TEXT,
            source_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            url TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT,
            prize_amount REAL,
            prize_currency TEXT,
            prize_description TEXT,
            start_date TEXT,
            end_date TEXT,
            deadline TEXT,
            location TEXT,
            organizer TEXT,
            image_url TEXT,
            summary TEXT,
            score REAL,
            score_reason TEXT,
            deadline_level TEXT,
            trust_level TEXT,
            updated_fields TEXT,
            analysis_fields TEXT,
            analysis_status TEXT,
            analysis_failed_layer TEXT,
            analysis_summary_reasons TEXT,
            status TEXT DEFAULT 'upcoming',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_id, url)
        )
        """
    )


def test_data_manager_migrates_agent_analysis_schema_without_corrupting_existing_activity(temp_db):
    created_at = datetime(2026, 1, 1, 10, 0, 0).isoformat()
    conn = sqlite3.connect(temp_db)
    try:
        _create_legacy_activities_table(conn)
        conn.execute(
            """
            INSERT INTO activities (
                id, title, description, full_content, source_id, source_name, url, category, tags,
                prize_amount, prize_currency, prize_description,
                start_date, end_date, deadline, location, organizer, image_url,
                summary, score, score_reason, deadline_level, trust_level, updated_fields,
                analysis_fields, analysis_status, analysis_failed_layer, analysis_summary_reasons,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-activity-1",
                "Legacy Activity",
                "Legacy description",
                None,
                "legacy-source",
                "Legacy Source",
                "https://example.com/legacy",
                "bounty",
                "[]",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "Legacy summary",
                42.0,
                "Legacy reason",
                "upcoming",
                "high",
                "[]",
                "{}",
                "watch",
                None,
                "[\"legacy note\"]",
                "upcoming",
                created_at,
                created_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    data_manager = DataManager(db_path=temp_db)

    with data_manager._get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        activity_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(activities)").fetchall()
        }
        legacy_row = conn.execute(
            """
            SELECT id, title, source_id, source_name, url, category, status, created_at, updated_at
            FROM activities
            WHERE id = ?
            """,
            ("legacy-activity-1",),
        ).fetchone()

    assert {
        "analysis_jobs",
        "analysis_job_items",
        "analysis_item_steps",
        "analysis_evidence",
        "analysis_reviews",
    } <= tables
    assert {
        "analysis_summary",
        "analysis_reasons",
        "analysis_risk_flags",
        "analysis_recommended_action",
        "analysis_confidence",
        "analysis_structured",
        "analysis_template_id",
        "analysis_current_run_id",
        "analysis_updated_at",
    } <= activity_columns
    assert legacy_row is not None
    assert legacy_row["title"] == "Legacy Activity"
    assert legacy_row["source_id"] == "legacy-source"
    assert legacy_row["url"] == "https://example.com/legacy"
    assert legacy_row["created_at"] == created_at


def test_activity_snapshot_fields_round_trip_through_sqlite_and_data_manager(temp_db):
    data_manager = DataManager(db_path=temp_db)
    source = data_manager.get_sources_status()[0]
    now = datetime(2026, 3, 27, 12, 34, 56)
    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/snapshot-roundtrip"),
        title="Snapshot Roundtrip",
        description="Minimal activity used for snapshot persistence checks.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/snapshot-roundtrip",
        category=Category.BOUNTY,
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)

    created = data_manager.get_activity_by_id(activity.id)
    assert created is not None
    assert created.analysis_summary is None
    assert created.analysis_reasons == []
    assert created.analysis_structured == {}

    snapshot = AnalysisSnapshot(
        status="watch",
        summary="Needs explicit reward details before approval",
        reasons=["Reward clarity is incomplete"],
        risk_flags=["low_source_trust"],
        recommended_action="request_manual_review",
        confidence=0.62,
        structured={"should_deep_research": True, "roi_level": "medium"},
        template_id="template-123",
        current_run_id="run-456",
        updated_at=now,
    )
    packed = data_manager._pack_activity_snapshot_fields(snapshot)
    assignment_clause = ", ".join(f"{column} = ?" for column in packed.keys())

    with data_manager._get_connection() as conn:
        conn.execute(
            f"UPDATE activities SET {assignment_clause} WHERE id = ?",
            [*packed.values(), activity.id],
        )

    loaded = data_manager.get_activity_by_id(activity.id)
    assert loaded is not None
    assert "analysis_status" in packed
    assert packed["analysis_status"] == snapshot.status
    assert loaded.analysis_status == snapshot.status
    assert loaded.analysis_summary == snapshot.summary
    assert loaded.analysis_reasons == snapshot.reasons
    assert loaded.analysis_risk_flags == snapshot.risk_flags
    assert loaded.analysis_recommended_action == snapshot.recommended_action
    assert loaded.analysis_confidence == snapshot.confidence
    assert loaded.analysis_structured == snapshot.structured
    assert loaded.analysis_template_id == snapshot.template_id
    assert loaded.analysis_current_run_id == snapshot.current_run_id
    assert loaded.analysis_updated_at == snapshot.updated_at


def test_rerun_analysis_does_not_populate_approved_snapshot_fields_without_writeback(temp_db):
    data_manager = DataManager(db_path=temp_db)
    source = data_manager.get_sources_status()[0]
    now = datetime(2026, 3, 27, 12, 40, 0)
    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/rerun-no-approved-snapshot"),
        title="Rerun should not write approved snapshot",
        description="Used to ensure rerun path does not auto-write approved snapshot fields.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/rerun-no-approved-snapshot",
        category=Category.BOUNTY,
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)

    rerun_count = data_manager.rerun_analysis_for_all_activities()
    assert rerun_count >= 1

    loaded = data_manager.get_activity_by_id(activity.id)
    assert loaded is not None
    assert loaded.analysis_summary is None
    assert loaded.analysis_reasons == []
    assert loaded.analysis_risk_flags == []
    assert loaded.analysis_recommended_action is None
    assert loaded.analysis_confidence is None
    assert loaded.analysis_structured == {}
    assert loaded.analysis_template_id is None
    assert loaded.analysis_current_run_id is None
    assert loaded.analysis_updated_at is None
