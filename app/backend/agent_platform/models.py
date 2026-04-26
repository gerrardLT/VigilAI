"""
Pydantic models for the shared agent platform layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentSession(BaseModel):
    id: str
    domain_type: str
    entry_mode: str
    status: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_turn_at: Optional[datetime] = None


class AgentTurn(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sequence_no: int
    tool_name: Optional[str] = None
    tool_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentArtifact(BaseModel):
    id: str
    session_id: str
    artifact_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentJob(BaseModel):
    id: str
    session_id: Optional[str] = None
    domain_type: str
    job_type: str
    status: str
    requested_by: Optional[str] = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None
