"""
SQLite 连接池单元测试
Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

import asyncio
import os
import uuid

import pytest
import pytest_asyncio

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection_pool import SQLitePool


@pytest.fixture
def temp_db():
    """创建临时数据库路径"""
    temp_root = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(temp_root, exist_ok=True)
    db_path = os.path.join(temp_root, f"{uuid.uuid4().hex}.db")
    try:
        yield db_path
    finally:
        # Clean up db file and WAL/SHM files
        for suffix in ("", "-wal", "-shm"):
            path = db_path + suffix
            if os.path.exists(path):
                os.remove(path)


@pytest_asyncio.fixture
async def pool(temp_db):
    """创建并初始化连接池"""
    p = SQLitePool(temp_db, max_size=3)
    await p.initialize()
    yield p
    await p.close_all()


class TestPoolCreatesConnections:
    """Pool creates connections up to max_size."""

    @pytest.mark.asyncio
    async def test_creates_connections_up_to_max_size(self, temp_db):
        """连接池应创建不超过 max_size 个连接"""
        pool = SQLitePool(temp_db, max_size=3)
        connections = []
        try:
            for _ in range(3):
                conn = await pool._get_connection()
                connections.append(conn)

            assert pool._size == 3
        finally:
            for conn in connections:
                await pool._return_connection(conn)
            await pool.close_all()

    @pytest.mark.asyncio
    async def test_size_does_not_exceed_max(self, temp_db):
        """连接数不应超过 max_size"""
        pool = SQLitePool(temp_db, max_size=2)
        connections = []
        try:
            for _ in range(2):
                conn = await pool._get_connection()
                connections.append(conn)

            assert pool._size == 2

            # Next request should block (timeout quickly for test)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(pool._get_connection(), timeout=0.1)
        finally:
            for conn in connections:
                await pool._return_connection(conn)
            await pool.close_all()


class TestPoolReusesConnections:
    """Pool reuses returned connections."""

    @pytest.mark.asyncio
    async def test_returned_connection_is_reused(self, pool):
        """归还的连接应被复用"""
        # Acquire and return a connection
        async with pool.acquire() as conn1:
            conn1_id = id(conn1)

        # Acquire again - should get the same connection back
        async with pool.acquire() as conn2:
            conn2_id = id(conn2)

        assert conn1_id == conn2_id

    @pytest.mark.asyncio
    async def test_pool_size_stays_stable_on_reuse(self, pool):
        """复用连接时 _size 不应增长"""
        for _ in range(5):
            async with pool.acquire() as _:
                pass

        # Only 1 connection should have been created
        assert pool._size == 1


class TestPoolWaitsWhenFull:
    """Pool waits when full (timeout behavior)."""

    @pytest.mark.asyncio
    async def test_timeout_when_pool_exhausted(self, temp_db):
        """连接池耗尽时应超时"""
        pool = SQLitePool(temp_db, max_size=1)
        conn = await pool._get_connection()
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(pool._get_connection(), timeout=0.1)
        finally:
            await pool._return_connection(conn)
            await pool.close_all()

    @pytest.mark.asyncio
    async def test_waits_and_succeeds_when_connection_returned(self, temp_db):
        """连接归还后等待者应获得连接"""
        pool = SQLitePool(temp_db, max_size=1)
        conn = await pool._get_connection()

        async def return_later():
            await asyncio.sleep(0.05)
            await pool._return_connection(conn)

        asyncio.create_task(return_later())

        # Should succeed within timeout
        conn2 = await asyncio.wait_for(pool._get_connection(), timeout=1.0)
        assert conn2 is not None
        await pool._return_connection(conn2)
        await pool.close_all()


class TestWALModeEnabled:
    """WAL mode is enabled after initialize()."""

    @pytest.mark.asyncio
    async def test_wal_mode_set(self, pool):
        """initialize() 后应启用 WAL 模式"""
        async with pool.acquire() as conn:
            cursor = await conn.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0].lower() == "wal"


class TestPragmasSet:
    """busy_timeout and synchronous pragmas are set."""

    @pytest.mark.asyncio
    async def test_busy_timeout_set(self, pool):
        """busy_timeout 应设置为 5000"""
        async with pool.acquire() as conn:
            cursor = await conn.execute("PRAGMA busy_timeout")
            row = await cursor.fetchone()
            assert row[0] == 5000

    @pytest.mark.asyncio
    async def test_synchronous_normal(self, pool):
        """synchronous 应设置为 NORMAL (1)"""
        async with pool.acquire() as conn:
            cursor = await conn.execute("PRAGMA synchronous")
            row = await cursor.fetchone()
            # NORMAL = 1
            assert row[0] == 1


class TestCloseAll:
    """close_all() closes all connections."""

    @pytest.mark.asyncio
    async def test_close_all_empties_pool(self, temp_db):
        """close_all() 应关闭所有连接并重置状态"""
        pool = SQLitePool(temp_db, max_size=3)

        # Create multiple connections and return them
        conns = []
        for _ in range(3):
            conn = await pool._get_connection()
            conns.append(conn)
        for conn in conns:
            await pool._return_connection(conn)

        assert pool._size == 3
        assert not pool._pool.empty()

        await pool.close_all()

        assert pool._size == 0
        assert pool._pool.empty()
