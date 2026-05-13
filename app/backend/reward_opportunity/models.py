"""Pydantic models for the reward-opportunity bounded context."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RewardOpportunity(BaseModel):
    id: str
    title: str
    source_platform: str
    source_url: str
    ai_stage_2_label: str
    ai_confidence: float
    reward_type: Optional[str] = None
    reward_value_text: Optional[str] = None
    action_required: Optional[str] = None
    ai_summary: Optional[str] = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class RewardInvestigationAction(BaseModel):
    id: str
    run_id: str
    action_type: str
    target_url: Optional[str] = None
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RewardInvestigationRun(BaseModel):
    id: str
    candidate_id: str
    status: str
    current_round: int = 0
    actions: list[RewardInvestigationAction] = Field(default_factory=list)
    created_at: datetime

