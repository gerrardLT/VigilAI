"""
数据库迁移管理器单元测试
Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
"""

import os
import uuid

import aiosqlite
import pytest
import pytest_asyncio

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema_manager import SchemaManager


@pytest.fixture
def temp_dir(tmp_path):
    """创建临时目录用于数据库和迁移文件"""
    return tmp_path


@pytest.fixture
def temp_db(temp_dir):
    """创建临时数据库路径"""
    return str(temp_dir / f"{uuid.uuid4().hex}.db")


@pytest.fixture
def migrations_dir(temp_dir):
    """创建临时迁移文件目录"""
    mdir = temp_dir / "migrations"
    mdir.mkdir()
    return str(mdir)


def write_migration(migrations_dir: str, filename: str, sql: str):
    """写入迁移 SQL 文件"""
    path = os.path.join(migrations_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(sql)


class TestApplyPendingCreatesTable:
    """apply_pending creates schema_migrations table."""

    @pytest.mark.asyncio
    async def test_creates_schema_migrations_table(self, temp_db, migrations_dir):
        """apply_pending 应创建 schema_migrations 表"""
        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        async with aiosqlite.connect(temp_db) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "schema_migrations"

    @pytest.mark.asyncio
    async def test_schema_migrations_has_correct_columns(self, temp_db, migrations_dir):
        """schema_migrations 表应包含 version, name, applied_at 列"""
        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        async with aiosqlite.connect(temp_db) as conn:
            cursor = await conn.execute("PRAGMA table_info(schema_migrations)")
            columns = {row[1] for row in await cursor.fetchall()}
            assert "version" in columns
            assert "name" in columns
            assert "applied_at" in columns


class TestApplyPendingAppliesMigrations:
    """apply_pending applies SQL migration files in order."""

    @pytest.mark.asyncio
    async def test_applies_single_migration(self, temp_db, migrations_dir):
        """应成功应用单个迁移文件"""
        write_migration(
            migrations_dir,
            "001_create_users.sql",
            "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT NOT NULL);",
        )

        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        async with aiosqlite.connect(temp_db) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            row = await cursor.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_applies_migrations_in_version_order(self, temp_db, migrations_dir):
        """应按版本号顺序应用迁移"""
        # Write in reverse order to ensure sorting works
        write_migration(
            migrations_dir,
            "002_create_posts.sql",
            "CREATE TABLE posts (id TEXT PRIMARY KEY, user_id TEXT);",
        )
        write_migration(
            migrations_dir,
            "001_create_users.sql",
            "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT NOT NULL);",
        )

        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        versions = await manager.get_applied_versions()
        assert versions == ["001", "002"]

    @pytest.mark.asyncio
    async def test_records_migration_in_schema_migrations(self, temp_db, migrations_dir):
        """应在 schema_migrations 表中记录已应用的迁移"""
        write_migration(
            migrations_dir,
            "001_init.sql",
            "CREATE TABLE items (id TEXT PRIMARY KEY);",
        )

        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        async with aiosqlite.connect(temp_db) as conn:
            cursor = await conn.execute(
                "SELECT version, name FROM schema_migrations WHERE version='001'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "001"
            assert row[1] == "001_init.sql"


class TestAlreadyAppliedSkipped:
    """Already-applied migrations are skipped."""

    @pytest.mark.asyncio
    async def test_skips_already_applied(self, temp_db, migrations_dir):
        """已应用的迁移不应重复执行"""
        write_migration(
            migrations_dir,
            "001_create_users.sql",
            "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT NOT NULL);",
        )

        manager = SchemaManager(temp_db, migrations_dir)

        # Apply once
        await manager.apply_pending()

        # Apply again - should not raise (table already exists would fail if re-run)
        await manager.apply_pending()

        versions = await manager.get_applied_versions()
        assert versions == ["001"]

    @pytest.mark.asyncio
    async def test_applies_only_new_migrations(self, temp_db, migrations_dir):
        """第二次运行只应用新增的迁移"""
        write_migration(
            migrations_dir,
            "001_create_users.sql",
            "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT NOT NULL);",
        )

        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        # Add a new migration
        write_migration(
            migrations_dir,
            "002_create_posts.sql",
            "CREATE TABLE posts (id TEXT PRIMARY KEY, title TEXT);",
        )

        await manager.apply_pending()

        versions = await manager.get_applied_versions()
        assert versions == ["001", "002"]

        # Verify both tables exist
        async with aiosqlite.connect(temp_db) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'posts') ORDER BY name"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            assert "posts" in tables
            assert "users" in tables


class TestFailedMigrationRaisesRuntimeError:
    """Failed migration raises RuntimeError."""

    @pytest.mark.asyncio
    async def test_invalid_sql_raises_runtime_error(self, temp_db, migrations_dir):
        """无效 SQL 应抛出 RuntimeError"""
        write_migration(
            migrations_dir,
            "001_bad.sql",
            "THIS IS NOT VALID SQL;",
        )

        manager = SchemaManager(temp_db, migrations_dir)

        with pytest.raises(RuntimeError) as exc_info:
            await manager.apply_pending()

        assert "001" in str(exc_info.value)
        assert "001_bad.sql" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_partial_failure_stops_at_bad_migration(self, temp_db, migrations_dir):
        """失败的迁移应阻止后续迁移执行"""
        write_migration(
            migrations_dir,
            "001_good.sql",
            "CREATE TABLE good_table (id TEXT PRIMARY KEY);",
        )
        write_migration(
            migrations_dir,
            "002_bad.sql",
            "INVALID SQL STATEMENT;",
        )
        write_migration(
            migrations_dir,
            "003_never.sql",
            "CREATE TABLE never_table (id TEXT PRIMARY KEY);",
        )

        manager = SchemaManager(temp_db, migrations_dir)

        with pytest.raises(RuntimeError):
            await manager.apply_pending()

        # 001 should have been applied, 003 should not
        versions = await manager.get_applied_versions()
        assert "001" in versions
        assert "003" not in versions


class TestGetAppliedVersions:
    """get_applied_versions returns correct list."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_migrations(self, temp_db, migrations_dir):
        """无迁移时应返回空列表"""
        manager = SchemaManager(temp_db, migrations_dir)
        versions = await manager.get_applied_versions()
        assert versions == []

    @pytest.mark.asyncio
    async def test_returns_applied_versions_in_order(self, temp_db, migrations_dir):
        """应按顺序返回已应用的版本号"""
        write_migration(
            migrations_dir,
            "001_first.sql",
            "CREATE TABLE t1 (id TEXT PRIMARY KEY);",
        )
        write_migration(
            migrations_dir,
            "002_second.sql",
            "CREATE TABLE t2 (id TEXT PRIMARY KEY);",
        )
        write_migration(
            migrations_dir,
            "003_third.sql",
            "CREATE TABLE t3 (id TEXT PRIMARY KEY);",
        )

        manager = SchemaManager(temp_db, migrations_dir)
        await manager.apply_pending()

        versions = await manager.get_applied_versions()
        assert versions == ["001", "002", "003"]

    @pytest.mark.asyncio
    async def test_returns_empty_when_table_does_not_exist(self, temp_db, migrations_dir):
        """schema_migrations 表不存在时应返回空列表"""
        manager = SchemaManager(temp_db, migrations_dir)
        # Don't call apply_pending - table doesn't exist
        versions = await manager.get_applied_versions()
        assert versions == []
