"""Action automator service for generating and executing recommended actions."""

from enum import Enum
from datetime import datetime
import hashlib
import os


class ActionType(str, Enum):
    REGISTER = "register"
    BOOKMARK = "bookmark"
    PREPARE_SUBMISSION = "prepare_submission"
    SET_REMINDER = "set_reminder"
    DISMISS = "dismiss"


class ActionAutomator:
    """Generates and executes recommended actions for high-scoring activities."""

    def __init__(self, pool, score_threshold: float = 80.0):
        self.pool = pool
        self.score_threshold = score_threshold

    async def generate_actions(self, activity: dict) -> list[dict]:
        """Generate recommended actions for a high-scoring activity."""
        score = activity.get("score") or 0
        if score < self.score_threshold:
            return []
        actions = []
        if activity.get("deadline"):
            actions.append({
                "type": ActionType.SET_REMINDER,
                "label": "设置截止提醒",
                "deadline": activity["deadline"],
            })
        if activity.get("url"):
            actions.append({
                "type": ActionType.REGISTER,
                "label": "前往报名",
            })
        actions.append({"type": ActionType.BOOKMARK, "label": "收藏跟进"})
        return actions

    async def execute_action(self, activity_id: str, action_type: str) -> dict:
        """Execute an action and persist it to action_recommendations table."""
        action_id = hashlib.md5(
            f"{activity_id}:{action_type}:{datetime.now().isoformat()}:{os.urandom(4).hex()}".encode()
        ).hexdigest()
        now = datetime.now().isoformat()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO action_recommendations (id, activity_id, action_type, label, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (action_id, activity_id, action_type, action_type, "executed", now),
            )
            await conn.commit()
        return {
            "id": action_id,
            "activity_id": activity_id,
            "action_type": action_type,
            "status": "executed",
            "created_at": now,
        }

    async def list_actions(self, activity_id: str) -> list[dict]:
        """List all actions for an activity."""
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM action_recommendations WHERE activity_id = ? ORDER BY created_at DESC",
                (activity_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
