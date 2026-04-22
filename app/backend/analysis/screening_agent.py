"""
First-pass screening agent for stored-content analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from analysis.ai_enrichment import screening_result_from_heuristics
from analysis.providers import AnalysisModelRouter, build_analysis_provider
from analysis.schemas import AnalysisContext, ScreeningResult

logger = logging.getLogger(__name__)


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_screening_prompt(context: AnalysisContext) -> str:
    current_snapshot = context.current_snapshot.model_dump(mode="json") if context.current_snapshot else None
    return "\n".join(
        [
            "You are the VigilAI screening agent.",
            "Use only the stored internal activity content provided below.",
            "Do not claim external research and do not invent missing facts.",
            "Return a structured first-pass screening result.",
            "",
            "Activity content:",
            json.dumps(context.content.model_dump(mode="json"), ensure_ascii=False, indent=2, default=_json_default),
            "",
            "Source health:",
            json.dumps(context.source_health, ensure_ascii=False, indent=2, default=_json_default),
            "",
            "Tracking and metadata:",
            json.dumps(
                {
                    "tracking": context.tracking,
                    "metadata": context.metadata,
                    "current_snapshot": current_snapshot,
                },
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            ),
            "",
            "Heuristic hints:",
            json.dumps(context.heuristic_signals, ensure_ascii=False, indent=2, default=_json_default),
        ]
    )


class ScreeningAgent:
    def __init__(self, *, provider=None, router: AnalysisModelRouter | None = None) -> None:
        self.provider = provider or build_analysis_provider()
        self.router = router or AnalysisModelRouter()

    def run(self, context: AnalysisContext, *, budget_tier: str = "low") -> ScreeningResult:
        route = self.router.select(task_type="screening", budget_tier=budget_tier)
        prompt = build_screening_prompt(context)
        heuristic_result = screening_result_from_heuristics(context, model_name=route.primary_model)

        try:
            response = self.provider.generate_structured(
                task_type="screening",
                schema_name="screening_result",
                json_schema=ScreeningResult.model_json_schema(),
                prompt=prompt,
                model=route.primary_model,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            logger.warning("Screening provider failed for activity %s: %s", context.activity_id, exc)
            return screening_result_from_heuristics(
                context,
                model_name=route.primary_model,
                provider_error=str(exc),
            )

        merged = heuristic_result.model_dump(mode="json")
        provider_output = dict(response.output or {})
        merged.update(provider_output)

        merged_structured = dict(heuristic_result.structured)
        merged_structured.update(provider_output.get("structured") or {})
        merged_structured.setdefault("should_deep_research", heuristic_result.structured["should_deep_research"])
        merged["structured"] = merged_structured

        merged["risk_flags"] = list(
            dict.fromkeys([*heuristic_result.risk_flags, *(provider_output.get("risk_flags") or [])])
        )
        merged["research_state"] = provider_output.get("research_state") or "not_requested"
        merged["model_name"] = response.model_name or route.primary_model

        if "needs_manual_review" not in provider_output:
            merged["needs_manual_review"] = heuristic_result.needs_manual_review

        try:
            return ScreeningResult.model_validate(merged)
        except ValidationError as exc:
            logger.warning("Screening provider returned invalid payload for activity %s: %s", context.activity_id, exc)
            return screening_result_from_heuristics(
                context,
                model_name=response.model_name or route.primary_model,
                provider_error="invalid_provider_payload",
            )
