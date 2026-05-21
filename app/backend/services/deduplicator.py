"""Cross-domain deduplication service.

Detects duplicate opportunities across different domains (activities, reward_opportunities)
using URL matching, title similarity, and temporal windowing.

Validates: Requirements 19.1, 19.3
"""
from __future__ import annotations

from datetime import datetime, timedelta
from difflib import SequenceMatcher

from db.connection_pool import SQLitePool


class CrossDomainDeduplicator:
    """Deduplicates opportunities across activity and reward domains.

    Detection strategies:
    1. Exact URL match across activities and reward_opportunities tables
    2. Title similarity > 0.85 (SequenceMatcher ratio) within a 7-day temporal window

    Attributes:
        TITLE_SIMILARITY_THRESHOLD: Minimum similarity ratio to consider titles as duplicates.
        TEMPORAL_WINDOW_DAYS: Number of days to look back for candidate matches.
    """

    TITLE_SIMILARITY_THRESHOLD = 0.85
    TEMPORAL_WINDOW_DAYS = 7

    def __init__(self, pool: SQLitePool):
        """Initialize the deduplicator with a database connection pool.

        Args:
            pool: SQLitePool instance for database access.
        """
        self.pool = pool

    async def check_duplicate(self, opportunity: dict) -> dict | None:
        """Check if an opportunity already exists in other domains.

        Performs two checks in order:
        1. Exact URL match across activities and reward_opportunities
        2. Title similarity > 0.85 within a 7-day temporal window

        Args:
            opportunity: Dict with at least 'url' and/or 'title' keys.

        Returns:
            Matching record dict with keys (id, title, url, domain) or None if no duplicate found.
        """
        url = opportunity.get("url", "")
        title = opportunity.get("title", "")

        # 1. Exact URL match
        if url:
            url_match = await self._find_by_url(url)
            if url_match:
                return url_match

        # 2. Title similarity within temporal window
        if title:
            candidates = await self._find_recent_candidates()
            for candidate in candidates:
                similarity = SequenceMatcher(
                    None, title.lower(), candidate["title"].lower()
                ).ratio()
                if similarity >= self.TITLE_SIMILARITY_THRESHOLD:
                    return candidate

        return None

    async def mark_duplicate(
        self,
        source_domain: str,
        source_id: str,
        target_domain: str,
        target_id: str,
        similarity_score: float,
        match_type: str,
    ) -> dict:
        """Mark an item as duplicate in the duplicate_links table.

        Args:
            source_domain: Domain of the source item (e.g. 'opportunity', 'reward').
            source_id: ID of the source item.
            target_domain: Domain of the target (existing) item.
            target_id: ID of the target item.
            similarity_score: Similarity score between 0 and 1.
            match_type: Type of match ('url' or 'title').

        Returns:
            Dict with link metadata (id, source_id, target_id, match_type).
        """
        import hashlib
        import os

        link_id = hashlib.md5(
            f"{source_id}:{target_id}:{os.urandom(4).hex()}".encode()
        ).hexdigest()
        now = datetime.now().isoformat()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO duplicate_links
                   (id, source_domain, source_id, target_domain, target_id,
                    similarity_score, match_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    link_id,
                    source_domain,
                    source_id,
                    target_domain,
                    target_id,
                    similarity_score,
                    match_type,
                    now,
                ),
            )
            await conn.commit()

        return {
            "id": link_id,
            "source_id": source_id,
            "target_id": target_id,
            "match_type": match_type,
        }

    async def list_duplicates(self) -> list[dict]:
        """List all active (non-overridden) duplicate links.

        Returns:
            List of duplicate link dicts ordered by creation date descending.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM duplicate_links WHERE overridden = 0 ORDER BY created_at DESC"
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def override_duplicate(self, link_id: str) -> bool:
        """Mark a duplicate link as overridden (user confirms it's not a duplicate).

        Args:
            link_id: ID of the duplicate link to override.

        Returns:
            True if the link was found and updated, False otherwise.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "UPDATE duplicate_links SET overridden = 1 WHERE id = ?", (link_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def _find_by_url(self, url: str) -> dict | None:
        """Find an existing record by exact URL match.

        Searches both activities and reward_opportunities tables.

        Args:
            url: The URL to search for.

        Returns:
            Dict with (id, title, url, domain) or None.
        """
        async with self.pool.acquire() as conn:
            # Check activities
            cursor = await conn.execute(
                "SELECT id, title, url, 'opportunity' as domain FROM activities WHERE url = ?",
                (url,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)

            # Check reward_opportunities
            cursor = await conn.execute(
                "SELECT id, title, source_url as url, 'reward' as domain "
                "FROM reward_opportunities WHERE source_url = ?",
                (url,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)

            return None

    async def _find_recent_candidates(self) -> list[dict]:
        """Find all records created within the temporal window.

        Queries both activities and reward_opportunities for items
        created in the last TEMPORAL_WINDOW_DAYS days.

        Returns:
            List of candidate dicts with (id, title, url, domain).
        """
        cutoff = (
            datetime.now() - timedelta(days=self.TEMPORAL_WINDOW_DAYS)
        ).isoformat()

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT id, title, url, 'opportunity' as domain FROM activities "
                "WHERE created_at >= ? "
                "UNION ALL "
                "SELECT id, title, source_url as url, 'reward' as domain "
                "FROM reward_opportunities WHERE created_at >= ?",
                (cutoff, cutoff),
            )
            return [dict(row) for row in await cursor.fetchall()]
