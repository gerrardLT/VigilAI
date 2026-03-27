"""
Policy models compiled from business-facing analysis templates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class RouteTargetPolicy(BaseModel):
    task_type: str
    model_tier: str | None = None


class RoutePolicy(BaseModel):
    single_item: RouteTargetPolicy
    batch: RouteTargetPolicy


class BudgetPolicy(BaseModel):
    item_token_limit: int
    daily_token_limit: int
    allow_manual_override: bool = True


class ResearchPolicy(BaseModel):
    default_mode: Literal["off", "shallow", "layered", "deep"] = "layered"
    max_queries_per_item: int = 3


class SafetyPolicy(BaseModel):
    writeback_mode: Literal["auto", "human_review", "dry_run"] = "human_review"
    allow_external_actions: bool = False


class CompiledAnalysisTemplate(BaseModel):
    route_policy: RoutePolicy
    budget_policy: BudgetPolicy
    research_policy: ResearchPolicy
    safety_policy: SafetyPolicy
