"""Autonomous investigation loop for reward-opportunity evaluation."""

from __future__ import annotations

from typing import Any, Callable

from reward_opportunity.graph import RewardInvestigationGraph
from reward_opportunity.pydantic_evaluator import EvaluatorClient


CollectorFn = Callable[[dict[str, object], dict[str, object], int], list[dict[str, object]]]
ExtractEvidenceFn = Callable[[list[dict[str, object]], dict[str, object]], dict[str, object]]


def run_investigation_cycle(
    candidate: dict[str, object],
    evidence_bundle: dict[str, object],
    max_rounds: int = 2,
    max_new_links: int = 3,
    timeout_seconds: int = 10,
    collector: CollectorFn | None = None,
    extract_evidence: ExtractEvidenceFn | None = None,
    evaluator_client: EvaluatorClient | None = None,
) -> dict[str, object]:
    graph = RewardInvestigationGraph(collector=collector, extract_evidence=extract_evidence, evaluator_client=evaluator_client)
    result = graph.invoke(
        {
            "candidate": candidate,
            "evidence_bundle": evidence_bundle,
            "budgets": {
                "max_rounds": max_rounds,
                "max_new_links": max_new_links,
                "timeout_seconds": timeout_seconds,
            },
        }
    )
    result["rounds_used"] = result.get("round_index", 0)
    return result
