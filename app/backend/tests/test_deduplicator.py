"""
CrossDomainDeduplicator 单元测试
Validates: Requirements 19.1, 19.4
"""

import os
import sys
import uuid
from datetime import datetime

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection_pool import SQLitePool
from services.deduplicator import CrossDomainDeduplicator


@pytest.fixture
def temp_db():
    """创建临时数据库路径"""
    temp_root = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(temp_root, exist_ok=True)
    db_path = os.path.join(temp_root, f"{uuid.uuid4().hex}.db")
    try:
        yield db_path
    finally:
        for suffix in ("", "-wal", "-shm"):
            path = db_path + suffix
            if os.path.exists(path):
                os.remove(path)


@pytest_asyncio.fixture
async def pool(temp_db):
    """创建连接池并初始化 activities、reward_opportunities 和 duplicate_links 表"""
    p = SQLitePool(temp_db, max_size=3)
    await p.initialize()
    async with p.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT DEFAULT 'upcoming',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source_id, url)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reward_opportunities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_platform TEXT NOT NULL,
                source_url TEXT NOT NULL,
                ai_stage_2_label TEXT NOT NULL DEFAULT 'unknown',
                ai_confidence REAL NOT NULL DEFAULT 0.0,
                ai_missing_evidence TEXT NOT NULL DEFAULT '[]',
                ai_risk_flags TEXT NOT NULL DEFAULT '[]',
                ai_structured_evidence TEXT NOT NULL DEFAULT '{}',
                external_links_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_links (
                id TEXT PRIMARY KEY,
                source_domain TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_domain TEXT NOT NULL,
                target_id TEXT NOT NULL,
                similarity_score REAL,
                match_type TEXT NOT NULL,
                overridden BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await conn.commit()
    yield p
    await p.close_all()


@pytest_asyncio.fixture
async def deduplicator(pool):
    """创建 CrossDomainDeduplicator 实例"""
    return CrossDomainDeduplicator(pool)


@pytest_asyncio.fixture
async def seeded_pool(pool):
    """插入测试数据用于 URL 和标题匹配场景"""
    now = datetime.now().isoformat()
    async with pool.acquire() as conn:
        # 插入 activities 测试数据
        await conn.execute(
            """INSERT INTO activities (id, title, source_id, source_name, url, category, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("act-001", "Global AI Hackathon 2024", "devpost", "Devpost",
             "https://devpost.com/hackathons/ai-2024", "hackathon", now, now),
        )
        await conn.execute(
            """INSERT INTO activities (id, title, source_id, source_name, url, category, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("act-002", "Web3 Builder Challenge", "dorahacks", "DoraHacks",
             "https://dorahacks.io/web3-challenge", "hackathon", now, now),
        )
        # 插入 reward_opportunities 测试数据
        await conn.execute(
            """INSERT INTO reward_opportunities (id, title, source_platform, source_url, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("reward-001", "Blockchain Security Bounty", "immunefi",
             "https://immunefi.com/bounty/security", now),
        )
        await conn.commit()
    return pool


class TestCheckDuplicate:
    """check_duplicate 方法测试"""

    @pytest.mark.asyncio
    async def test_url_match_detects_duplicate(self, deduplicator, seeded_pool):
        """相同 URL 的机会应被检测为重复
        Validates: Requirement 19.1
        """
        opportunity = {
            "url": "https://devpost.com/hackathons/ai-2024",
            "title": "Some Different Title",
        }
        result = await deduplicator.check_duplicate(opportunity)

        assert result is not None
        assert result["id"] == "act-001"
        assert result["url"] == "https://devpost.com/hackathons/ai-2024"
        assert result["domain"] == "opportunity"

    @pytest.mark.asyncio
    async def test_title_similarity_detects_duplicate(self, deduplicator, seeded_pool):
        """标题相似度 >0.85 的机会应被检测为重复
        Validates: Requirement 19.1
        """
        # "Global AI Hackathon 2024" vs "Global AI Hackathon 2024 Edition" 相似度 > 0.85
        opportunity = {
            "url": "https://other-site.com/different-url",
            "title": "Global AI Hackathon 2024 Edition",
        }
        result = await deduplicator.check_duplicate(opportunity)

        assert result is not None
        assert result["id"] == "act-001"
        assert result["title"] == "Global AI Hackathon 2024"

    @pytest.mark.asyncio
    async def test_dissimilar_title_not_detected(self, deduplicator, seeded_pool):
        """标题差异较大的机会不应被检测为重复
        Validates: Requirement 19.1
        """
        opportunity = {
            "url": "https://completely-different.com/new-event",
            "title": "Machine Learning Workshop for Beginners",
        }
        result = await deduplicator.check_duplicate(opportunity)

        assert result is None


class TestMarkDuplicate:
    """mark_duplicate 方法测试"""

    @pytest.mark.asyncio
    async def test_mark_duplicate_persists_link(self, deduplicator, pool):
        """mark_duplicate 应在 duplicate_links 表中持久化记录
        Validates: Requirement 19.1
        """
        result = await deduplicator.mark_duplicate(
            source_domain="opportunity",
            source_id="act-new-001",
            target_domain="reward",
            target_id="reward-001",
            similarity_score=0.92,
            match_type="title",
        )

        assert "id" in result
        assert result["source_id"] == "act-new-001"
        assert result["target_id"] == "reward-001"
        assert result["match_type"] == "title"

        # 验证数据库中确实存在该记录
        async with pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM duplicate_links WHERE id = ?", (result["id"],)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row["source_domain"] == "opportunity"
            assert row["target_domain"] == "reward"
            assert row["similarity_score"] == 0.92
            assert row["overridden"] == 0


class TestOverrideDuplicate:
    """override_duplicate 方法测试"""

    @pytest.mark.asyncio
    async def test_override_duplicate_sets_overridden_flag(self, deduplicator, pool):
        """override_duplicate 应将 overridden 标志设为 1
        Validates: Requirement 19.4
        """
        # 先创建一条 duplicate link
        link = await deduplicator.mark_duplicate(
            source_domain="opportunity",
            source_id="act-override-001",
            target_domain="reward",
            target_id="reward-override-001",
            similarity_score=1.0,
            match_type="url",
        )

        # 执行 override
        success = await deduplicator.override_duplicate(link["id"])
        assert success is True

        # 验证数据库中 overridden 已设为 1
        async with pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT overridden FROM duplicate_links WHERE id = ?", (link["id"],)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row["overridden"] == 1


class TestListDuplicates:
    """list_duplicates 方法测试"""

    @pytest.mark.asyncio
    async def test_list_duplicates_excludes_overridden(self, deduplicator, pool):
        """list_duplicates 应排除已被 override 的记录
        Validates: Requirement 19.4
        """
        # 创建两条 duplicate links
        link1 = await deduplicator.mark_duplicate(
            source_domain="opportunity",
            source_id="act-list-001",
            target_domain="reward",
            target_id="reward-list-001",
            similarity_score=0.90,
            match_type="title",
        )
        link2 = await deduplicator.mark_duplicate(
            source_domain="opportunity",
            source_id="act-list-002",
            target_domain="reward",
            target_id="reward-list-002",
            similarity_score=1.0,
            match_type="url",
        )

        # Override 第一条
        await deduplicator.override_duplicate(link1["id"])

        # list_duplicates 应只返回未被 override 的记录
        duplicates = await deduplicator.list_duplicates()
        duplicate_ids = [d["id"] for d in duplicates]

        assert link1["id"] not in duplicate_ids
        assert link2["id"] in duplicate_ids
