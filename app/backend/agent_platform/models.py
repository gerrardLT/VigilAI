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
    policy_mode: str = "standard"
    memory_scope: str = "domain"
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


class AgentExecutionPlanStep(BaseModel):
    tool_name: str
    intent: str
    rationale: str
    priority: int = 1
    stage: str = "analysis"
    access_mode: str = "read_only"
    policy_decision: str = "allow"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionPlan(BaseModel):
    id: str
    session_id: str
    source_turn_id: Optional[str] = None
    mode: str
    summary: str
    requested_steps: list[AgentExecutionPlanStep] = Field(default_factory=list)
    runnable_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
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


class AgentSessionState(BaseModel):
    session_id: str
    goal: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    working_memory: list[str] = Field(default_factory=list)
    current_focus: Optional[str] = None
    next_question: Optional[str] = None
    next_action: Optional[str] = None
    summary: Optional[str] = None
    last_tool_names: list[str] = Field(default_factory=list)
    state_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AgentInsight(BaseModel):
    id: str
    session_id: str
    source_turn_id: Optional[str] = None
    insight_type: str
    content: str
    importance: float = 0.5
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentThinkingStep(BaseModel):
    id: str
    session_id: str
    source_turn_id: Optional[str] = None
    phase: str
    summary: str
    tool_name: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentMemory(BaseModel):
    id: str
    session_id: str
    source_turn_id: Optional[str] = None
    memory_type: str
    content: str
    importance: float = 0.5
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentReflection(BaseModel):
    id: str
    session_id: str
    source_turn_id: Optional[str] = None
    reflection_type: str
    summary: str
    action_item: Optional[str] = None
    score: float = 0.5
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
