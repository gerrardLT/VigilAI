"""
Compile business-facing analysis template fields into executable policies.
"""

from __future__ import annotations

from typing import Any

from analysis.policies import (
    BudgetPolicy,
    CompiledAnalysisTemplate,
    ResearchPolicy,
    RoutePolicy,
    RouteTargetPolicy,
    SafetyPolicy,
)

DEFAULT_PREFERENCE_PROFILE = "balanced"
DEFAULT_RISK_TOLERANCE = "balanced"
DEFAULT_RESEARCH_MODE = "layered"

_ROUTE_BY_PROFILE = {
    "money_first": RoutePolicy(
        single_item=RouteTargetPolicy(task_type="deep_analysis", model_tier="high"),
        batch=RouteTargetPolicy(task_type="screening", model_tier="standard"),
    ),
    "balanced": RoutePolicy(
        single_item=RouteTargetPolicy(task_type="deep_analysis", model_tier="standard"),
        batch=RouteTargetPolicy(task_type="screening", model_tier="standard"),
    ),
    "safety_first": RoutePolicy(
        single_item=RouteTargetPolicy(task_type="deep_analysis", model_tier="high"),
        batch=RouteTargetPolicy(task_type="screening", model_tier="high"),
    ),
}

_BUDGET_BY_RISK = {
    "conservative": BudgetPolicy(item_token_limit=2500, daily_token_limit=30000, allow_manual_override=False),
    "balanced": BudgetPolicy(item_token_limit=4000, daily_token_limit=60000, allow_manual_override=True),
    "aggressive": BudgetPolicy(item_token_limit=6000, daily_token_limit=100000, allow_manual_override=True),
}

_RESEARCH_QUERY_CAP = {
    "off": 0,
    "shallow": 2,
    "layered": 4,
    "deep": 8,
}

_SAFETY_BY_RISK = {
    "conservative": SafetyPolicy(writeback_mode="human_review", allow_external_actions=False),
    "balanced": SafetyPolicy(writeback_mode="human_review", allow_external_actions=False),
    "aggressive": SafetyPolicy(writeback_mode="human_review", allow_external_actions=False),
}


def _norm(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return default


def build_route_policy(raw_template: dict[str, Any]) -> RoutePolicy:
    profile = _norm(raw_template.get("preference_profile"), DEFAULT_PREFERENCE_PROFILE)
    return _ROUTE_BY_PROFILE.get(profile, _ROUTE_BY_PROFILE[DEFAULT_PREFERENCE_PROFILE]).model_copy(deep=True)


def build_budget_policy(raw_template: dict[str, Any]) -> BudgetPolicy:
    risk = _norm(raw_template.get("risk_tolerance"), DEFAULT_RISK_TOLERANCE)
    return _BUDGET_BY_RISK.get(risk, _BUDGET_BY_RISK[DEFAULT_RISK_TOLERANCE]).model_copy(deep=True)


def build_research_policy(raw_template: dict[str, Any]) -> ResearchPolicy:
    mode = _norm(raw_template.get("research_mode"), DEFAULT_RESEARCH_MODE)
    if mode not in _RESEARCH_QUERY_CAP:
        mode = DEFAULT_RESEARCH_MODE
    return ResearchPolicy(default_mode=mode, max_queries_per_item=_RESEARCH_QUERY_CAP[mode])


def build_safety_policy(raw_template: dict[str, Any]) -> SafetyPolicy:
    risk = _norm(raw_template.get("risk_tolerance"), DEFAULT_RISK_TOLERANCE)
    return _SAFETY_BY_RISK.get(risk, _SAFETY_BY_RISK[DEFAULT_RISK_TOLERANCE]).model_copy(deep=True)


def compile_analysis_template(raw_template: dict[str, Any]) -> CompiledAnalysisTemplate:
    return CompiledAnalysisTemplate(
        route_policy=build_route_policy(raw_template),
        budget_policy=build_budget_policy(raw_template),
        research_policy=build_research_policy(raw_template),
        safety_policy=build_safety_policy(raw_template),
    )
