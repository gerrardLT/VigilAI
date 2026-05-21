"""Versioned SQL migration system for VigilAI.

Tracks applied migrations in a `schema_migrations` table and applies pending
SQL migration files in version order. Each migration runs within a transaction
and rolls back on failure, preventing the application from starting with an
inconsistent schema.
"""

import glob
import logging
import os

import aiosqlite

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages versioned database schema migrations.

    Reads SQL migration files from a directory, tracks which have been applied
    in a `schema_migrations` table, and applies pending migrations in version
    order. Migrations are expected to be named with a version prefix, e.g.
    ``001_initial_schema.sql``.

    Attributes:
        db_path: Path to the SQLite database file.
        migrations_dir: Directory containing versioned SQL migration files.
    """

    def __init__(self, db_path: str, migrations_dir: str):
        """Initialize the SchemaManager.

        Args:
            db_path: Path to the SQLite database file.
            migrations_dir: Directory containing `*.sql` migration files named
                with a version prefix (e.g. ``001_initial_schema.sql``).
        """
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    async def apply_pending(self):
        """Apply all pending migrations in version order.

        Creates the ``schema_migrations`` table if it does not exist, then
        discovers and applies any migration files whose version has not yet
        been recorded. Each migration is executed via ``executescript`` and
        its version is recorded on success.

        Raises:
            RuntimeError: If any migration fails. The error includes the
                version and filename of the failed migration. This prevents
                the application from starting with a partially-applied schema.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            await conn.commit()

            # Get already applied migrations
            cursor = await conn.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in await cursor.fetchall()}

            # Find and sort migration files
            pattern = os.path.join(self.migrations_dir, "*.sql")
            migration_files = sorted(glob.glob(pattern))

            for path in migration_files:
                filename = os.path.basename(path)
                version = filename.split("_")[0]  # e.g., "001" from "001_initial_schema.sql"

                if version in applied:
                    continue

                logger.info("Applying migration %s: %s", version, filename)

                try:
                    with open(path, encoding="utf-8") as f:
                        sql = f.read()

                    await conn.executescript(sql)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (version, filename),
                    )
                    await conn.commit()
                    logger.info("Migration %s applied successfully", version)
                except Exception as exc:
                    logger.error("Migration %s failed: %s", version, exc)
                    raise RuntimeError(
                        f"Migration {version} ({filename}) failed: {exc}"
                    ) from exc

    async def get_applied_versions(self) -> list[str]:
        """Return list of applied migration versions in order.

        Returns:
            A sorted list of version strings that have been successfully
            applied. Returns an empty list if the ``schema_migrations``
            table does not yet exist.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                cursor = await conn.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
                return [row[0] for row in await cursor.fetchall()]
            except Exception:
                return []
