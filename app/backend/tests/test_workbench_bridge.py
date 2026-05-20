"""
WorkbenchBridge 单元测试
Validates: Requirements 18.2, 18.4
"""

import os
import sys
import uuid

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection_pool import SQLitePool
from services.workbench_bridge import WorkbenchBridge


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
    """创建连接池并初始化 activities 和 selection_opportunities 表"""
    p = SQLitePool(temp_db, max_size=3)
    await p.initialize()
    async with p.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                description TEXT DEFAULT '',
                source_id TEXT DEFAULT '',
                source_name TEXT DEFAULT '',
                url TEXT DEFAULT '',
                category TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'upcoming',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS selection_opportunities (
                id TEXT PRIMARY KEY,
                query_id TEXT DEFAULT '',
                platform TEXT DEFAULT '',
                platform_item_id TEXT DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                source_urls TEXT DEFAULT '[]',
                source_mode TEXT DEFAULT '',
                snapshot_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await conn.commit()
    yield p
    await p.close_all()


@pytest_asyncio.fixture
async def bridge(pool):
    """创建 WorkbenchBridge 实例"""
    return WorkbenchBridge(pool)


class TestWorkbenchBridge:
    """WorkbenchBridge 核心功能测试"""

    @pytest.mark.asyncio
    async def test_save_opportunity_creates_activity_record(self, bridge, pool):
        """保存 opportunity 域的 payload 应在 activities 表中创建记录
        Validates: Requirement 18.2
        """
        result = await bridge.save_to_workbench(
            session_id="session-001",
            turn_id="turn-001",
            payload={
                "domain": "opportunity",
                "title": "Test Hackathon",
                "url": "https://example.com/hackathon",
                "description": "A test hackathon opportunity",
                "category": "hackathon",
                "source_name": "Devpost",
            },
        )

        assert result["status"] == "created"
        assert result["domain"] == "opportunity"
        assert "id" in result

        # 验证数据库中确实存在该记录
        async with pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM activities WHERE id = ?", (result["id"],)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row["title"] == "Test Hackathon"
            assert row["url"] == "https://example.com/hackathon"
            assert row["source_name"] == "Devpost"

    @pytest.mark.asyncio
    async def test_save_selection_creates_selection_record(self, bridge, pool):
        """保存 product_selection 域的 payload 应在 selection_opportunities 表中创建记录
        Validates: Requirement 18.2
        """
        result = await bridge.save_to_workbench(
            session_id="session-002",
            turn_id="turn-002",
            payload={
                "domain": "product_selection",
                "title": "Bluetooth Earbuds Market",
                "url": "https://example.com/product/earbuds",
            },
        )

        assert result["status"] == "created"
        assert result["domain"] == "product_selection"
        assert "id" in result

        # 验证数据库中确实存在该记录
        async with pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM selection_opportunities WHERE id = ?", (result["id"],)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row["title"] == "Bluetooth Earbuds Market"
            assert "https://example.com/product/earbuds" in row["source_urls"]

    @pytest.mark.asyncio
    async def test_duplicate_url_returns_duplicate_status(self, bridge, pool):
        """相同 URL 的第二次保存应返回 duplicate 状态
        Validates: Requirement 18.4
        """
        payload = {
            "domain": "opportunity",
            "title": "Duplicate Test",
            "url": "https://example.com/duplicate-test",
        }

        # 第一次保存应成功
        first_result = await bridge.save_to_workbench(
            session_id="session-003",
            turn_id="turn-003",
            payload=payload,
        )
        assert first_result["status"] == "created"

        # 第二次保存相同 URL 应返回 duplicate
        second_result = await bridge.save_to_workbench(
            session_id="session-004",
            turn_id="turn-004",
            payload=payload,
        )
        assert second_result["status"] == "duplicate"
        assert "existing_id" in second_result

    @pytest.mark.asyncio
    async def test_empty_url_does_not_trigger_dedup(self, bridge, pool):
        """空 URL 不应触发去重检查，每次都应创建新记录
        Validates: Requirement 18.4
        """
        payload_no_url = {
            "domain": "opportunity",
            "title": "No URL Opportunity",
            "url": "",
        }

        # 第一次保存
        first_result = await bridge.save_to_workbench(
            session_id="session-005",
            turn_id="turn-005",
            payload=payload_no_url,
        )
        assert first_result["status"] == "created"

        # 第二次保存空 URL 也应成功创建（不触发去重）
        second_result = await bridge.save_to_workbench(
            session_id="session-006",
            turn_id="turn-006",
            payload=payload_no_url,
        )
        assert second_result["status"] == "created"
        # 两次创建的 ID 应不同
        assert first_result["id"] != second_result["id"]
