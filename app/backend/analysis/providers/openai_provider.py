"""
OpenAI-backed provider implementation for structured agent-analysis calls.
"""

from __future__ import annotations

import json
from typing import Any

from config import ANALYSIS_OPENAI_API_KEY

from analysis.providers.base import ProviderResponse, ProviderUsage


class OpenAIAnalysisProvider:
    def __init__(self, *, api_key: str | None = None, client: Any = None) -> None:
        self.api_key = api_key or ANALYSIS_OPENAI_API_KEY
        self.client = client or self._build_client()

    def _build_client(self) -> Any:
        if not self.api_key:
            raise RuntimeError("ANALYSIS_OPENAI_API_KEY or OPENAI_API_KEY is required for the OpenAI provider")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required to use the OpenAI analysis provider") from exc

        return OpenAI(api_key=self.api_key)

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
        if not model:
            raise ValueError("A concrete model name is required for OpenAI provider calls")
        if not json_schema:
            raise ValueError("OpenAI structured calls require a JSON schema")

        response = self.client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            tools=tools or [],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": json_schema,
                    "strict": True,
                }
            },
        )

        raw_text = getattr(response, "output_text", "") or ""
        if not raw_text:
            raise ValueError(f"OpenAI provider returned no structured output for schema {schema_name}")
        try:
            output = json.loads(raw_text)
        except json.JSONDecodeError:
            raise ValueError(f"OpenAI provider returned non-JSON output for schema {schema_name}") from None

        usage = getattr(response, "usage", None)
        return ProviderResponse(
            task_type=task_type,
            schema_name=schema_name,
            model_name=model,
            output=output,
            raw_output=response.model_dump() if hasattr(response, "model_dump") else raw_text,
            usage=ProviderUsage(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
            ),
            tool_results=[],
        )
