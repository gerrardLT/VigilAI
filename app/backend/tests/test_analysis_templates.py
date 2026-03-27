"""
Analysis template persistence tests.
"""

from __future__ import annotations

from datetime import datetime
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def test_data_manager_creates_default_analysis_templates(temp_db):
    data_manager = DataManager(db_path=temp_db)

    templates = data_manager.get_analysis_templates()
    default_template = data_manager.get_default_analysis_template()

    assert {item["slug"] for item in templates} >= {
        "quick-money",
        "low-effort-high-roi",
        "safe-trust",
    }
    assert default_template is not None
    assert default_template["slug"] == "quick-money"


def test_data_manager_can_duplicate_and_activate_template(temp_db):
    data_manager = DataManager(db_path=temp_db)
    default_template = data_manager.get_default_analysis_template()

    clone = data_manager.duplicate_analysis_template(default_template["id"], "Fast money v2")
    data_manager.set_default_analysis_template(clone["id"])

    assert clone["name"] == "Fast money v2"
    assert clone["slug"].startswith("fast-money-v2")
    assert data_manager.get_default_analysis_template()["id"] == clone["id"]


def test_data_manager_can_rename_and_delete_template(temp_db):
    data_manager = DataManager(db_path=temp_db)
    template = next(item for item in data_manager.get_analysis_templates() if item["slug"] == "safe-trust")

    renamed = data_manager.update_analysis_template(template["id"], {"name": "Safe trust plus"})
    remaining = data_manager.get_analysis_templates()

    assert renamed["name"] == "Safe trust plus"
    assert renamed["slug"] == "safe-trust-plus"

    data_manager.delete_analysis_template(template["id"])

    assert all(item["id"] != template["id"] for item in data_manager.get_analysis_templates())
    assert len(data_manager.get_analysis_templates()) == len(remaining) - 1


def test_deleting_default_template_promotes_another_template(temp_db):
    data_manager = DataManager(db_path=temp_db)
    default_template = data_manager.get_default_analysis_template()

    deleted = data_manager.delete_analysis_template(default_template["id"])
    promoted = data_manager.get_default_analysis_template()

    assert deleted is True
    assert promoted is not None
    assert promoted["id"] != default_template["id"]


def test_activating_template_recomputes_existing_activity_analysis(temp_db):
    data_manager = DataManager(db_path=temp_db)
    source = data_manager.get_sources_status()[0]

    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/no-explicit-reward"),
        title="Solo lightweight personal challenge",
        description="A solo-friendly lightweight project with no listed payout yet.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/no-explicit-reward",
        category=Category.BOUNTY,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    data_manager.add_activity(activity)

    loaded_before = data_manager.get_activity_by_id(activity.id)
    roi_template = next(
        item for item in data_manager.get_analysis_templates() if item["slug"] == "low-effort-high-roi"
    )

    assert loaded_before is not None
    assert loaded_before.analysis_status == "rejected"

    data_manager.set_default_analysis_template(roi_template["id"])

    loaded_after = data_manager.get_activity_by_id(activity.id)
    assert loaded_after is not None
    assert loaded_after.analysis_status == "passed"
