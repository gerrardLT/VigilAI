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


class AnalysisContent(BaseModel):
    title: str
    description: str | None = None
    full_content: str | None = None
    full_text: str
    url: str
    category: str
    summary: str | None = None
    source_name: str | None = None


class AnalysisContext(BaseModel):
    activity_id: str
    source_id: str
    content: AnalysisContent
    source_health: dict[str, Any] = Field(default_factory=dict)
    tracking: dict[str, Any] = Field(default_factory=dict)
    heuristic_signals: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    current_snapshot: AnalysisSnapshot | None = None


class ScreeningResult(BaseModel):
    status: Literal["pass", "watch", "reject"]
    summary: str
    reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    confidence: float | None = None
    structured: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: str | None = None
    research_state: Literal["not_requested", "requested", "completed", "failed"] = "not_requested"
    needs_manual_review: bool = False
    model_name: str | None = None
