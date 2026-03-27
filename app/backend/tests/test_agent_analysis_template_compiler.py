"""
Tests for business-template compilation into execution policies.
"""

from __future__ import annotations

import os
import sys
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
            os.remove(db_path)


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
