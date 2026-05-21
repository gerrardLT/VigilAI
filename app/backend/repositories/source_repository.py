"""Async CRUD repository for the sources table.

Provides parameterized queries and async access via SQLitePool.
Validates requirements 7.2, 7.4, 11.1.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from db.connection_pool import SQLitePool

logger = logging.getLogger(__name__)


class SourceRepository:
    """Async repository for the sources table.

    All database access goes through the connection pool using
    ``async with self.pool.acquire() as conn``.
    """

    def __init__(self, pool: SQLitePool) -> None:
        self.pool = pool

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_all(self) -> list[dict]:
        """List all sources ordered by priority then name.

        Returns:
            List of source dicts.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM sources
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END,
                    name ASC
                """
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_by_id(self, source_id: str) -> dict | None:
        """Fetch a single source by its ID.

        Args:
            source_id: The source ID to look up.

        Returns:
            A dict representation of the row, or None if not found.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert(self, source: dict) -> dict:
        """Insert or replace a source record.

        Uses INSERT OR REPLACE so that an existing row with the same id
        is fully replaced. All columns are written.

        Args:
            source: Dict with source fields. Required: id, name, type, url,
                priority, update_interval.

        Returns:
            The upserted source as a dict (re-read from DB).
        """
        source_id = source["id"]

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO sources (
                    id, name, type, url, priority, update_interval,
                    enabled, last_run, last_success, status,
                    error_message, activity_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    source["name"],
                    source["type"],
                    source["url"],
                    source["priority"],
                    source["update_interval"],
                    source.get("enabled", 1),
                    source.get("last_run"),
                    source.get("last_success"),
                    source.get("status", "idle"),
                    source.get("error_message"),
                    source.get("activity_count", 0),
                ),
            )
            await conn.commit()

            # Re-read to return the persisted state
            cursor = await conn.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def update_status(
        self,
        source_id: str,
        status: str,
        *,
        activity_count: int | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Update the status of a source, optionally setting activity_count and error_message.

        When status indicates a successful run, last_run and last_success are
        automatically updated. When status is any other value, only last_run
        is updated.

        Args:
            source_id: The source ID to update.
            status: New status value (e.g. 'idle', 'running', 'error', 'success').
            activity_count: If provided, update the activity_count column.
            error_message: If provided, update the error_message column.

        Returns:
            True if a row was updated, False if the source_id was not found.
        """
        now = datetime.now().isoformat()

        assignments: list[str] = ["status = ?", "last_run = ?"]
        params: list[Any] = [status, now]

        # Mark last_success when status indicates completion
        if status == "success":
            assignments.append("last_success = ?")
            params.append(now)

        if activity_count is not None:
            assignments.append("activity_count = ?")
            params.append(activity_count)

        if error_message is not None:
            assignments.append("error_message = ?")
            params.append(error_message)
        elif status == "success":
            # Clear error on success
            assignments.append("error_message = NULL")

        sql = f"UPDATE sources SET {', '.join(assignments)} WHERE id = ?"
        params.append(source_id)

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.rowcount > 0
