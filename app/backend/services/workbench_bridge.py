"""Agent-to-Workbench bridge service.

Creates structured records from Agent conversation insights with provenance
linking and deduplication checking.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime

from db.connection_pool import SQLitePool


class WorkbenchBridge:
    """Bridge between Agent conversations and the structured Workbench.

    Converts unstructured Agent insights into structured records (activities
    or selection opportunities) with provenance linking back to the originating
    session and turn. Performs deduplication by URL before creating new records.
    """

    def __init__(self, pool: SQLitePool):
        """Initialize the bridge with a database connection pool.

        Args:
            pool: SQLitePool instance for database access.
        """
        self.pool = pool

    async def save_to_workbench(
        self, *, session_id: str, turn_id: str, payload: dict
    ) -> dict:
        """Create a structured record from an Agent conversation insight.

        Args:
            session_id: The agent session that produced this insight.
            turn_id: The specific turn that identified the opportunity.
            payload: Dict with keys:
                - domain: "opportunity" or "product_selection"
                - title: str
                - url: str (used as dedupe key)
                - description: str (optional)
                - category: str (optional)
                - source_name: str (optional)

        Returns:
            Dict with status ("created" or "duplicate"), id, domain,
            and optional existing_id.
        """
        domain = payload.get("domain", "opportunity")
        url = payload.get("url", "")

        # Check for duplicates by URL
        existing = await self._find_existing(domain, url)
        if existing:
            return {"status": "duplicate", "existing_id": existing, "domain": domain}

        # Create the record
        record_id = self._generate_id(session_id, url)
        now = datetime.now().isoformat()

        if domain == "opportunity":
            await self._create_opportunity(record_id, payload, session_id, turn_id, now)
        else:
            await self._create_selection_opportunity(
                record_id, payload, session_id, turn_id, now
            )

        return {"status": "created", "id": record_id, "domain": domain}

    async def _find_existing(self, domain: str, url: str) -> str | None:
        """Check if a record with the given URL already exists.

        Args:
            domain: The domain to search in ("opportunity" or "product_selection").
            url: The URL to check for duplicates.

        Returns:
            The existing record ID if found, None otherwise.
        """
        if not url:
            return None
        async with self.pool.acquire() as conn:
            if domain == "opportunity":
                cursor = await conn.execute(
                    "SELECT id FROM activities WHERE url = ?", (url,)
                )
            else:
                cursor = await conn.execute(
                    "SELECT id FROM selection_opportunities WHERE source_urls LIKE ?",
                    (f"%{url}%",),
                )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def _create_opportunity(
        self, record_id: str, payload: dict, session_id: str, turn_id: str, now: str
    ) -> None:
        """Create an opportunity record in the activities table.

        Args:
            record_id: Unique ID for the new record.
            payload: Data payload with title, description, url, etc.
            session_id: Originating agent session ID.
            turn_id: Originating agent turn ID.
            now: ISO-formatted timestamp for created_at/updated_at.
        """
        source_id = f"agent:{session_id}"
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO activities
                   (id, title, description, source_id, source_name, url,
                    category, tags, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    payload.get("title", ""),
                    payload.get("description", ""),
                    source_id,
                    payload.get("source_name", "Agent"),
                    payload.get("url", ""),
                    payload.get("category", "other_competition"),
                    f'["agent_bridge","{turn_id}"]',
                    "upcoming",
                    now,
                    now,
                ),
            )
            await conn.commit()

    async def _create_selection_opportunity(
        self, record_id: str, payload: dict, session_id: str, turn_id: str, now: str
    ) -> None:
        """Create a selection opportunity record.

        Args:
            record_id: Unique ID for the new record.
            payload: Data payload with title, url, etc.
            session_id: Originating agent session ID.
            turn_id: Originating agent turn ID.
            now: ISO-formatted timestamp for created_at/updated_at.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO selection_opportunities
                   (id, query_id, platform, platform_item_id, title,
                    source_urls, source_mode, snapshot_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    f"agent:{session_id}",
                    "agent",
                    turn_id,
                    payload.get("title", ""),
                    f'["{payload.get("url", "")}"]',
                    "agent_bridge",
                    now,
                    now,
                    now,
                ),
            )
            await conn.commit()

    @staticmethod
    def _generate_id(session_id: str, url: str) -> str:
        """Generate a unique record ID using session, URL, and random bytes.

        Args:
            session_id: The agent session ID.
            url: The opportunity URL.

        Returns:
            A 32-character hex string ID.
        """
        return hashlib.md5(
            f"bridge:{session_id}:{url}:{os.urandom(4).hex()}".encode()
        ).hexdigest()
