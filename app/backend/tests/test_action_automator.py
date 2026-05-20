"""
ActionAutomator 单元测试
Validates: Requirements 17.1, 17.4
"""

import os
import sys
import uuid

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection_pool import SQLitePool
from services.action_automator import ActionAutomator, ActionType


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
    """创建连接池并初始化 action_recommendations 表"""
    p = SQLitePool(temp_db, max_size=3)
    await p.initialize()
    async with p.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS action_recommendations (
                id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                label TEXT NOT NULL,
                deadline TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                executed_at TEXT
            )
        """)
        await conn.commit()
    yield p
    await p.close_all()


@pytest_asyncio.fixture
async def automator(pool):
    """创建 ActionAutomator 实例"""
    return ActionAutomator(pool)


class TestGenerateActions:
    """generate_actions 方法测试"""

    @pytest.mark.asyncio
    async def test_generate_actions_below_threshold_returns_empty(self, automator):
        """评分低于阈值(80)时应返回空列表"""
        activity = {"score": 50, "title": "低分活动"}
        actions = await automator.generate_actions(activity)
        assert actions == []

    @pytest.mark.asyncio
    async def test_generate_actions_above_threshold_returns_actions(self, automator):
        """评分达到阈值(80)时应返回非空操作列表"""
        activity = {"score": 85, "title": "高分活动"}
        actions = await automator.generate_actions(activity)
        assert len(actions) > 0

    @pytest.mark.asyncio
    async def test_generate_actions_includes_reminder_when_deadline_present(self, automator):
        """活动包含 deadline 时应生成 SET_REMINDER 操作"""
        activity = {"score": 90, "title": "有截止日期的活动", "deadline": "2025-03-01"}
        actions = await automator.generate_actions(activity)
        action_types = [a["type"] for a in actions]
        assert ActionType.SET_REMINDER in action_types

    @pytest.mark.asyncio
    async def test_generate_actions_includes_register_when_url_present(self, automator):
        """活动包含 url 时应生成 REGISTER 操作"""
        activity = {"score": 90, "title": "有链接的活动", "url": "https://example.com/register"}
        actions = await automator.generate_actions(activity)
        action_types = [a["type"] for a in actions]
        assert ActionType.REGISTER in action_types

    @pytest.mark.asyncio
    async def test_generate_actions_always_includes_bookmark(self, automator):
        """高分活动应始终包含 BOOKMARK 操作"""
        activity = {"score": 80, "title": "基本高分活动"}
        actions = await automator.generate_actions(activity)
        action_types = [a["type"] for a in actions]
        assert ActionType.BOOKMARK in action_types


class TestExecuteAction:
    """execute_action 方法测试"""

    @pytest.mark.asyncio
    async def test_execute_action_persists_to_db(self, automator, pool):
        """执行操作后应持久化到数据库"""
        activity_id = "test-activity-001"
        result = await automator.execute_action(activity_id, ActionType.BOOKMARK)

        assert result["activity_id"] == activity_id
        assert result["action_type"] == ActionType.BOOKMARK
        assert result["status"] == "executed"

        # 验证数据库中确实存在该记录
        async with pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM action_recommendations WHERE activity_id = ?",
                (activity_id,),
            )
            rows = await cursor.fetchall()
            assert len(rows) == 1
            assert rows[0]["action_type"] == ActionType.BOOKMARK


class TestListActions:
    """list_actions 方法测试"""

    @pytest.mark.asyncio
    async def test_list_actions_returns_executed_actions(self, automator):
        """list_actions 应返回已执行的操作列表"""
        activity_id = "test-activity-002"

        # 执行多个操作
        await automator.execute_action(activity_id, ActionType.BOOKMARK)
        await automator.execute_action(activity_id, ActionType.REGISTER)

        actions = await automator.list_actions(activity_id)
        assert len(actions) == 2
        action_types = [a["action_type"] for a in actions]
        assert ActionType.BOOKMARK in action_types
        assert ActionType.REGISTER in action_types
