"""
Shared schemas for agent-analysis workflows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisSnapshot(BaseModel):
    status: Literal["pass", "watch", "reject", "insufficient_evidence"]
    summary: str
    reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    confidence: float | None = None
    structured: dict[str, Any] = Field(default_factory=dict)
    template_id: str | None = None
    current_run_id: str | None = None
    updated_at: datetime | None = None
