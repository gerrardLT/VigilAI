"""
Deterministic provider implementation used in tests and local fallback flows.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from analysis.providers.base import ProviderResponse


class MockAnalysisProvider:
    def __init__(
        self,
        *,
        screening_payload: dict[str, Any] | None = None,
        research_payload: dict[str, Any] | None = None,
        verdict_payload: dict[str, Any] | None = None,
        default_payload: dict[str, Any] | None = None,
    ) -> None:
        self.payloads = {
            "screening": screening_payload or {"status": "watch"},
            "research": research_payload or {"research_state": "not_requested"},
            "verdict": verdict_payload or {"status": "watch"},
        }
        self.default_payload = default_payload or {"status": "watch"}

    def generate_structured(
        self,
        *,
        task_type: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> ProviderResponse:
        payload = deepcopy(self.payloads.get(task_type, self.default_payload))
        return ProviderResponse(
            task_type=task_type,
            schema_name=schema_name,
            model_name=model or f"mock-{task_type}",
            output=payload,
            raw_output={"prompt": prompt, "tools": tools or []},
            tool_results=[],
        )
