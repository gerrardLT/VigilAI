"""
Tests for provider routing and deterministic contract providers.
"""

from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.providers.mock_provider import MockAnalysisProvider  # noqa: E402
from analysis.providers.router import AnalysisModelRouter  # noqa: E402


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
