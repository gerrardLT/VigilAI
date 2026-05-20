"""Integration tests for OpportunityRepository."""

import asyncio
import pytest
import pytest_asyncio

from repositories import OpportunityRepository
from db.connection_pool import SQLitePool


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    full_content TEXT,
    source_id TEXT,
    source_name TEXT,
    url TEXT,
    category TEXT,
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
    status TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""

CREATE_TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tracking_items (
    activity_id TEXT PRIMARY KEY,
    is_favorited INTEGER DEFAULT 0,
    status TEXT,
    stage TEXT,
    notes TEXT,
    next_action TEXT,
    remind_at TEXT,
    block_reason TEXT,
    abandon_reason TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""


@pytest_asyncio.fixture
async def repo():
    pool = SQLitePool(":memory:")
    await pool.initialize()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
        await conn.execute(CREATE_TRACKING_TABLE_SQL)
        await conn.commit()
    repository = OpportunityRepository(pool)
    yield repository
    await pool.close_all()


@pytest.fixture
def sample_activity():
    return {
        "id": "test-1",
        "title": "Test Hackathon",
        "description": "A great hackathon",
        "source_id": "devpost",
        "source_name": "Devpost",
        "url": "https://example.com/hack",
        "category": "hackathon",
        "tags": ["ai", "web3"],
        "status": "active",
        "score": 75.0,
        "trust_level": "high",
        "deadline_level": "soon",
    }


@pytest.mark.asyncio
async def test_create_returns_true(repo, sample_activity):
    result = await repo.create(sample_activity)
    assert result is True


@pytest.mark.asyncio
async def test_create_duplicate_returns_false(repo, sample_activity):
    await repo.create(sample_activity)
    result = await repo.create(sample_activity)
    assert result is False


@pytest.mark.asyncio
async def test_get_by_id_found(repo, sample_activity):
    await repo.create(sample_activity)
    row = await repo.get_by_id("test-1")
    assert row is not None
    assert row["title"] == "Test Hackathon"
    assert row["source_id"] == "devpost"


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo):
    row = await repo.get_by_id("nonexistent")
    assert row is None


@pytest.mark.asyncio
async def test_update_existing(repo, sample_activity):
    await repo.create(sample_activity)
    result = await repo.update("test-1", {"title": "Updated Title", "score": 90.0})
    assert result is True
    row = await repo.get_by_id("test-1")
    assert row["title"] == "Updated Title"
    assert row["score"] == 90.0


@pytest.mark.asyncio
async def test_update_nonexistent(repo):
    result = await repo.update("nonexistent", {"title": "X"})
    assert result is False


@pytest.mark.asyncio
async def test_update_empty_fields(repo, sample_activity):
    await repo.create(sample_activity)
    result = await repo.update("test-1", {})
    assert result is False


@pytest.mark.asyncio
async def test_delete_existing(repo, sample_activity):
    await repo.create(sample_activity)
    result = await repo.delete("test-1")
    assert result is True
    row = await repo.get_by_id("test-1")
    assert row is None


@pytest.mark.asyncio
async def test_delete_nonexistent(repo):
    result = await repo.delete("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_count_no_filters(repo, sample_activity):
    await repo.create(sample_activity)
    total = await repo.count()
    assert total == 1


@pytest.mark.asyncio
async def test_count_with_filter(repo, sample_activity):
    await repo.create(sample_activity)
    total = await repo.count({"source_id": "devpost"})
    assert total == 1
    total = await repo.count({"source_id": "other"})
    assert total == 0


@pytest.mark.asyncio
async def test_list_activities_basic(repo, sample_activity):
    await repo.create(sample_activity)
    items, total = await repo.list_activities(page=1, page_size=10)
    assert total == 1
    assert len(items) == 1
    assert items[0]["title"] == "Test Hackathon"


@pytest.mark.asyncio
async def test_list_activities_search_filter(repo, sample_activity):
    await repo.create(sample_activity)
    items, total = await repo.list_activities(
        page=1, page_size=10, filters={"search": "Hackathon"}
    )
    assert total == 1

    items, total = await repo.list_activities(
        page=1, page_size=10, filters={"search": "nonexistent"}
    )
    assert total == 0


@pytest.mark.asyncio
async def test_list_activities_category_filter(repo, sample_activity):
    await repo.create(sample_activity)
    items, total = await repo.list_activities(
        page=1, page_size=10, filters={"category": "hackathon"}
    )
    assert total == 1

    items, total = await repo.list_activities(
        page=1, page_size=10, filters={"category": "bounty"}
    )
    assert total == 0


@pytest.mark.asyncio
async def test_list_activities_pagination(repo):
    for i in range(5):
        await repo.create({
            "id": f"item-{i}",
            "title": f"Activity {i}",
            "source_id": "devpost",
            "url": f"https://example.com/{i}",
            "category": "hackathon",
            "status": "active",
        })

    items, total = await repo.list_activities(page=1, page_size=2)
    assert total == 5
    assert len(items) == 2

    items, total = await repo.list_activities(page=3, page_size=2)
    assert total == 5
    assert len(items) == 1


@pytest.mark.asyncio
async def test_list_activities_sort(repo):
    await repo.create({
        "id": "a1",
        "title": "Alpha",
        "source_id": "devpost",
        "url": "https://example.com/a",
        "category": "hackathon",
        "status": "active",
        "score": 50.0,
    })
    await repo.create({
        "id": "a2",
        "title": "Beta",
        "source_id": "devpost",
        "url": "https://example.com/b",
        "category": "hackathon",
        "status": "active",
        "score": 90.0,
    })

    items, _ = await repo.list_activities(
        page=1, page_size=10, sort_by="score", sort_order="desc"
    )
    assert items[0]["title"] == "Beta"
    assert items[1]["title"] == "Alpha"

    items, _ = await repo.list_activities(
        page=1, page_size=10, sort_by="score", sort_order="asc"
    )
    assert items[0]["title"] == "Alpha"
    assert items[1]["title"] == "Beta"


@pytest.mark.asyncio
async def test_list_excludes_news_by_default(repo):
    await repo.create({
        "id": "news-1",
        "title": "News Item",
        "source_id": "rss",
        "url": "https://example.com/news",
        "category": "news",
        "status": "active",
    })
    await repo.create({
        "id": "hack-1",
        "title": "Hackathon Item",
        "source_id": "devpost",
        "url": "https://example.com/hack",
        "category": "hackathon",
        "status": "active",
    })

    items, total = await repo.list_activities(page=1, page_size=10)
    assert total == 1
    assert items[0]["category"] == "hackathon"


@pytest.mark.asyncio
async def test_json_fields_serialized(repo):
    await repo.create({
        "id": "json-test",
        "title": "JSON Test",
        "source_id": "devpost",
        "url": "https://example.com/json",
        "category": "hackathon",
        "status": "active",
        "tags": ["tag1", "tag2"],
        "analysis_fields": {"key": "value"},
    })
    row = await repo.get_by_id("json-test")
    # JSON fields should be stored as strings
    assert isinstance(row["tags"], str)
    assert "tag1" in row["tags"]
