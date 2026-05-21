"""Async CRUD repository for the digests and digest_candidates tables.

Provides parameterized queries and async access via SQLitePool.
Validates requirements 7.2, 7.4, 11.1.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any

from db.connection_pool import SQLitePool

logger = logging.getLogger(__name__)


class DigestRepository:
    """Async repository for digests and digest_candidates tables.

    All database access goes through the connection pool using
    ``async with self.pool.acquire() as conn``.
    """

    def __init__(self, pool: SQLitePool) -> None:
        self.pool = pool

    # ======================================================================
    # digests — Read
    # ======================================================================

    async def list_digests(self) -> list[dict]:
        """List all digests ordered by digest_date descending.

        Returns:
            List of digest dicts.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM digests ORDER BY digest_date DESC"
            )
            rows = await cursor.fetchall()
            return [self._digest_row_to_dict(row) for row in rows]

    async def get_by_id(self, digest_id: str) -> dict | None:
        """Fetch a single digest by its ID.

        Returns:
            A dict representation of the row, or None if not found.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM digests WHERE id = ?", (digest_id,)
            )
            row = await cursor.fetchone()
            return self._digest_row_to_dict(row) if row else None

    # ======================================================================
    # digests — Write
    # ======================================================================

    async def create(self, digest: dict) -> dict:
        """Insert a new digest.

        Args:
            digest: Dict with digest fields. Required: digest_date, title, content, item_ids.
                item_ids will be JSON-serialized if passed as a list.

        Returns:
            The inserted digest as a dict.
        """
        now = datetime.now().isoformat()
        digest_id = digest.get("id") or self._generate_id()

        # Serialize item_ids if it's a list
        item_ids = digest.get("item_ids", [])
        if not isinstance(item_ids, str):
            item_ids = json.dumps(item_ids)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO digests (
                    id, digest_date, title, summary, content, item_ids,
                    status, created_at, updated_at, last_sent_at, send_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    digest_id,
                    digest["digest_date"],
                    digest["title"],
                    digest.get("summary"),
                    digest["content"],
                    item_ids,
                    digest.get("status", "draft"),
                    now,
                    now,
                    digest.get("last_sent_at"),
                    digest.get("send_channel"),
                ),
            )
            await conn.commit()

            cursor = await conn.execute(
                "SELECT * FROM digests WHERE id = ?", (digest_id,)
            )
            row = await cursor.fetchone()
            return self._digest_row_to_dict(row)

    async def update_status(
        self, digest_id: str, status: str, **fields: Any
    ) -> dict | None:
        """Update the status of a digest, optionally setting additional fields.

        Automatically updates updated_at. Sets last_sent_at when status is 'sent'.

        Args:
            digest_id: The digest ID to update.
            status: New status value (e.g. 'draft', 'sent', 'archived').
            **fields: Additional fields to update (e.g. send_channel, summary).

        Returns:
            The updated digest dict, or None if not found.
        """
        assignments = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status, datetime.now().isoformat()]

        # Auto-set last_sent_at when marking as sent
        if status == "sent" and "last_sent_at" not in fields:
            assignments.append("last_sent_at = ?")
            params.append(datetime.now().isoformat())

        # Handle extra fields
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            if key == "item_ids" and not isinstance(value, str):
                params.append(json.dumps(value))
            else:
                params.append(value)

        params.append(digest_id)

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                f"UPDATE digests SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return None

            cursor = await conn.execute(
                "SELECT * FROM digests WHERE id = ?", (digest_id,)
            )
            row = await cursor.fetchone()
            return self._digest_row_to_dict(row) if row else None

    # ======================================================================
    # digest_candidates — Read
    # ======================================================================

    async def list_candidates(self, digest_date: str | None = None) -> list[dict]:
        """List digest candidates, optionally filtered by digest_date.

        Args:
            digest_date: If provided, only return candidates for this date.

        Returns:
            List of candidate dicts.
        """
        async with self.pool.acquire() as conn:
            if digest_date:
                cursor = await conn.execute(
                    """
                    SELECT * FROM digest_candidates
                    WHERE digest_date = ?
                    ORDER BY created_at DESC
                    """,
                    (digest_date,),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM digest_candidates ORDER BY digest_date DESC, created_at DESC"
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ======================================================================
    # digest_candidates — Write
    # ======================================================================

    async def add_candidate(self, activity_id: str, digest_date: str) -> bool:
        """Add an activity as a digest candidate for a given date.

        Uses INSERT OR IGNORE to handle duplicates gracefully.

        Args:
            activity_id: The activity ID to add as a candidate.
            digest_date: The target digest date.

        Returns:
            True if the candidate was inserted, False if it already existed.
        """
        now = datetime.now().isoformat()

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                """
                INSERT OR IGNORE INTO digest_candidates (digest_date, activity_id, created_at)
                VALUES (?, ?, ?)
                """,
                (digest_date, activity_id, now),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def remove_candidate(self, activity_id: str, digest_date: str) -> bool:
        """Remove an activity from digest candidates for a given date.

        Args:
            activity_id: The activity ID to remove.
            digest_date: The target digest date.

        Returns:
            True if a row was deleted, False if it didn't exist.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                """
                DELETE FROM digest_candidates
                WHERE digest_date = ? AND activity_id = ?
                """,
                (digest_date, activity_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    # ======================================================================
    # Private helpers
    # ======================================================================

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique record ID using timestamp + random bytes."""
        return hashlib.md5(
            f"{datetime.now().isoformat()}:{os.urandom(8).hex()}".encode()
        ).hexdigest()

    @staticmethod
    def _digest_row_to_dict(row) -> dict:
        """Convert a digests row to a dict with item_ids parsed as JSON."""
        return {
            "id": row["id"],
            "digest_date": row["digest_date"],
            "title": row["title"],
            "summary": row["summary"],
            "content": row["content"],
            "item_ids": json.loads(row["item_ids"]) if row["item_ids"] else [],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_sent_at": row["last_sent_at"],
            "send_channel": row["send_channel"],
        }
