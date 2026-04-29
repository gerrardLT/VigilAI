"""
Data models for VigilAI.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
from typing import Any, List, Optional

from analysis.schemas import AnalysisSnapshot
from pydantic import BaseModel, Field

from agent_platform.models import AgentArtifact, AgentJob, AgentSession, AgentTurn


class Category(str, Enum):
    HACKATHON = "hackathon"
    DATA_COMPETITION = "data_competition"
    CODING_COMPETITION = "coding_competition"
    OTHER_COMPETITION = "other_competition"
    AIRDROP = "airdrop"
    BOUNTY = "bounty"
    GRANT = "grant"
    DEV_EVENT = "dev_event"
    NEWS = "news"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    RSS = "rss"
    WEB = "web"
    API = "api"
    FIRECRAWL = "firecrawl"
    KAGGLE = "kaggle"
    TECH_MEDIA = "tech_media"
    AIRDROP = "airdrop"
    DATA_COMPETITION = "data_competition"
    HACKATHON_AGGREGATOR = "hackathon_aggregator"
    BOUNTY = "bounty"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    DESIGN_COMPETITION = "design_competition"
    CODING_COMPETITION = "coding_competition"
    UNIVERSAL = "universal"


class SourceStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class TrackingStatus(str, Enum):
    SAVED = "saved"
    TRACKING = "tracking"
    DONE = "done"
    ARCHIVED = "archived"


class DigestStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"


class Prize(BaseModel):
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None


class ActivityDates(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None


class TimelineEvent(BaseModel):
    key: str
    label: str
    timestamp: str


class TrackingState(BaseModel):
    activity_id: str
    is_favorited: bool = False
    status: TrackingStatus = TrackingStatus.SAVED
    stage: Optional[str] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    remind_at: Optional[str] = None
    block_reason: Optional[str] = None
    abandon_reason: Optional[str] = None
    created_at: str
    updated_at: str


class DigestRecord(BaseModel):
    id: str
    digest_date: str
    title: str
    summary: Optional[str] = None
    content: str
    item_ids: List[str] = Field(default_factory=list)
    status: DigestStatus = DigestStatus.DRAFT
    created_at: str
    updated_at: str
    last_sent_at: Optional[str] = None
    send_channel: Optional[str] = None


class Activity(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    full_content: Optional[str] = None
    source_id: str
    source_name: str
    url: str
    category: Category
    tags: List[str] = Field(default_factory=list)
    prize: Optional[Prize] = None
    dates: Optional[ActivityDates] = None
    location: Optional[str] = None
    organizer: Optional[str] = None
    image_url: Optional[str] = None
    summary: Optional[str] = None
    score: Optional[float] = None
    score_reason: Optional[str] = None
    deadline_level: Optional[str] = None
    trust_level: Optional[str] = None
    updated_fields: List[str] = Field(default_factory=list)
    analysis_fields: dict = Field(default_factory=dict)
    analysis_status: Optional[str] = None
    analysis_failed_layer: Optional[str] = None
    analysis_summary_reasons: List[str] = Field(default_factory=list)
    analysis_summary: Optional[str] = None
    analysis_reasons: List[str] = Field(default_factory=list)
    analysis_risk_flags: List[str] = Field(default_factory=list)
    analysis_recommended_action: Optional[str] = None
    analysis_confidence: Optional[float] = None
    analysis_structured: dict[str, Any] = Field(default_factory=dict)
    analysis_template_id: Optional[str] = None
    analysis_current_run_id: Optional[str] = None
    analysis_updated_at: Optional[datetime] = None
    is_tracking: bool = False
    is_favorited: bool = False
    is_digest_candidate: bool = False
    status: str = "upcoming"
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def generate_id(source_id: str, url: str) -> str:
        return hashlib.md5(f"{source_id}:{url}".encode()).hexdigest()


class Source(BaseModel):
    id: str
    name: str
    type: SourceType
    url: str
    priority: Priority
    update_interval: int
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    status: SourceStatus = SourceStatus.IDLE
    error_message: Optional[str] = None
    activity_count: int = 0


class AnalysisJob(BaseModel):
    id: str
    trigger_type: str
    scope_type: str
    template_id: Optional[str] = None
    route_policy: dict[str, Any] = Field(default_factory=dict)
    budget_policy: dict[str, Any] = Field(default_factory=dict)
    status: str
    requested_by: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class AnalysisJobItem(BaseModel):
    id: str
    job_id: str
    activity_id: str
    status: str
    needs_research: bool = False
    final_draft_status: Optional[str] = None
    screening_model: Optional[str] = None
    research_model: Optional[str] = None
    verdict_model: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AnalysisStep(BaseModel):
    id: str
    job_item_id: str
    step_type: str
    step_status: str
    input_digest: Optional[str] = None
    output_payload: dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[int] = None
    cost_tokens_in: Optional[int] = None
    cost_tokens_out: Optional[int] = None
    model_name: Optional[str] = None
    created_at: datetime


class AnalysisEvidence(BaseModel):
    id: str
    job_item_id: str
    source_type: str
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None
    trust_score: Optional[float] = None
    supports_claim: Optional[bool] = None
    created_at: datetime


class AnalysisReview(BaseModel):
    id: str
    job_item_id: str
    activity_id: str
    review_action: str
    review_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: datetime


class AnalysisReviewResult(BaseModel):
    review_action: str
    item_id: str
    activity_id: str
    review_note: Optional[str] = None
    snapshot: AnalysisSnapshot | None = None


class ActivityListResponse(BaseModel):
    items: List[Activity]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsResponse(BaseModel):
    total_activities: int
    total_sources: int
    activities_by_category: dict
    activities_by_source: dict
    recent_activities: int
    last_update: Optional[str] = None
