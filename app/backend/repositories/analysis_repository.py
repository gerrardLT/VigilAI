"""Async CRUD repository for analysis_templates, analysis_jobs, and analysis_job_items tables.

Provides parameterized queries and async access via SQLitePool.
Validates requirements 7.2, 7.4, 11.1.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from db.connection_pool import SQLitePool

logger = logging.getLogger(__name__)


class AnalysisRepository:
    """Async repository for analysis-related tables.

    All database access goes through the connection pool using
    ``async with self.pool.acquire() as conn``.
    """

    def __init__(self, pool: SQLitePool) -> None:
        self.pool = pool

    # ======================================================================
    # analysis_templates
    # ======================================================================

    async def get_template_by_id(self, template_id: str) -> dict | None:
        """Fetch a single analysis template by its ID.

        Returns:
            A dict representation of the row, or None if not found.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM analysis_templates WHERE id = ?", (template_id,)
            )
            row = await cursor.fetchone()
            return self._template_row_to_dict(row) if row else None

    async def get_default_template(self) -> dict | None:
        """Fetch the default analysis template.

        Returns the template with is_default=1, or the earliest created
        template if none is marked as default. Returns None if no templates exist.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM analysis_templates
                ORDER BY is_default DESC, created_at ASC
                LIMIT 1
                """
            )
            row = await cursor.fetchone()
            return self._template_row_to_dict(row) if row else None

    async def list_templates(self) -> list[dict]:
        """List all analysis templates ordered by default status then creation date.

        Returns:
            List of template dicts.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM analysis_templates ORDER BY is_default DESC, created_at ASC"
            )
            rows = await cursor.fetchall()
            return [self._template_row_to_dict(row) for row in rows]

    async def create_template(self, template: dict) -> dict:
        """Insert a new analysis template.

        Args:
            template: Dict with template fields. Required: name, slug.
                JSON fields (tags, layers, sort_fields, compiled_policy) will be
                serialized automatically.

        Returns:
            The inserted template as a dict.
        """
        now = datetime.now().isoformat()
        template_id = template.get("id") or self._generate_id()

        # If marking as default, clear existing defaults
        if template.get("is_default"):
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE analysis_templates SET is_default = 0")
                await conn.commit()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO analysis_templates (
                    id, name, slug, description, is_default, tags, layers, sort_fields,
                    preference_profile, risk_tolerance, research_mode, compiled_policy,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    template["name"],
                    template["slug"],
                    template.get("description"),
                    1 if template.get("is_default") else 0,
                    json.dumps(template.get("tags") or []),
                    json.dumps(template.get("layers") or []),
                    json.dumps(template.get("sort_fields") or []),
                    template.get("preference_profile"),
                    template.get("risk_tolerance"),
                    template.get("research_mode"),
                    json.dumps(template.get("compiled_policy") or {}),
                    now,
                    now,
                ),
            )
            await conn.commit()

            cursor = await conn.execute(
                "SELECT * FROM analysis_templates WHERE id = ?", (template_id,)
            )
            row = await cursor.fetchone()
            return self._template_row_to_dict(row)

    async def update_template(self, template_id: str, fields: dict) -> dict | None:
        """Update specific fields of an analysis template.

        Args:
            template_id: The template ID to update.
            fields: Dict of column_name -> new_value pairs.

        Returns:
            The updated template dict, or None if not found.
        """
        if not fields:
            return await self.get_template_by_id(template_id)

        # Serialize JSON fields
        json_fields = ("tags", "layers", "sort_fields", "compiled_policy")
        serialized = dict(fields)
        for field in json_fields:
            if field in serialized and not isinstance(serialized[field], str):
                serialized[field] = json.dumps(serialized[field])

        # Convert is_default to integer
        if "is_default" in serialized:
            serialized["is_default"] = 1 if serialized["is_default"] else 0

        serialized["updated_at"] = datetime.now().isoformat()

        set_clauses = [f"{col} = ?" for col in serialized]
        values = list(serialized.values()) + [template_id]

        async with self.pool.acquire() as conn:
            # If setting as default, clear other defaults first
            if fields.get("is_default"):
                await conn.execute("UPDATE analysis_templates SET is_default = 0")

            cursor = await conn.execute(
                f"UPDATE analysis_templates SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return None

            cursor = await conn.execute(
                "SELECT * FROM analysis_templates WHERE id = ?", (template_id,)
            )
            row = await cursor.fetchone()
            return self._template_row_to_dict(row) if row else None

    # ======================================================================
    # analysis_jobs
    # ======================================================================

    async def get_job_by_id(self, job_id: str) -> dict | None:
        """Fetch a single analysis job by its ID.

        Returns:
            A dict representation of the row, or None if not found.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            return self._job_row_to_dict(row) if row else None

    async def list_jobs(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List analysis jobs with pagination.

        Args:
            limit: Maximum number of jobs to return.
            offset: Number of jobs to skip.

        Returns:
            Tuple of (list of job dicts, total count).
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) AS total FROM analysis_jobs"
            )
            count_row = await cursor.fetchone()
            total = count_row[0] if count_row else 0

            cursor = await conn.execute(
                """
                SELECT * FROM analysis_jobs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = await cursor.fetchall()
            jobs = [self._job_row_to_dict(row) for row in rows]

        return jobs, total

    async def create_job(self, job: dict) -> dict:
        """Insert a new analysis job.

        Args:
            job: Dict with job fields. Required: trigger_type, scope_type, status.
                JSON fields (route_policy, budget_policy) will be serialized.

        Returns:
            The inserted job as a dict.
        """
        now = datetime.now().isoformat()
        job_id = job.get("id") or self._generate_id()
        status = job["status"]

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO analysis_jobs (
                    id, trigger_type, scope_type, template_id, route_policy, budget_policy,
                    status, requested_by, created_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job["trigger_type"],
                    job["scope_type"],
                    job.get("template_id"),
                    json.dumps(job.get("route_policy") or {}),
                    json.dumps(job.get("budget_policy") or {}),
                    status,
                    job.get("requested_by"),
                    now,
                    now if status in ("completed", "failed") else None,
                ),
            )
            await conn.commit()

            cursor = await conn.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            return self._job_row_to_dict(row)

    async def update_job_status(self, job_id: str, status: str, **extra_fields: Any) -> dict | None:
        """Update the status of an analysis job, optionally setting additional fields.

        Automatically sets finished_at when status is 'completed' or 'failed'.

        Args:
            job_id: The job ID to update.
            status: New status value.
            **extra_fields: Additional fields to update (e.g., route_policy, budget_policy).

        Returns:
            The updated job dict, or None if not found.
        """
        assignments = ["status = ?"]
        params: list[Any] = [status]

        # Auto-set finished_at for terminal statuses
        if status in ("completed", "failed"):
            assignments.append("finished_at = ?")
            params.append(datetime.now().isoformat())

        # Handle extra fields
        for key, value in extra_fields.items():
            assignments.append(f"{key} = ?")
            if key in ("route_policy", "budget_policy") and isinstance(value, dict):
                params.append(json.dumps(value))
            elif isinstance(value, datetime):
                params.append(value.isoformat())
            else:
                params.append(value)

        params.append(job_id)

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                f"UPDATE analysis_jobs SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return None

            cursor = await conn.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            return self._job_row_to_dict(row) if row else None

    # ======================================================================
    # analysis_job_items
    # ======================================================================

    async def get_job_item_by_id(self, item_id: str) -> dict | None:
        """Fetch a single analysis job item by its ID.

        Returns:
            A dict representation of the row, or None if not found.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM analysis_job_items WHERE id = ?", (item_id,)
            )
            row = await cursor.fetchone()
            return self._job_item_row_to_dict(row) if row else None

    async def list_job_items_by_job_id(self, job_id: str) -> list[dict]:
        """List all job items for a given job, ordered by creation date.

        Args:
            job_id: The parent job ID.

        Returns:
            List of job item dicts.
        """
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM analysis_job_items
                WHERE job_id = ?
                ORDER BY created_at ASC
                """,
                (job_id,),
            )
            rows = await cursor.fetchall()
            return [self._job_item_row_to_dict(row) for row in rows]

    async def create_job_item(self, item: dict) -> dict:
        """Insert a new analysis job item.

        Args:
            item: Dict with item fields. Required: job_id, activity_id, status.

        Returns:
            The inserted job item as a dict.
        """
        now = datetime.now().isoformat()
        item_id = item.get("id") or self._generate_id()
        status = item["status"]

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO analysis_job_items (
                    id, job_id, activity_id, status, needs_research, final_draft_status,
                    screening_model, research_model, verdict_model,
                    started_at, finished_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    item["job_id"],
                    item["activity_id"],
                    status,
                    1 if item.get("needs_research") else 0,
                    item.get("final_draft_status"),
                    item.get("screening_model"),
                    item.get("research_model"),
                    item.get("verdict_model"),
                    now,
                    now if status in ("completed", "failed") else None,
                    now,
                    now,
                ),
            )
            await conn.commit()

            cursor = await conn.execute(
                "SELECT * FROM analysis_job_items WHERE id = ?", (item_id,)
            )
            row = await cursor.fetchone()
            return self._job_item_row_to_dict(row)

    async def update_job_item(self, item_id: str, fields: dict) -> dict | None:
        """Update specific fields of an analysis job item.

        Automatically sets updated_at. Sets finished_at when status becomes
        'completed' or 'failed'.

        Args:
            item_id: The job item ID to update.
            fields: Dict of column_name -> new_value pairs.

        Returns:
            The updated job item dict, or None if not found.
        """
        if not fields:
            return await self.get_job_item_by_id(item_id)

        assignments = ["updated_at = ?"]
        params: list[Any] = [datetime.now().isoformat()]

        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            if key == "needs_research":
                params.append(1 if value else 0)
            elif isinstance(value, datetime):
                params.append(value.isoformat())
            else:
                params.append(value)

        # Auto-set finished_at for terminal statuses
        if "status" in fields and fields["status"] in ("completed", "failed") and "finished_at" not in fields:
            assignments.append("finished_at = ?")
            params.append(datetime.now().isoformat())

        params.append(item_id)

        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                f"UPDATE analysis_job_items SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return None

            cursor = await conn.execute(
                "SELECT * FROM analysis_job_items WHERE id = ?", (item_id,)
            )
            row = await cursor.fetchone()
            return self._job_item_row_to_dict(row) if row else None

    # ======================================================================
    # Private helpers
    # ======================================================================

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique record ID using timestamp + random bytes."""
        import hashlib
        import os
        return hashlib.md5(
            f"{datetime.now().isoformat()}:{os.urandom(8).hex()}".encode()
        ).hexdigest()

    @staticmethod
    def _template_row_to_dict(row) -> dict:
        """Convert an analysis_templates row to a dict with JSON fields parsed."""
        keys = row.keys() if hasattr(row, "keys") else []
        return {
            "id": row["id"],
            "name": row["name"],
            "slug": row["slug"],
            "description": row["description"],
            "is_default": bool(row["is_default"]),
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "layers": json.loads(row["layers"]) if row["layers"] else [],
            "sort_fields": json.loads(row["sort_fields"]) if row["sort_fields"] else [],
            "preference_profile": row["preference_profile"] if "preference_profile" in keys else None,
            "risk_tolerance": row["risk_tolerance"] if "risk_tolerance" in keys else None,
            "research_mode": row["research_mode"] if "research_mode" in keys else None,
            "compiled_policy": json.loads(row["compiled_policy"])
            if "compiled_policy" in keys and row["compiled_policy"]
            else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _job_row_to_dict(row) -> dict:
        """Convert an analysis_jobs row to a dict with JSON fields parsed."""
        return {
            "id": row["id"],
            "trigger_type": row["trigger_type"],
            "scope_type": row["scope_type"],
            "template_id": row["template_id"],
            "route_policy": json.loads(row["route_policy"]) if row["route_policy"] else {},
            "budget_policy": json.loads(row["budget_policy"]) if row["budget_policy"] else {},
            "status": row["status"],
            "requested_by": row["requested_by"],
            "created_at": row["created_at"],
            "finished_at": row["finished_at"],
        }

    @staticmethod
    def _job_item_row_to_dict(row) -> dict:
        """Convert an analysis_job_items row to a dict."""
        return {
            "id": row["id"],
            "job_id": row["job_id"],
            "activity_id": row["activity_id"],
            "status": row["status"],
            "needs_research": bool(row["needs_research"]),
            "final_draft_status": row["final_draft_status"],
            "screening_model": row["screening_model"],
            "research_model": row["research_model"],
            "verdict_model": row["verdict_model"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
