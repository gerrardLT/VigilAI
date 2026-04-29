"""
Explicitly disabled provider used when no real analysis backend is configured.
"""

from __future__ import annotations

from typing import Any


class DisabledAnalysisProvider:
    def generate_structured(
        self,
        *,
        task_type: str,
        schema_name: str,
        json_schema: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ):
        raise RuntimeError(
            "ANALYSIS_PROVIDER is disabled. Configure ANALYSIS_PROVIDER=openai and a valid "
            "ANALYSIS_OPENAI_API_KEY or OPENAI_API_KEY to enable real analysis calls."
        )
