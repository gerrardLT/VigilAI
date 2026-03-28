"""
Replay-based regression coverage for the agent-analysis harness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.policies import ResearchPolicy, SafetyPolicy  # noqa: E402
from analysis.providers.mock_provider import MockAnalysisProvider  # noqa: E402
from analysis.providers.router import AnalysisModelRouter  # noqa: E402
from analysis.research_agent import ResearchAgent  # noqa: E402
from analysis.research_fetcher import FetchedDocument, ResearchFetcher  # noqa: E402
from analysis.safety_gate import AnalysisSafetyGate  # noqa: E402
from analysis.schemas import AnalysisContext  # noqa: E402
from analysis.screening_agent import ScreeningAgent  # noqa: E402
from analysis.verdict_agent import VerdictAgent  # noqa: E402


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "agent_analysis_eval_set.json"


@pytest.fixture
def eval_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _build_router() -> AnalysisModelRouter:
    return AnalysisModelRouter(
        {
            "screening": {"low": "screening-cheap", "default": "screening-main"},
            "verdict": {"default": "verdict-main"},
        }
    )


def _risk_flags_match(expected_flags: list[str], actual_flags: list[str]) -> bool:
    expected = set(expected_flags)
    actual = set(actual_flags)
    if not expected:
        return not actual
    return expected.issubset(actual)


def replay_eval_set(cases: list[dict]):
    router = _build_router()
    safety_gate = AnalysisSafetyGate()
    results: list[dict[str, object]] = []

    for case in cases:
        context = AnalysisContext.model_validate(case["context"])
        screening_agent = ScreeningAgent(
            provider=MockAnalysisProvider(screening_payload=case.get("screening_payload") or {}),
            router=router,
        )
        screening = screening_agent.run(context, budget_tier="low")

        research_agent = ResearchAgent(
            fetcher=ResearchFetcher(
                documents=[
                    FetchedDocument.model_validate(document)
                    for document in case.get("research_documents", [])
                ]
            )
        )
        research = research_agent.run(
            context=context,
            screening_result=screening,
            policy=ResearchPolicy.model_validate(case.get("research_policy") or {}),
        )

        verdict_agent = VerdictAgent(
            provider=MockAnalysisProvider(verdict_payload=case.get("verdict_payload") or {}),
            router=router,
        )
        draft = verdict_agent.run(
            context=context,
            screening_result=screening,
            research_result=research,
            task_type="verdict",
            budget_tier="default",
        )
        final_snapshot = safety_gate.apply(
            draft=draft,
            context=context,
            policy=SafetyPolicy.model_validate(case.get("safety_policy") or {}),
        )

        expected = case["expected"]
        results.append(
            {
                "id": case["id"],
                "expected_status": expected["status"],
                "final_status": final_snapshot.status,
                "draft_status": draft.status,
                "risk_flags": final_snapshot.risk_flags,
                "expected_risk_flags": expected.get("risk_flags", []),
                "research_state": final_snapshot.research_state,
                "status_match": final_snapshot.status == expected["status"],
                "risk_flags_match": _risk_flags_match(
                    expected.get("risk_flags", []),
                    final_snapshot.risk_flags,
                ),
            }
        )

    total = len(results)
    status_matches = sum(1 for item in results if item["status_match"])
    risk_flag_matches = sum(1 for item in results if item["risk_flags_match"])

    return {
        "total": total,
        "status_match_rate": status_matches / total if total else 0.0,
        "risk_flag_match_rate": risk_flag_matches / total if total else 0.0,
        "cases": results,
    }


def test_eval_replay_matches_expected_status_and_risk_flags(eval_fixture):
    report = replay_eval_set(eval_fixture)

    assert report["total"] >= 5
    assert report["status_match_rate"] >= 0.8
    assert report["risk_flag_match_rate"] >= 0.7
    assert any(case["research_state"] == "completed" for case in report["cases"])
    assert any(case["research_state"] == "research_unavailable" for case in report["cases"])
    assert any(case["draft_status"] != case["final_status"] for case in report["cases"])
