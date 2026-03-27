"""
Default analysis templates for the AI filtering MVP.
"""

from __future__ import annotations

from copy import deepcopy


DEFAULT_ANALYSIS_TEMPLATES = [
    {
        "name": "Quick money",
        "slug": "quick-money",
        "description": "Prioritize short-cycle opportunities with low effort and explicit rewards.",
        "is_default": True,
        "tags": ["money-first", "fast-return"],
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


def get_default_analysis_templates() -> list[dict]:
    return deepcopy(DEFAULT_ANALYSIS_TEMPLATES)
