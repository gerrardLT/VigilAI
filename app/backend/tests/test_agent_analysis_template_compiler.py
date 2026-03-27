"""
Tests for business-template compilation into execution policies.
"""

from __future__ import annotations

from datetime import datetime
import gc
import json
import os
import sqlite3
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.template_compiler import compile_analysis_template  # noqa: E402
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
            for _ in range(10):
                try:
                    os.remove(db_path)
                    break
                except PermissionError:
                    gc.collect()
                    time.sleep(0.05)
            else:
                os.remove(db_path)


def _seed_legacy_template_row(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        now = datetime.now().isoformat()
        conn.execute(
            """
            CREATE TABLE analysis_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                description TEXT,
                is_default INTEGER DEFAULT 0,
                tags TEXT NOT NULL,
                layers TEXT NOT NULL,
                sort_fields TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_templates (
                id, name, slug, description, is_default, tags, layers, sort_fields, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-safe-trust",
                "Safe and trusted",
                "safe-trust",
                "Prefer clearer, better-backed opportunities even if payout is slightly slower.",
                1,
                json.dumps(["safe", "trusted"]),
                json.dumps(
                    [
                        {
                            "key": "hard_gate",
                            "label": "Hard gate",
                            "enabled": True,
                            "mode": "filter",
                            "conditions": [
                                {
                                    "key": "reward_clarity",
                                    "label": "Reward clarity",
                                    "enabled": True,
                                    "operator": "gte",
                                    "value": "medium",
                                    "is_hard_gate": True,
                                }
                            ],
                        },
                        {
                            "key": "trust",
                            "label": "Trust",
                            "enabled": True,
                            "mode": "filter",
                            "conditions": [
                                {
                                    "key": "source_trust",
                                    "label": "Source trust",
                                    "enabled": True,
                                    "operator": "gte",
                                    "value": "high",
                                }
                            ],
                        },
                    ]
                ),
                json.dumps(["trust", "clarity", "roi"]),
                now,
                now,
            ),
        )


def test_template_compiler_maps_business_preferences_to_execution_policy():
    compiled = compile_analysis_template(
        {
            "name": "Money first",
            "preference_profile": "money_first",
            "risk_tolerance": "balanced",
            "research_mode": "layered",
        }
    )

    assert compiled.route_policy.single_item.task_type == "deep_analysis"
    assert compiled.route_policy.batch.task_type == "screening"
    assert compiled.safety_policy.writeback_mode == "human_review"
    assert compiled.research_policy.default_mode == "layered"


def test_template_compiler_keeps_writeback_human_review_for_aggressive_templates():
    compiled = compile_analysis_template(
        {
            "name": "Fast lane",
            "preference_profile": "money_first",
            "risk_tolerance": "aggressive",
            "research_mode": "deep",
        }
    )

    assert compiled.safety_policy.writeback_mode == "human_review"


def test_data_manager_template_roundtrip_keeps_business_fields_and_legacy_shape(temp_db):
    data_manager = DataManager(db_path=temp_db)

    created = data_manager.create_analysis_template(
        {
            "name": "Business template",
            "description": "Business-first template payload",
            "preference_profile": "money_first",
            "risk_tolerance": "balanced",
            "research_mode": "layered",
        }
    )

    assert created["preference_profile"] == "money_first"
    assert created["risk_tolerance"] == "balanced"
    assert created["research_mode"] == "layered"
    assert created["compiled_policy"]["route_policy"]["single_item"]["task_type"] == "deep_analysis"
    assert created["layers"]
    assert created["sort_fields"]


def test_low_effort_default_template_uses_balanced_business_profile(temp_db):
    data_manager = DataManager(db_path=temp_db)

    template = next(item for item in data_manager.get_analysis_templates() if item["slug"] == "low-effort-high-roi")

    assert template["preference_profile"] == "balanced"
    assert template["risk_tolerance"] == "balanced"
    assert template["research_mode"] == "layered"
    assert template["compiled_policy"]["route_policy"]["single_item"]["model_tier"] == "standard"
    assert template["compiled_policy"]["route_policy"]["batch"]["model_tier"] == "standard"
    assert template["sort_fields"] == ["effort", "roi", "deadline"]


def test_data_manager_backfills_legacy_template_business_fields_on_migration(temp_db):
    _seed_legacy_template_row(temp_db)

    data_manager = DataManager(db_path=temp_db)
    migrated = next(item for item in data_manager.get_analysis_templates() if item["slug"] == "safe-trust")

    assert migrated["preference_profile"] == "safety_first"
    assert migrated["risk_tolerance"] == "conservative"
    assert migrated["research_mode"] == "layered"
    assert migrated["compiled_policy"]["safety_policy"]["writeback_mode"] == "human_review"

    del data_manager

    with sqlite3.connect(temp_db) as conn:
        conn.row_factory = sqlite3.Row
        stored = conn.execute(
            """
            SELECT preference_profile, risk_tolerance, research_mode, compiled_policy
            FROM analysis_templates
            WHERE slug = ?
            """,
            ("safe-trust",),
        ).fetchone()

    assert stored["preference_profile"] == "safety_first"
    assert stored["risk_tolerance"] == "conservative"
    assert stored["research_mode"] == "layered"
    assert json.loads(stored["compiled_policy"])["safety_policy"]["writeback_mode"] == "human_review"
