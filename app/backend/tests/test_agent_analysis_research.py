"""
Tests for guarded research mode and evidence persistence.
"""

from __future__ import annotations

from datetime import datetime
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.context_builder import build_analysis_context  # noqa: E402
from analysis.policies import ResearchPolicy  # noqa: E402
from analysis.research_agent import ResearchAgent  # noqa: E402
from analysis.research_fetcher import FetchedDocument, ResearchFetcher  # noqa: E402
from analysis.schemas import ScreeningResult  # noqa: E402
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


def _build_context(data_manager: DataManager):
    source = _pick_test_source(data_manager)
    now = datetime(2026, 3, 27, 16, 0, 0)
    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/research-context"),
        title="Official API bounty with unclear reward cap",
        description="Organizer mentions reward but exact amount is missing.",
        full_content="Official docs exist, but payout wording is vague and requires cross-checking search results.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/research-context",
        category=Category.BOUNTY,
        created_at=now,
        updated_at=now,
    )
    data_manager.add_activity(activity)
    data_manager.update_source_status(source.id, SourceStatus.SUCCESS, activity_count=4)
    loaded = data_manager.get_activity_by_id(activity.id)
    assert loaded is not None
    with data_manager._get_connection() as conn:
        source_row = data_manager._source_snapshot(conn, loaded.source_id)
    return build_analysis_context(loaded, source_row, current_snapshot=None)


def test_research_agent_respects_url_budget_and_allowed_source_classes(temp_db):
    data_manager = DataManager(db_path=temp_db)
    context = _build_context(data_manager)
    screening_result = ScreeningResult(
        status="watch",
        summary="Need reward verification",
        reasons=["Reward cap is unclear"],
        structured={"should_deep_research": True},
    )
    research_agent = ResearchAgent(
        fetcher=ResearchFetcher(
            documents=[
                FetchedDocument(
                    source_type="official",
                    url="https://example.com/official",
                    title="Official terms",
                    snippet="Official reward terms are partially documented.",
                    trust_score=0.92,
                ),
                FetchedDocument(
                    source_type="search",
                    url="https://search.example.com/result",
                    title="Search summary",
                    snippet="Search result summarises the missing reward cap.",
                    trust_score=0.64,
                ),
                FetchedDocument(
                    source_type="forum",
                    url="https://forum.example.com/thread",
                    title="Forum rumor",
                    snippet="Unverified forum chatter.",
                    trust_score=0.18,
                ),
            ]
        )
    )

    result = research_agent.run(
        context=context,
        screening_result=screening_result,
        policy=ResearchPolicy(max_urls_per_item=2, allowed_source_classes=["official", "search"]),
    )

    assert result.state == "completed"
    assert len(result.evidence) <= 2
    assert all(item.source_type in {"official", "search"} for item in result.evidence)


def test_research_agent_marks_unavailable_state_when_budget_is_exhausted(temp_db):
    data_manager = DataManager(db_path=temp_db)
    context = _build_context(data_manager)
    screening_result = ScreeningResult(
        status="watch",
        summary="Need reward verification",
        reasons=["Reward cap is unclear"],
        structured={"should_deep_research": True},
    )
    research_agent = ResearchAgent(fetcher=ResearchFetcher(documents=[]))

    result = research_agent.run(
        context=context,
        screening_result=screening_result,
        policy=ResearchPolicy(max_urls_per_item=0),
    )

    assert result.state == "research_unavailable"
    assert result.evidence == []


def test_data_manager_round_trips_research_evidence_records(temp_db):
    data_manager = DataManager(db_path=temp_db)
    context = _build_context(data_manager)
    screening_result = ScreeningResult(
        status="watch",
        summary="Need reward verification",
        reasons=["Reward cap is unclear"],
        structured={"should_deep_research": True},
    )
    research_agent = ResearchAgent(
        fetcher=ResearchFetcher(
            documents=[
                FetchedDocument(
                    source_type="official",
                    url="https://example.com/official",
                    title="Official terms",
                    snippet="Official reward terms are partially documented.",
                    trust_score=0.92,
                ),
                FetchedDocument(
                    source_type="search",
                    url="https://search.example.com/result",
                    title="Search summary",
                    snippet="Search result summarises the missing reward cap.",
                    trust_score=0.64,
                ),
            ]
        )
    )

    result = research_agent.run(
        context=context,
        screening_result=screening_result,
        policy=ResearchPolicy(max_urls_per_item=2, allowed_source_classes=["official", "search"]),
    )

    stored = data_manager.replace_analysis_evidence("job-item-1", result.evidence)
    loaded = data_manager.get_analysis_evidence("job-item-1")

    assert len(stored) == 2
    assert [item.source_type for item in loaded] == ["official", "search"]
    assert loaded[0].url == "https://example.com/official"
