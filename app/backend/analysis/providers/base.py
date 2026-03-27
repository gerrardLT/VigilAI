"""
Shared provider contracts for agent-analysis model calls.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ProviderUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderModelRoute(BaseModel):
    task_type: str
    budget_tier: str
    primary_model: str
    fallback_model: str | None = None
    downgraded_from: str | None = None


class ProviderResponse(BaseModel):
    task_type: str
    schema_name: str
    model_name: str
    output: dict[str, Any] = Field(default_factory=dict)
    raw_output: Any = None
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisProvider(Protocol):
    def generate_structured(
        self,
        *,
        task_type: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> ProviderResponse: ...
