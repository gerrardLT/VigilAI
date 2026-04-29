"""
Deterministic provider implementation used in tests and explicit local dry runs.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from analysis.providers.base import ProviderResponse


class DeterministicTestAnalysisProvider:
    def __init__(
        self,
        *,
        screening_payload: dict[str, Any] | None = None,
        research_payload: dict[str, Any] | None = None,
        verdict_payload: dict[str, Any] | None = None,
        default_payload: dict[str, Any] | None = None,
    ) -> None:
        self.payloads = {
            "screening": screening_payload if screening_payload is not None else {"status": "watch"},
            "research": research_payload if research_payload is not None else {"research_state": "not_requested"},
            "verdict": verdict_payload if verdict_payload is not None else {"status": "watch"},
        }
        self.default_payload = default_payload if default_payload is not None else {"status": "watch"}

    def generate_structured(
        self,
        *,
        task_type: str,
        schema_name: str,
        json_schema: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> ProviderResponse:
        payload = deepcopy(self.payloads.get(task_type, self.default_payload))
        return ProviderResponse(
            task_type=task_type,
            schema_name=schema_name,
            model_name=model or f"test-{task_type}",
            output=payload,
            raw_output={"prompt": prompt, "tools": tools or []},
            tool_results=[],
        )
