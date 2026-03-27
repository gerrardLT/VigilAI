"""
Default analysis templates for the AI filtering MVP.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from analysis.template_compiler import (
    DEFAULT_PREFERENCE_PROFILE,
    DEFAULT_RESEARCH_MODE,
    DEFAULT_RISK_TOLERANCE,
    compile_analysis_template,
)


DEFAULT_TEMPLATE_BUSINESS_FIELDS = {
    "preference_profile": DEFAULT_PREFERENCE_PROFILE,
    "risk_tolerance": DEFAULT_RISK_TOLERANCE,
    "research_mode": DEFAULT_RESEARCH_MODE,
}


DEFAULT_ANALYSIS_TEMPLATES = [
    {
        "name": "Quick money",
        "slug": "quick-money",
        "description": "Prioritize short-cycle opportunities with low effort and explicit rewards.",
        "is_default": True,
        "tags": ["money-first", "fast-return"],
        "preference_profile": "money_first",
        "risk_tolerance": "balanced",
        "research_mode": "layered",
        "sort_fields": ["roi", "payout_speed", "trust"],
        "layers": [
            {
                "key": "hard_gate",
                "label": "Hard gate",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "reward_clarity",
                        "label": "Reward must be explicit",
                        "enabled": True,
                        "operator": "gte",
                        "value": "medium",
                        "is_hard_gate": True,
                    },
                    {
                        "key": "solo_friendliness",
                        "label": "Must be solo-friendly",
                        "enabled": True,
                        "operator": "eq",
                        "value": "solo_friendly",
                        "is_hard_gate": True,
                    },
                ],
            },
            {
                "key": "roi",
                "label": "ROI",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "effort_level",
                        "label": "Estimated effort",
                        "enabled": True,
                        "operator": "lte",
                        "value": "medium",
                    },
                    {
                        "key": "payout_speed",
                        "label": "Payout speed",
                        "enabled": True,
                        "operator": "lte",
                        "value": "14d",
                    },
                ],
            },
            {
                "key": "trust",
                "label": "Trust",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "source_trust",
                        "label": "Source trust",
                        "enabled": True,
                        "operator": "gte",
                        "value": "medium",
                    }
                ],
            },
            {
                "key": "priority",
                "label": "Priority",
                "enabled": True,
                "mode": "rank",
                "conditions": [],
            },
        ],
    },
    {
        "name": "Low effort, high ROI",
        "slug": "low-effort-high-roi",
        "description": "Favor personal opportunities with low setup costs and strong payout-to-effort ratio.",
        "is_default": False,
        "tags": ["low-effort", "roi"],
        "preference_profile": "money_first",
        "risk_tolerance": "balanced",
        "research_mode": "layered",
        "sort_fields": ["effort", "roi", "deadline"],
        "layers": [
            {
                "key": "hard_gate",
                "label": "Hard gate",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "solo_friendliness",
                        "label": "Must be solo-friendly",
                        "enabled": True,
                        "operator": "eq",
                        "value": "solo_friendly",
                        "is_hard_gate": True,
                    }
                ],
            },
            {
                "key": "roi",
                "label": "ROI",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "roi_level",
                        "label": "ROI level",
                        "enabled": True,
                        "operator": "gte",
                        "value": "medium",
                    }
                ],
            },
            {
                "key": "trust",
                "label": "Trust",
                "enabled": True,
                "mode": "filter",
                "conditions": [],
            },
            {
                "key": "priority",
                "label": "Priority",
                "enabled": True,
                "mode": "rank",
                "conditions": [],
            },
        ],
    },
    {
        "name": "Safe and trusted",
        "slug": "safe-trust",
        "description": "Prefer clearer, better-backed opportunities even if payout is slightly slower.",
        "is_default": False,
        "tags": ["safe", "trusted"],
        "preference_profile": "safety_first",
        "risk_tolerance": "conservative",
        "research_mode": "layered",
        "sort_fields": ["trust", "clarity", "roi"],
        "layers": [
            {
                "key": "hard_gate",
                "label": "Hard gate",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "reward_clarity",
                        "label": "Reward clarity",
                        "enabled": True,
                        "operator": "gte",
                        "value": "medium",
                        "is_hard_gate": True,
                    }
                ],
            },
            {
                "key": "roi",
                "label": "ROI",
                "enabled": True,
                "mode": "filter",
                "conditions": [],
            },
            {
                "key": "trust",
                "label": "Trust",
                "enabled": True,
                "mode": "filter",
                "conditions": [
                    {
                        "key": "source_trust",
                        "label": "Source trust",
                        "enabled": True,
                        "operator": "gte",
                        "value": "high",
                    }
                ],
            },
            {
                "key": "priority",
                "label": "Priority",
                "enabled": True,
                "mode": "rank",
                "conditions": [],
            },
        ],
    },
]


COMPATIBILITY_TEMPLATE_PRESETS = {
    "money_first": {
        "layers": DEFAULT_ANALYSIS_TEMPLATES[0]["layers"],
        "sort_fields": DEFAULT_ANALYSIS_TEMPLATES[0]["sort_fields"],
    },
    "balanced": {
        "layers": DEFAULT_ANALYSIS_TEMPLATES[1]["layers"],
        "sort_fields": DEFAULT_ANALYSIS_TEMPLATES[1]["sort_fields"],
    },
    "safety_first": {
        "layers": DEFAULT_ANALYSIS_TEMPLATES[2]["layers"],
        "sort_fields": DEFAULT_ANALYSIS_TEMPLATES[2]["sort_fields"],
    },
}


def apply_template_compat_defaults(raw_template: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(raw_template)
    for key, value in DEFAULT_TEMPLATE_BUSINESS_FIELDS.items():
        merged.setdefault(key, value)
    preset = COMPATIBILITY_TEMPLATE_PRESETS.get(
        merged["preference_profile"],
        COMPATIBILITY_TEMPLATE_PRESETS[DEFAULT_PREFERENCE_PROFILE],
    )
    merged["tags"] = list(merged.get("tags") or [])
    merged["layers"] = deepcopy(merged.get("layers") or preset["layers"])
    merged["sort_fields"] = list(merged.get("sort_fields") or preset["sort_fields"])
    merged["compiled_policy"] = compile_analysis_template(merged).model_dump(mode="json")
    return merged


def get_default_analysis_templates() -> list[dict]:
    return [apply_template_compat_defaults(item) for item in deepcopy(DEFAULT_ANALYSIS_TEMPLATES)]
