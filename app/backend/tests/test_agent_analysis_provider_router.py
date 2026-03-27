"""
Tests for provider routing and deterministic contract providers.
"""

from __future__ import annotations

import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.providers.openai_provider import OpenAIAnalysisProvider  # noqa: E402
from analysis.providers.mock_provider import MockAnalysisProvider  # noqa: E402
from analysis.providers.router import AnalysisModelRouter  # noqa: E402
from analysis.template_compiler import compile_analysis_template  # noqa: E402


class _FakeUsage:
    input_tokens = 11
    output_tokens = 7


class _FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.usage = _FakeUsage()

    def model_dump(self):
        return {"output_text": self.output_text}


class _FakeResponsesClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class _FakeOpenAIClient:
    def __init__(self, response: _FakeResponse):
        self.responses = _FakeResponsesClient(response)


def test_model_router_selects_models_by_task_type_and_budget():
    router = AnalysisModelRouter(
        {
            "screening": {"low": "screening-cheap", "default": "screening-main"},
            "research": {"default": "research-main", "fallback": "research-backup"},
        }
    )

    route = router.select(task_type="screening", budget_tier="low")

    assert route.primary_model == "screening-cheap"
    assert route.task_type == "screening"
    assert route.budget_tier == "low"


def test_model_router_logs_downgrade_when_requested_budget_tier_is_missing(caplog):
    router = AnalysisModelRouter(
        {
            "research": {
                "default": "research-main",
                "fallback": "research-backup",
            }
        }
    )

    with caplog.at_level(logging.WARNING):
        route = router.select(task_type="research", budget_tier="low")

    assert route.primary_model == "research-main"
    assert route.downgraded_from == "low"
    assert "downgrade" in caplog.text.lower()


def test_mock_provider_returns_structured_payload_for_contract_tests():
    provider = MockAnalysisProvider(
        screening_payload={"status": "pass", "confidence": 0.83}
    )

    response = provider.generate_structured(
        task_type="screening",
        schema_name="screening_result",
        prompt="...",
    )

    assert response.output["status"] == "pass"
    assert response.output["confidence"] == 0.83
    assert response.model_name == "mock-screening"


def test_model_router_accepts_compiled_template_route_targets():
    compiled = compile_analysis_template(
        {
            "name": "Balanced profile",
            "preference_profile": "balanced",
            "risk_tolerance": "balanced",
            "research_mode": "layered",
        }
    )
    router = AnalysisModelRouter(
        {
            "screening": {"default": "screening-main", "low": "screening-cheap"},
            "deep_analysis": {"default": "verdict-main", "high": "verdict-main"},
        }
    )

    route = router.select(
        task_type=compiled.route_policy.single_item.task_type,
        budget_tier=compiled.route_policy.single_item.model_tier or "default",
    )

    assert route.task_type == "deep_analysis"
    assert route.primary_model == "verdict-main"
    assert route.budget_tier == "default"


def test_openai_provider_uses_json_schema_and_fails_closed_on_invalid_json():
    provider = OpenAIAnalysisProvider(
        api_key="test-key",
        client=_FakeOpenAIClient(_FakeResponse("not-json")),
    )

    with pytest.raises(ValueError):
        provider.generate_structured(
            task_type="screening",
            schema_name="screening_result",
            json_schema={
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
            },
            prompt="...",
            model="gpt-4o-mini",
        )


def test_openai_provider_passes_json_schema_and_returns_structured_output():
    fake_client = _FakeOpenAIClient(_FakeResponse('{"status":"pass","confidence":0.83}'))
    provider = OpenAIAnalysisProvider(
        api_key="test-key",
        client=fake_client,
    )

    response = provider.generate_structured(
        task_type="screening",
        schema_name="screening_result",
        json_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["status", "confidence"],
        },
        prompt="...",
        model="gpt-4o-mini",
    )

    assert response.output["status"] == "pass"
    assert response.output["confidence"] == 0.83
    assert fake_client.responses.last_kwargs["text"]["format"]["type"] == "json_schema"
    assert fake_client.responses.last_kwargs["text"]["format"]["schema"]["required"] == [
        "status",
        "confidence",
    ]
