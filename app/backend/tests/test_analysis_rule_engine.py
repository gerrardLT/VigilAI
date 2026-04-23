"""
Layered analysis rule engine tests.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.ai_enrichment import enrich_activity_for_analysis  # noqa: E402
from analysis.rule_engine import run_analysis  # noqa: E402
from data_manager import DataManager  # noqa: E402
from models import Activity, ActivityDates, Category, Prize  # noqa: E402


def build_template() -> dict:
    return {
        "layers": [
            {
                "key": "hard_gate",
                "label": "Hard gate",
                "conditions": [
                    {
                        "key": "reward_clarity_score",
                        "label": "Reward clarity",
                        "enabled": True,
                        "operator": "gte",
                        "value": 2,
                        "hard_fail": True,
                    }
                ],
            },
            {
                "key": "roi",
                "label": "ROI",
                "conditions": [
                    {
                        "key": "roi_score",
                        "label": "ROI score",
                        "enabled": True,
                        "operator": "gte",
                        "value": 60,
                        "strictness": "medium",
                        "hard_fail": False,
                    }
                ],
            },
            {
                "key": "trust",
                "label": "Trust",
                "conditions": [
                    {
                        "key": "trust_score",
                        "label": "Trust score",
                        "enabled": True,
                        "operator": "gte",
                        "value": 50,
                        "hard_fail": False,
                    }
                ],
            },
            {
                "key": "priority",
                "label": "Priority",
                "mode": "rank",
                "conditions": [],
            },
        ]
    }


def test_rule_engine_filters_activity_at_hard_gate_layer():
    result = run_analysis(
        activity={"id": "activity-1", "title": "Unclear reward opportunity"},
        template=build_template(),
        analysis_fields={
            "reward_clarity_score": 1,
            "roi_score": 82,
            "trust_score": 90,
        },
    )

    assert result.status == "rejected"
    assert result.failed_layer == "hard_gate"
    assert result.layer_results[0].decision == "failed"


def test_rule_engine_marks_borderline_activity_as_watchlist():
    result = run_analysis(
        activity={"id": "activity-2", "title": "Borderline ROI opportunity"},
        template=build_template(),
        analysis_fields={
            "reward_clarity_score": 3,
            "roi_score": 56,
            "trust_score": 80,
        },
    )

    assert result.status == "watch"
    assert result.failed_layer is None
    assert result.layer_results[1].decision == "borderline"
    assert result.folded_summary_reasons


def test_rule_engine_returns_human_facing_chinese_reasons():
    result = run_analysis(
        activity={"id": "activity-3", "title": "Unclear reward opportunity"},
        template=build_template(),
        analysis_fields={
            "reward_clarity_score": 1,
            "roi_score": 82,
            "trust_score": 90,
        },
    )

    assert result.layer_results[0].reasons == ["奖励信息不够明确，建议先不要投入"]
    assert result.folded_summary_reasons == ["奖励信息不够明确，建议先不要投入"]


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


def create_activity(data_manager: DataManager, url: str = "https://example.com/ai-analysis") -> Activity:
    source = data_manager.get_sources_status()[0]
    now = datetime.now()
    return Activity(
        id=Activity.generate_id(source.id, url),
        title="Solo bug bounty with fast payout",
        description="Individual developers can submit a small fix and receive reward payout within 7 days.",
        source_id=source.id,
        source_name=source.name,
        url=url,
        category=Category.BOUNTY,
        prize=Prize(amount=1500, currency="USD", description="Guaranteed reward"),
        dates=ActivityDates(deadline=now + timedelta(days=5)),
        created_at=now,
        updated_at=now,
    )


def test_ai_enrichment_extracts_money_and_effort_fields():
    fields = enrich_activity_for_analysis(
        {
            "title": "Solo bug bounty with fast payout",
            "description": "Individual developers can submit a small fix and receive reward payout within 7 days.",
            "category": "bounty",
            "prize_amount": 1500,
        }
    )

    assert fields["roi_level"] in {"medium", "high"}
    assert fields["solo_friendliness"] == "solo_friendly"
    assert fields["_confidence"]["roi_level"] in {"medium", "high"}


def test_data_manager_persists_analysis_result_fields_on_activity(temp_db):
    data_manager = DataManager(db_path=temp_db)
    activity = create_activity(data_manager, url="https://example.com/analysis-persisted")

    data_manager.add_activity(activity)
    loaded = data_manager.get_activity_by_id(activity.id)

    assert loaded.analysis_fields["roi_level"] in {"medium", "high"}
    assert loaded.analysis_status in {"passed", "watch", "rejected"}
    assert loaded.analysis_summary_reasons
