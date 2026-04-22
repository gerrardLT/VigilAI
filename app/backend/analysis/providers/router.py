"""
Model routing helpers for agent-analysis provider calls.
"""

from __future__ import annotations

import logging

from analysis.providers.base import ProviderModelRoute
from config import ANALYSIS_MODEL_ROUTES

logger = logging.getLogger(__name__)

MODEL_TIER_ALIASES = {
    "standard": "default",
}


class AnalysisModelRouter:
    def __init__(self, routes: dict[str, dict[str, str]] | None = None):
        raw_routes = routes or ANALYSIS_MODEL_ROUTES
        self.routes = {
            task_type: {
                tier: model_name
                for tier, model_name in tier_map.items()
                if model_name
            }
            for task_type, tier_map in raw_routes.items()
        }

    def select(self, *, task_type: str, budget_tier: str = "default") -> ProviderModelRoute:
        task_routes = self.routes.get(task_type)
        if not task_routes:
            raise ValueError(f"No provider route configured for task type: {task_type}")

        normalized_budget_tier = MODEL_TIER_ALIASES.get(budget_tier, budget_tier)
        primary_model = task_routes.get(normalized_budget_tier)
        downgraded_from: str | None = None

        if primary_model is None and normalized_budget_tier != "default" and task_routes.get("default"):
            primary_model = task_routes["default"]
            downgraded_from = normalized_budget_tier
            logger.warning(
                "Downgrade provider route for %s from budget tier %s to default model %s",
                task_type,
                normalized_budget_tier,
                primary_model,
            )

        if primary_model is None and task_routes.get("fallback"):
            primary_model = task_routes["fallback"]
            downgraded_from = downgraded_from or normalized_budget_tier
            logger.warning(
                "Downgrade provider route for %s from budget tier %s to fallback model %s",
                task_type,
                normalized_budget_tier,
                primary_model,
            )

        if primary_model is None:
            raise ValueError(
                f"No model configured for task type {task_type} and budget tier {normalized_budget_tier}"
            )

        return ProviderModelRoute(
            task_type=task_type,
            budget_tier=normalized_budget_tier,
            primary_model=primary_model,
            fallback_model=task_routes.get("fallback"),
            downgraded_from=downgraded_from,
        )
