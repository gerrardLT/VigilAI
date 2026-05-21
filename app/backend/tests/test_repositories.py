"""Integration tests for AnalysisRepository, DigestRepository, and SourceRepository.

Validates requirements 7.2 (async CRUD via repositories) and 7.4 (parameterized queries).
Uses in-memory SQLite via SQLitePool(":memory:").
"""

import pytest
import pytest_asyncio

from repositories import AnalysisRepository, DigestRepository, SourceRepository
from db.connection_pool import SQLitePool


# ---------------------------------------------------------------------------
# Schema DDL (subset of 001_initial_schema.sql relevant to these repositories)
# ---------------------------------------------------------------------------

SOURCES_DDL = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    priority TEXT NOT NULL,
    update_interval INTEGER NOT NULL,
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    last_success TEXT,
    status TEXT DEFAULT 'idle',
    error_message TEXT,
    activity_count INTEGER DEFAULT 0
);
"""

ANALYSIS_TEMPLATES_DDL = """
CREATE TABLE IF NOT EXISTS analysis_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    tags TEXT NOT NULL,
    layers TEXT NOT NULL,
    sort_fields TEXT NOT NULL,
    preference_profile TEXT,
    risk_tolerance TEXT,
    research_mode TEXT,
    compiled_policy TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

ANALYSIS_JOBS_DDL = """
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id TEXT PRIMARY KEY,
    trigger_type TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    template_id TEXT,
    route_policy TEXT,
    budget_policy TEXT,
    status TEXT NOT NULL,
    requested_by TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);
"""

ANALYSIS_JOB_ITEMS_DDL = """
CREATE TABLE IF NOT EXISTS analysis_job_items (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    status TEXT NOT NULL,
    needs_research INTEGER DEFAULT 0,
    final_draft_status TEXT,
    screening_model TEXT,
    research_model TEXT,
    verdict_model TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

DIGESTS_DDL = """
CREATE TABLE IF NOT EXISTS digests (
    id TEXT PRIMARY KEY,
    digest_date TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    item_ids TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_sent_at TEXT,
    send_channel TEXT
);
"""

DIGEST_CANDIDATES_DDL = """
CREATE TABLE IF NOT EXISTS digest_candidates (
    digest_date TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (digest_date, activity_id)
);
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def analysis_repo():
    pool = SQLitePool(":memory:")
    await pool.initialize()
    async with pool.acquire() as conn:
        await conn.execute(ANALYSIS_TEMPLATES_DDL)
        await conn.execute(ANALYSIS_JOBS_DDL)
        await conn.execute(ANALYSIS_JOB_ITEMS_DDL)
        await conn.commit()
    repo = AnalysisRepository(pool)
    yield repo
    await pool.close_all()


@pytest_asyncio.fixture
async def digest_repo():
    pool = SQLitePool(":memory:")
    await pool.initialize()
    async with pool.acquire() as conn:
        await conn.execute(DIGESTS_DDL)
        await conn.execute(DIGEST_CANDIDATES_DDL)
        await conn.commit()
    repo = DigestRepository(pool)
    yield repo
    await pool.close_all()


@pytest_asyncio.fixture
async def source_repo():
    pool = SQLitePool(":memory:")
    await pool.initialize()
    async with pool.acquire() as conn:
        await conn.execute(SOURCES_DDL)
        await conn.commit()
    repo = SourceRepository(pool)
    yield repo
    await pool.close_all()


# ===========================================================================
# AnalysisRepository — Templates
# ===========================================================================


@pytest.mark.asyncio
async def test_create_and_get_template(analysis_repo):
    template = await analysis_repo.create_template({
        "name": "Default Template",
        "slug": "default-template",
        "description": "A test template",
        "is_default": True,
        "tags": ["ai", "web3"],
        "layers": ["screening", "research"],
        "sort_fields": ["score"],
    })

    assert template["name"] == "Default Template"
    assert template["slug"] == "default-template"
    assert template["is_default"] is True
    assert template["tags"] == ["ai", "web3"]
    assert template["layers"] == ["screening", "research"]

    # Retrieve by ID
    fetched = await analysis_repo.get_template_by_id(template["id"])
    assert fetched is not None
    assert fetched["id"] == template["id"]
    assert fetched["name"] == "Default Template"


@pytest.mark.asyncio
async def test_get_default_template(analysis_repo):
    # No templates yet
    result = await analysis_repo.get_default_template()
    assert result is None

    # Create a non-default template
    await analysis_repo.create_template({
        "name": "Non-Default",
        "slug": "non-default",
        "is_default": False,
        "tags": [],
        "layers": [],
        "sort_fields": [],
    })

    # Create a default template
    await analysis_repo.create_template({
        "name": "The Default",
        "slug": "the-default",
        "is_default": True,
        "tags": [],
        "layers": [],
        "sort_fields": [],
    })

    default = await analysis_repo.get_default_template()
    assert default is not None
    assert default["name"] == "The Default"
    assert default["is_default"] is True


@pytest.mark.asyncio
async def test_list_templates(analysis_repo):
    await analysis_repo.create_template({
        "name": "Template A",
        "slug": "template-a",
        "tags": [],
        "layers": [],
        "sort_fields": [],
    })
    await analysis_repo.create_template({
        "name": "Template B",
        "slug": "template-b",
        "is_default": True,
        "tags": [],
        "layers": [],
        "sort_fields": [],
    })

    templates = await analysis_repo.list_templates()
    assert len(templates) == 2
    # Default template should come first
    assert templates[0]["name"] == "Template B"
    assert templates[0]["is_default"] is True


# ===========================================================================
# AnalysisRepository — Jobs
# ===========================================================================


@pytest.mark.asyncio
async def test_create_and_get_job(analysis_repo):
    job = await analysis_repo.create_job({
        "trigger_type": "manual",
        "scope_type": "full",
        "status": "pending",
        "requested_by": "user-1",
    })

    assert job["trigger_type"] == "manual"
    assert job["scope_type"] == "full"
    assert job["status"] == "pending"
    assert job["requested_by"] == "user-1"
    assert job["created_at"] is not None

    # Retrieve by ID
    fetched = await analysis_repo.get_job_by_id(job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]
    assert fetched["trigger_type"] == "manual"


@pytest.mark.asyncio
async def test_update_job_status(analysis_repo):
    job = await analysis_repo.create_job({
        "trigger_type": "scheduled",
        "scope_type": "incremental",
        "status": "pending",
    })

    # Update to running
    updated = await analysis_repo.update_job_status(job["id"], "running")
    assert updated is not None
    assert updated["status"] == "running"
    assert updated["finished_at"] is None

    # Update to completed — should auto-set finished_at
    completed = await analysis_repo.update_job_status(job["id"], "completed")
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["finished_at"] is not None

    # Update non-existent job
    result = await analysis_repo.update_job_status("nonexistent", "failed")
    assert result is None


# ===========================================================================
# AnalysisRepository — Job Items
# ===========================================================================


@pytest.mark.asyncio
async def test_create_and_list_job_items(analysis_repo):
    job = await analysis_repo.create_job({
        "trigger_type": "manual",
        "scope_type": "full",
        "status": "running",
    })

    # Create two job items
    item1 = await analysis_repo.create_job_item({
        "job_id": job["id"],
        "activity_id": "activity-1",
        "status": "pending",
        "needs_research": True,
    })
    item2 = await analysis_repo.create_job_item({
        "job_id": job["id"],
        "activity_id": "activity-2",
        "status": "pending",
        "needs_research": False,
    })

    assert item1["job_id"] == job["id"]
    assert item1["activity_id"] == "activity-1"
    assert item1["needs_research"] is True
    assert item2["needs_research"] is False

    # List items by job ID
    items = await analysis_repo.list_job_items_by_job_id(job["id"])
    assert len(items) == 2
    assert items[0]["activity_id"] == "activity-1"
    assert items[1]["activity_id"] == "activity-2"

    # Get single item by ID
    fetched = await analysis_repo.get_job_item_by_id(item1["id"])
    assert fetched is not None
    assert fetched["activity_id"] == "activity-1"


# ===========================================================================
# DigestRepository — Digests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_and_get_digest(digest_repo):
    digest = await digest_repo.create({
        "digest_date": "2025-01-15",
        "title": "Daily Digest",
        "content": "Here are today's highlights.",
        "item_ids": ["item-1", "item-2"],
        "summary": "Two items found.",
    })

    assert digest["title"] == "Daily Digest"
    assert digest["digest_date"] == "2025-01-15"
    assert digest["item_ids"] == ["item-1", "item-2"]
    assert digest["status"] == "draft"
    assert digest["created_at"] is not None

    # Retrieve by ID
    fetched = await digest_repo.get_by_id(digest["id"])
    assert fetched is not None
    assert fetched["id"] == digest["id"]
    assert fetched["title"] == "Daily Digest"


@pytest.mark.asyncio
async def test_list_digests(digest_repo):
    await digest_repo.create({
        "digest_date": "2025-01-14",
        "title": "Digest A",
        "content": "Content A",
        "item_ids": [],
    })
    await digest_repo.create({
        "digest_date": "2025-01-15",
        "title": "Digest B",
        "content": "Content B",
        "item_ids": [],
    })

    digests = await digest_repo.list_digests()
    assert len(digests) == 2
    # Ordered by digest_date DESC
    assert digests[0]["title"] == "Digest B"
    assert digests[1]["title"] == "Digest A"


@pytest.mark.asyncio
async def test_update_status_to_sent(digest_repo):
    digest = await digest_repo.create({
        "digest_date": "2025-01-15",
        "title": "To Send",
        "content": "Content",
        "item_ids": ["x"],
    })

    updated = await digest_repo.update_status(digest["id"], "sent")
    assert updated is not None
    assert updated["status"] == "sent"
    assert updated["last_sent_at"] is not None

    # Update non-existent digest
    result = await digest_repo.update_status("nonexistent", "sent")
    assert result is None


# ===========================================================================
# DigestRepository — Candidates
# ===========================================================================


@pytest.mark.asyncio
async def test_add_and_list_candidates(digest_repo):
    # Add candidates
    added1 = await digest_repo.add_candidate("activity-1", "2025-01-15")
    added2 = await digest_repo.add_candidate("activity-2", "2025-01-15")
    assert added1 is True
    assert added2 is True

    # Duplicate insert should return False
    dup = await digest_repo.add_candidate("activity-1", "2025-01-15")
    assert dup is False

    # List candidates for a specific date
    candidates = await digest_repo.list_candidates("2025-01-15")
    assert len(candidates) == 2
    activity_ids = {c["activity_id"] for c in candidates}
    assert "activity-1" in activity_ids
    assert "activity-2" in activity_ids


@pytest.mark.asyncio
async def test_remove_candidate(digest_repo):
    await digest_repo.add_candidate("activity-1", "2025-01-15")

    # Remove existing candidate
    removed = await digest_repo.remove_candidate("activity-1", "2025-01-15")
    assert removed is True

    # Remove non-existent candidate
    removed_again = await digest_repo.remove_candidate("activity-1", "2025-01-15")
    assert removed_again is False

    # Verify list is empty
    candidates = await digest_repo.list_candidates("2025-01-15")
    assert len(candidates) == 0


# ===========================================================================
# SourceRepository
# ===========================================================================


@pytest.mark.asyncio
async def test_upsert_and_get(source_repo):
    source = await source_repo.upsert({
        "id": "src-1",
        "name": "Devpost",
        "type": "scraper",
        "url": "https://devpost.com",
        "priority": "high",
        "update_interval": 3600,
        "enabled": 1,
        "status": "idle",
    })

    assert source["id"] == "src-1"
    assert source["name"] == "Devpost"
    assert source["priority"] == "high"
    assert source["status"] == "idle"

    # Retrieve by ID
    fetched = await source_repo.get_by_id("src-1")
    assert fetched is not None
    assert fetched["name"] == "Devpost"

    # Upsert (update) the same source
    updated = await source_repo.upsert({
        "id": "src-1",
        "name": "Devpost Updated",
        "type": "scraper",
        "url": "https://devpost.com",
        "priority": "critical",
        "update_interval": 1800,
    })
    assert updated["name"] == "Devpost Updated"
    assert updated["priority"] == "critical"

    # Get non-existent
    missing = await source_repo.get_by_id("nonexistent")
    assert missing is None


@pytest.mark.asyncio
async def test_list_all(source_repo):
    await source_repo.upsert({
        "id": "src-low",
        "name": "Low Priority",
        "type": "rss",
        "url": "https://example.com/low",
        "priority": "low",
        "update_interval": 7200,
    })
    await source_repo.upsert({
        "id": "src-high",
        "name": "High Priority",
        "type": "scraper",
        "url": "https://example.com/high",
        "priority": "high",
        "update_interval": 3600,
    })
    await source_repo.upsert({
        "id": "src-critical",
        "name": "Critical Priority",
        "type": "api",
        "url": "https://example.com/critical",
        "priority": "critical",
        "update_interval": 1800,
    })

    sources = await source_repo.list_all()
    assert len(sources) == 3
    # Ordered by priority: critical, high, low
    assert sources[0]["priority"] == "critical"
    assert sources[1]["priority"] == "high"
    assert sources[2]["priority"] == "low"


@pytest.mark.asyncio
async def test_update_status_success(source_repo):
    await source_repo.upsert({
        "id": "src-1",
        "name": "Test Source",
        "type": "scraper",
        "url": "https://example.com",
        "priority": "medium",
        "update_interval": 3600,
    })

    result = await source_repo.update_status(
        "src-1", "success", activity_count=42
    )
    assert result is True

    source = await source_repo.get_by_id("src-1")
    assert source["status"] == "success"
    assert source["activity_count"] == 42
    assert source["last_run"] is not None
    assert source["last_success"] is not None
    # Error message should be cleared on success
    assert source["error_message"] is None


@pytest.mark.asyncio
async def test_update_status_error(source_repo):
    await source_repo.upsert({
        "id": "src-1",
        "name": "Test Source",
        "type": "scraper",
        "url": "https://example.com",
        "priority": "medium",
        "update_interval": 3600,
    })

    result = await source_repo.update_status(
        "src-1", "error", error_message="Connection timeout"
    )
    assert result is True

    source = await source_repo.get_by_id("src-1")
    assert source["status"] == "error"
    assert source["error_message"] == "Connection timeout"
    assert source["last_run"] is not None
    # last_success should NOT be set on error
    assert source["last_success"] is None

    # Update non-existent source
    result = await source_repo.update_status("nonexistent", "error")
    assert result is False
