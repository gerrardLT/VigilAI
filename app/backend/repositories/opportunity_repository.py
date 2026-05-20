"""Async CRUD repository for the activities table.

Provides SQL-level filtering, pagination, and parameterized queries
using the SQLitePool connection manager.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from db.connection_pool import SQLitePool

logger = logging.getLogger(__name__)


class OpportunityRepository:
    """Async repository for activities (opportunities) table.

    All database access goes through the connection pool using
    ``async with self.pool.acquire() as conn``.
    """

    def __init__(self, pool: SQLitePool) -> None:
        self.pool = pool

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, activity_id: str) -> dict | None:
        """Fetch a single activity by its ID.

        Returns:
            A dict representation of the row, or None if not found.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM activities WHERE id = ?", (activity_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_activities(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: dict | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], int]:
        """List activities with SQL-level filtering, sorting, and pagination.

        Args:
            page: 1-based page number.
            page_size: Number of items per page.
            filters: Dict of filter criteria. Supported keys:
                - category: exact match on category column
                - source_id: exact match on source_id column
                - status: exact match on status column
                - search: LIKE match on title, description, or summary
                - analysis_status: exact match on analysis_status column
                - deadline_level: exact match on deadline_level column
                - trust_level: exact match on trust_level column
                - is_tracking: boolean filter via tracking_items join
                - is_favorited: boolean filter via tracking_items join
            sort_by: Column to sort by.
            sort_order: 'asc' or 'desc'.

        Returns:
            Tuple of (list of activity dicts for the page, total count).
        """
        filters = filters or {}
        conditions: list[str] = []
        params: list[Any] = []

        # Build WHERE clauses from filters
        self._build_where_clauses(conditions, params, filters)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sort_expression = self._resolve_sort_expression(sort_by)
        direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        base_from = self._build_base_from(filters)

        # Count query
        count_sql = f"SELECT COUNT(*) AS total {base_from} WHERE {where_clause}"

        # Data query with pagination
        offset = max(0, (page - 1) * page_size)
        data_sql = (
            f"SELECT a.* {base_from} "
            f"WHERE {where_clause} "
            f"ORDER BY {sort_expression} {direction}, a.created_at DESC "
            f"LIMIT ? OFFSET ?"
        )
        data_params = params + [page_size, offset]

        async with self.pool.acquire() as conn:
            # Get total count
            cursor = await conn.execute(count_sql, params)
            count_row = await cursor.fetchone()
            total = count_row[0] if count_row else 0

            # Get page data
            cursor = await conn.execute(data_sql, data_params)
            rows = await cursor.fetchall()
            activities = [dict(row) for row in rows]

        return activities, total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, activity: dict) -> bool:
        """Insert a new activity using INSERT OR IGNORE.

        Returns:
            True if a row was inserted, False if it already existed.
        """
        columns = [
            "id", "title", "description", "full_content",
            "source_id", "source_name", "url", "category", "tags",
            "prize_amount", "prize_currency", "prize_description",
            "start_date", "end_date", "deadline",
            "location", "organizer", "image_url",
            "summary", "score", "score_reason",
            "deadline_level", "trust_level", "updated_fields",
            "analysis_fields", "analysis_status",
            "analysis_failed_layer", "analysis_summary_reasons",
            "status", "created_at", "updated_at",
        ]

        # Ensure JSON fields are serialized
        activity = self._serialize_json_fields(activity)

        now = datetime.now().isoformat()
        if "created_at" not in activity or not activity["created_at"]:
            activity["created_at"] = now
        if "updated_at" not in activity or not activity["updated_at"]:
            activity["updated_at"] = now

        # Only include columns that exist in the activity dict
        present_columns = [col for col in columns if col in activity]
        placeholders = ", ".join("?" for _ in present_columns)
        col_names = ", ".join(present_columns)
        values = [activity[col] for col in present_columns]

        sql = f"INSERT OR IGNORE INTO activities ({col_names}) VALUES ({placeholders})"

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(sql, values)
            await conn.commit()
            return cursor.rowcount > 0

    async def update(self, activity_id: str, fields: dict) -> bool:
        """Update specific fields of an activity.

        Args:
            activity_id: The activity ID to update.
            fields: Dict of column_name -> new_value pairs.

        Returns:
            True if a row was updated, False otherwise.
        """
        if not fields:
            return False

        # Serialize JSON fields if present
        fields = self._serialize_json_fields(fields)

        # Always update updated_at
        if "updated_at" not in fields:
            fields["updated_at"] = datetime.now().isoformat()

        set_clauses = [f"{col} = ?" for col in fields]
        values = list(fields.values()) + [activity_id]

        sql = f"UPDATE activities SET {', '.join(set_clauses)} WHERE id = ?"

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(sql, values)
            await conn.commit()
            return cursor.rowcount > 0

    async def delete(self, activity_id: str) -> bool:
        """Delete an activity by ID.

        Returns:
            True if a row was deleted, False otherwise.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "DELETE FROM activities WHERE id = ?", (activity_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    async def count(self, filters: dict | None = None) -> int:
        """Count activities matching the given filters.

        Args:
            filters: Optional filter dict (same keys as list_activities).

        Returns:
            Total number of matching activities.
        """
        filters = filters or {}
        conditions: list[str] = []
        params: list[Any] = []

        self._build_where_clauses(conditions, params, filters)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        base_from = self._build_base_from(filters)

        sql = f"SELECT COUNT(*) AS total {base_from} WHERE {where_clause}"

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(sql, params)
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_base_from(self, filters: dict) -> str:
        """Build the FROM clause, joining tracking_items when needed."""
        needs_tracking_join = any(
            key in filters for key in ("is_tracking", "is_favorited")
        )
        if needs_tracking_join:
            return (
                "FROM activities a "
                "LEFT JOIN tracking_items t ON t.activity_id = a.id"
            )
        return "FROM activities a"

    def _build_where_clauses(
        self,
        conditions: list[str],
        params: list[Any],
        filters: dict,
    ) -> None:
        """Append SQL WHERE conditions and params based on filter dict."""
        if filters.get("category"):
            conditions.append("a.category = ?")
            params.append(filters["category"])
        else:
            # Exclude news by default (matches existing behavior)
            conditions.append("a.category != ?")
            params.append("news")

        if filters.get("source_id"):
            conditions.append("a.source_id = ?")
            params.append(filters["source_id"])

        if filters.get("status"):
            conditions.append("a.status = ?")
            params.append(filters["status"])

        if filters.get("search"):
            conditions.append(
                "(a.title LIKE ? OR a.description LIKE ? OR a.summary LIKE ?)"
            )
            term = f"%{filters['search']}%"
            params.extend([term, term, term])

        if filters.get("analysis_status"):
            conditions.append("a.analysis_status = ?")
            params.append(filters["analysis_status"])

        if filters.get("deadline_level"):
            conditions.append("a.deadline_level = ?")
            params.append(filters["deadline_level"])

        if filters.get("trust_level"):
            conditions.append("a.trust_level = ?")
            params.append(filters["trust_level"])

        # Tracking-based filters (require JOIN)
        if "is_tracking" in filters and filters["is_tracking"] not in (None, "", "all"):
            is_tracking = str(filters["is_tracking"]).lower() in {"1", "true", "yes"}
            if is_tracking:
                conditions.append("t.activity_id IS NOT NULL")
            else:
                conditions.append("t.activity_id IS NULL")

        if "is_favorited" in filters and filters["is_favorited"] not in (None, "", "all"):
            is_favorited = str(filters["is_favorited"]).lower() in {"1", "true", "yes"}
            conditions.append("COALESCE(t.is_favorited, 0) = ?")
            params.append(1 if is_favorited else 0)

    def _resolve_sort_expression(self, sort_by: str) -> str:
        """Map sort_by parameter to a SQL expression."""
        order_map = {
            "created_at": "a.created_at",
            "updated_at": "a.updated_at",
            "deadline": "a.deadline",
            "prize_amount": "a.prize_amount",
            "prize": "a.prize_amount",
            "title": "a.title",
            "score": "COALESCE(a.score, 0)",
            "trust_level": (
                "CASE a.trust_level "
                "WHEN 'high' THEN 3 "
                "WHEN 'medium' THEN 2 "
                "WHEN 'low' THEN 1 "
                "ELSE 0 END"
            ),
        }
        return order_map.get(sort_by, "a.created_at")

    @staticmethod
    def _serialize_json_fields(data: dict) -> dict:
        """Ensure JSON-typed fields are serialized to strings for storage."""
        json_fields = (
            "tags", "updated_fields", "analysis_fields",
            "analysis_summary_reasons",
        )
        result = dict(data)
        for field in json_fields:
            if field in result and not isinstance(result[field], str):
                result[field] = json.dumps(result[field])
        return result
