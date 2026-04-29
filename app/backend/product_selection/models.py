"""
Pydantic models for the product-selection bounded context.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    KEYWORD = "keyword"
    CATEGORY = "category"
    LISTING_URL = "listing_url"


class PlatformScope(str, Enum):
    TAOBAO = "taobao"
    XIANYU = "xianyu"
    BOTH = "both"


class ResearchJobStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductSourceMode(str, Enum):
    LIVE = "live"
    FALLBACK = "fallback"
    MIXED = "mixed"
    FAILED = "failed"


class ProductTrackingStatus(str, Enum):
    SAVED = "saved"
    TRACKING = "tracking"
    DONE = "done"
    ARCHIVED = "archived"


class ProductResearchQuery(BaseModel):
    id: str
    query_type: QueryType
    query_text: str
    platform_scope: PlatformScope
    status: ResearchJobStatus
    created_at: datetime
    updated_at: datetime


class ProductOpportunity(BaseModel):
    id: str
    query_id: str
    platform: str
    platform_item_id: str
    title: str
    image_url: Optional[str] = None
    category_path: Optional[str] = None
    price_low: Optional[float] = None
    price_mid: Optional[float] = None
    price_high: Optional[float] = None
    sales_volume: Optional[int] = None
    seller_count: Optional[int] = None
    seller_type: Optional[str] = None
    seller_name: Optional[str] = None
    demand_score: float = 0
    competition_score: float = 0
    price_fit_score: float = 0
    risk_score: float = 0
    cross_platform_signal_score: float = 0
    opportunity_score: float = 0
    confidence_score: float = 0
    risk_tags: list[str] = Field(default_factory=list)
    reason_blocks: list[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    source_urls: list[str] = Field(default_factory=list)
    source_mode: ProductSourceMode = ProductSourceMode.LIVE
    source_diagnostics: dict[str, Any] = Field(default_factory=dict)
    snapshot_at: datetime
    created_at: datetime
    updated_at: datetime
    is_tracking: bool = False
    is_favorited: bool = False


class ProductOpportunitySignal(BaseModel):
    id: str
    opportunity_id: str
    platform: str
    signal_type: str
    value_json: dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0
    freshness: Optional[str] = None
    reliability: Optional[float] = None
    created_at: datetime


class ProductTrackingState(BaseModel):
    opportunity_id: str
    is_favorited: bool = False
    status: ProductTrackingStatus = ProductTrackingStatus.SAVED
    notes: Optional[str] = None
    next_action: Optional[str] = None
    remind_at: Optional[str] = None
    created_at: str
    updated_at: str
