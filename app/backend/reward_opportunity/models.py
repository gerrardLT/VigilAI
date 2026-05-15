"""Pydantic models for the reward-opportunity bounded context."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RewardSourceFeed(BaseModel):
    id: str
    name: str
    source_type: str
    source_platform: str | None = None
    entry_url: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    status: str = "idle"
    last_crawled_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RewardCrawlJob(BaseModel):
    id: str
    source_feed_id: str
    status: str
    mode: str = "scheduled"
    target_url: str | None = None
    document_count: int = 0
    candidate_count: int = 0
    opportunity_count: int = 0
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class RewardRawDocument(BaseModel):
    id: str
    crawl_job_id: str | None = None
    source_feed_id: str | None = None
    source_platform: str
    source_type: str | None = None
    source_url: str
    canonical_url: str | None = None
    title: str
    body: str | None = None
    summary: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RewardOpportunityEvidence(BaseModel):
    id: str
    opportunity_id: str
    evidence_type: str
    snippet: str
    source_url: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RewardEvaluationRun(BaseModel):
    id: str
    candidate_id: str | None = None
    opportunity_id: str | None = None
    ai_stage_2_label: str
    ai_confidence: float
    ai_summary: str | None = None
    ai_reasoning_brief: str | None = None
    ai_missing_evidence: list[str] = Field(default_factory=list)
    ai_risk_flags: list[str] = Field(default_factory=list)
    ai_structured_evidence: dict[str, Any] = Field(default_factory=dict)
    needs_investigation: bool = False
    created_at: datetime


class RewardOpportunity(BaseModel):
    id: str
    title: str
    normalized_title: str | None = None
    source_platform: str
    source_type: str | None = None
    source_url: str
    canonical_url: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime | None = None
    content_language: str | None = None
    raw_text_excerpt: str | None = None
    opportunity_type: str | None = None
    reward_type: str | None = None
    reward_value_text: str | None = None
    action_required: str | None = None
    eligibility: str | None = None
    deadline_text: str | None = None
    deadline_at: datetime | None = None
    region_limit: str | None = None
    platform_limit: str | None = None
    ai_stage_1_recall_reason: str | None = None
    ai_stage_2_label: str
    ai_confidence: float
    ai_summary: str | None = None
    ai_reasoning_brief: str | None = None
    ai_missing_evidence: list[str] = Field(default_factory=list)
    ai_risk_flags: list[str] = Field(default_factory=list)
    ai_structured_evidence: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    dedupe_key: str | None = None
    content_hash: str | None = None
    last_evaluated_at: datetime | None = None
    recheck_after: datetime | None = None
    evidence: list[RewardOpportunityEvidence] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    created_at: datetime


class RewardInvestigationAction(BaseModel):
    id: str
    run_id: str
    action_type: str
    target_url: str | None = None
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


class RewardEvaluationOutput(BaseModel):
    is_target_opportunity: bool = False
    opportunity_type: str = "unknown"
    reward_type: str = "unknown"
    stage_label: str = "reject"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_sufficiency: str = "insufficient"
    missing_evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    required_next_actions: list[str] = Field(default_factory=list)
    quoted_evidence_ids: list[str] = Field(default_factory=list)
    reasoning_brief: str = ""

    @classmethod
    def from_baseline(cls, payload: dict[str, Any]) -> "RewardEvaluationOutput":
        structured = payload.get("ai_structured_evidence") if isinstance(payload.get("ai_structured_evidence"), dict) else {}
        return cls(
            is_target_opportunity=bool(payload.get("is_target_opportunity")),
            opportunity_type=str(payload.get("opportunity_type") or "unknown"),
            reward_type=str(payload.get("reward_type") or "unknown"),
            stage_label=str(payload.get("stage_label") or payload.get("ai_stage_2_label") or "reject"),
            confidence=float(payload.get("confidence") or payload.get("ai_confidence") or 0.0),
            evidence_sufficiency=str(payload.get("evidence_sufficiency") or structured.get("evidence_sufficiency") or "insufficient"),
            missing_evidence=list(payload.get("missing_evidence") or payload.get("ai_missing_evidence") or []),
            risk_flags=list(payload.get("risk_flags") or payload.get("ai_risk_flags") or []),
            required_next_actions=list(payload.get("required_next_actions") or payload.get("recommended_next_actions") or []),
            quoted_evidence_ids=list(payload.get("quoted_evidence_ids") or []),
            reasoning_brief=str(payload.get("reasoning_brief") or payload.get("ai_reasoning_brief") or ""),
        )

    def to_legacy_evaluation(self, *, source: str = "pydantic_ai") -> dict[str, Any]:
        return {
            "is_target_opportunity": self.is_target_opportunity,
            "opportunity_type": self.opportunity_type,
            "reward_type": self.reward_type,
            "evidence_sufficiency": self.evidence_sufficiency,
            "recommended_next_actions": list(self.required_next_actions),
            "ai_stage_2_label": self.stage_label,
            "ai_confidence": self.confidence,
            "ai_summary": self.reasoning_brief,
            "ai_reasoning_brief": self.reasoning_brief,
            "ai_missing_evidence": list(self.missing_evidence),
            "ai_risk_flags": list(self.risk_flags),
            "ai_structured_evidence": {
                "evidence_sufficiency": self.evidence_sufficiency,
                "quoted_evidence_ids": list(self.quoted_evidence_ids),
                "required_next_actions": list(self.required_next_actions),
                "source": source,
            },
            "needs_investigation": self.stage_label in {"needs_more_evidence", "待补证据", "寰呰ˉ璇佹嵁"},
            "source": source,
        }
