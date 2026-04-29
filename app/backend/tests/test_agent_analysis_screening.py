"""
Tests for Task 4 context building and screening-agent flows.
"""

from __future__ import annotations

from datetime import datetime
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.context_builder import build_analysis_context  # noqa: E402
from analysis.providers.deterministic_provider import DeterministicTestAnalysisProvider  # noqa: E402
from analysis.providers.router import AnalysisModelRouter  # noqa: E402
from analysis.schemas import AnalysisSnapshot  # noqa: E402
from analysis.screening_agent import ScreeningAgent  # noqa: E402
from data_manager import DataManager  # noqa: E402
from models import Activity, Category, SourceStatus  # noqa: E402


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


def _pick_test_source(data_manager: DataManager):
    return next(
        (
            source
            for source in data_manager.get_sources_status()
            if getattr(source.type, "value", source.type) != "firecrawl"
        ),
        data_manager.get_sources_status()[0],
    )


def _create_activity(data_manager: DataManager, *, url: str, title: str, description: str, full_content: str) -> Activity:
    source = _pick_test_source(data_manager)
    now = datetime(2026, 3, 27, 14, 0, 0)
    activity = Activity(
        id=Activity.generate_id(source.id, url),
        title=title,
        description=description,
        full_content=full_content,
        source_id=source.id,
        source_name=source.name,
        url=url,
        category=Category.BOUNTY,
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)
    data_manager.update_source_status(source.id, SourceStatus.SUCCESS, activity_count=6)
    loaded = data_manager.get_activity_by_id(activity.id)
    assert loaded is not None
    return loaded


def test_context_builder_prefers_stored_activity_content_and_source_health(temp_db):
    data_manager = DataManager(db_path=temp_db)
    activity = _create_activity(
        data_manager,
        url="https://example.com/agent-context",
        title="Prize-rich bug bounty sprint",
        description="Short summary for first-pass screening.",
        full_content="Guaranteed reward payout within 7 days for a simple solo submission.",
    )
    current_snapshot = AnalysisSnapshot(
        status="watch",
        summary="Existing draft summary",
        reasons=["Need updated reward terms"],
        structured={"should_deep_research": True},
    )

    with data_manager._get_connection() as conn:
        source_row = data_manager._source_snapshot(conn, activity.source_id)

    context = build_analysis_context(activity, source_row, current_snapshot=current_snapshot)

    assert context.activity_id == activity.id
    assert context.content.full_text.startswith(activity.title)
    assert context.content.full_text.endswith(activity.full_content)
    assert context.source_health["freshness_level"] in {"fresh", "aging", "stale", "critical", "never"}
    assert context.current_snapshot is not None
    assert context.current_snapshot.summary == "Existing draft summary"
    assert context.heuristic_signals["roi_level"] in {"low", "medium", "high"}


def test_screening_agent_returns_structured_first_pass_without_research(temp_db):
    data_manager = DataManager(db_path=temp_db)
    activity = _create_activity(
        data_manager,
        url="https://example.com/agent-screening",
        title="Solo API security bounty",
        description="Guaranteed reward for quick API hardening.",
        full_content="Official organizer promises fast payout within 7 days and accepts individual work.",
    )

    with data_manager._get_connection() as conn:
        source_row = data_manager._source_snapshot(conn, activity.source_id)
    context = build_analysis_context(activity, source_row, current_snapshot=None)

    agent = ScreeningAgent(
        provider=DeterministicTestAnalysisProvider(
            screening_payload={
                "status": "pass",
                "summary": "High-signal solo bounty with clear rewards.",
                "reasons": ["Reward terms are explicit", "Solo participation looks supported"],
                "recommended_action": "queue_for_review",
                "confidence": 0.86,
                "structured": {
                    "should_deep_research": False,
                    "reward_clarity": "high",
                    "effort_level": "low",
                },
            }
        ),
        router=AnalysisModelRouter({"screening": {"low": "screening-cheap", "default": "screening-main"}}),
    )

    result = agent.run(context)

    assert result.status in {"pass", "watch", "reject"}
    assert result.research_state == "not_requested"
    assert "should_deep_research" in result.structured
    assert result.model_name == "screening-cheap"


def test_screening_agent_falls_back_to_heuristics_when_provider_fails(temp_db):
    class _FailingProvider:
        def generate_structured(self, **kwargs):
            raise RuntimeError("provider unavailable")

    data_manager = DataManager(db_path=temp_db)
    activity = _create_activity(
        data_manager,
        url="https://example.com/agent-screening-fallback",
        title="Unclear contest payout terms",
        description="Reward details are vague and organizer proof is limited.",
        full_content="Proposal required. Monthly review cycle. Reward mentioned but no firm amount.",
    )

    with data_manager._get_connection() as conn:
        source_row = data_manager._source_snapshot(conn, activity.source_id)
    context = build_analysis_context(activity, source_row, current_snapshot=None)

    agent = ScreeningAgent(
        provider=_FailingProvider(),
        router=AnalysisModelRouter({"screening": {"low": "screening-cheap", "default": "screening-main"}}),
    )

    result = agent.run(context)

    assert result.status in {"pass", "watch", "reject"}
    assert result.research_state == "not_requested"
    assert "should_deep_research" in result.structured
    assert "heuristic_fallback" in result.risk_flags
