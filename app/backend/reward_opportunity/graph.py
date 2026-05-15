"""LangGraph-compatible orchestration for reward-opportunity investigations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, TypedDict

from .evaluator import evaluate_evidence_bundle
from .investigator import decide_next_investigation_actions
from .pydantic_evaluator import EvaluatorClient, evaluate_with_pydantic_ai


CollectorFn = Callable[[dict[str, object], dict[str, object], int], list[dict[str, object]]]
ExtractEvidenceFn = Callable[[list[dict[str, object]], dict[str, object]], dict[str, object]]


class RewardGraphState(TypedDict, total=False):
    candidate: dict[str, object]
    evidence_bundle: dict[str, object]
    evaluation: dict[str, object]
    actions: list[dict[str, object]]
    collected_documents: list[dict[str, object]]
    round_index: int
    status: str
    errors: list[dict[str, object]]
    started_at: str
    budgets: dict[str, object]
    step_names: list[str]
    graph_version: str


def normalize_evidence_bundle(evidence_bundle: dict[str, object]) -> dict[str, object]:
    return {
        "title": evidence_bundle.get("title"),
        "source_platform": evidence_bundle.get("source_platform"),
        "raw_text_excerpt": evidence_bundle.get("raw_text_excerpt"),
        "reward_snippets": list(evidence_bundle.get("reward_snippets") or []),
        "action_snippets": list(evidence_bundle.get("action_snippets") or []),
        "time_snippets": list(evidence_bundle.get("time_snippets") or []),
        "rule_snippets": list(evidence_bundle.get("rule_snippets") or []),
        "eligibility_snippets": list(evidence_bundle.get("eligibility_snippets") or []),
        "external_links": list(evidence_bundle.get("external_links") or []),
        "priority_links": list(evidence_bundle.get("priority_links") or []),
    }


class RewardInvestigationGraph:
    graph_version = "reward-investigation-v1"

    def __init__(
        self,
        *,
        collector: CollectorFn | None = None,
        extract_evidence: ExtractEvidenceFn | None = None,
        evaluator_client: EvaluatorClient | None = None,
    ):
        self.collector = collector
        self.extract_evidence = extract_evidence
        self.evaluator_client = evaluator_client

    def invoke(self, state: RewardGraphState) -> dict[str, object]:
        working: RewardGraphState = {
            "candidate": dict(state.get("candidate") or {}),
            "evidence_bundle": normalize_evidence_bundle(dict(state.get("evidence_bundle") or {})),
            "actions": list(state.get("actions") or []),
            "collected_documents": list(state.get("collected_documents") or []),
            "round_index": int(state.get("round_index") or 0),
            "status": str(state.get("status") or "running"),
            "errors": list(state.get("errors") or []),
            "started_at": str(state.get("started_at") or datetime.now(UTC).isoformat()),
            "budgets": dict(state.get("budgets") or {}),
            "step_names": [],
            "graph_version": self.graph_version,
        }
        return self._run_linear(working)

    def _mark_step(self, state: RewardGraphState, name: str) -> None:
        state.setdefault("step_names", []).append(name)

    def _run_linear(self, state: RewardGraphState) -> dict[str, object]:
        self._evaluate_baseline(state)
        max_rounds = int(state.get("budgets", {}).get("max_rounds", 2))
        timeout_seconds = int(state.get("budgets", {}).get("timeout_seconds", 10))
        started_at = datetime.fromisoformat(str(state["started_at"]))

        while self._should_investigate(state):
            if (datetime.now(UTC) - started_at).total_seconds() >= timeout_seconds:
                break
            if int(state.get("round_index", 0)) >= max_rounds:
                break
            self._plan_next_actions(state)
            if not state.get("actions"):
                break
            if self.collector and self.extract_evidence:
                self._collect_documents(state)
                self._extract_evidence(state)
                self._evaluate_baseline(state)
                state["round_index"] = int(state.get("round_index", 0)) + 1
                continue
            state["round_index"] = int(state.get("round_index", 0)) + 1
            break

        self._evaluate_llm(state)
        self._finalize(state)
        return dict(state)

    def _evaluate_baseline(self, state: RewardGraphState) -> None:
        self._mark_step(state, "evaluate_baseline")
        state["evaluation"] = evaluate_evidence_bundle(dict(state["evidence_bundle"]))

    def _should_investigate(self, state: RewardGraphState) -> bool:
        self._mark_step(state, "should_investigate")
        return bool(dict(state.get("evaluation") or {}).get("needs_investigation"))

    def _plan_next_actions(self, state: RewardGraphState) -> None:
        self._mark_step(state, "plan_next_actions")
        max_new_links = int(state.get("budgets", {}).get("max_new_links", 3))
        next_actions = decide_next_investigation_actions(dict(state["candidate"]), dict(state["evidence_bundle"]))[:max_new_links]
        planned: list[dict[str, object]] = []
        for action in next_actions:
            action_payload = dict(action)
            action_payload["status"] = "completed" if self.collector else action.get("status", "planned")
            planned.append(action_payload)
        state.setdefault("actions", []).extend(planned)

    def _collect_documents(self, state: RewardGraphState) -> None:
        self._mark_step(state, "collect_documents")
        round_number = int(state.get("round_index", 0)) + 1
        new_documents = self.collector(dict(state["candidate"]), {"actions": list(state.get("actions") or []), "round": round_number}, round_number)
        state.setdefault("collected_documents", []).extend(new_documents)

    def _extract_evidence(self, state: RewardGraphState) -> None:
        self._mark_step(state, "extract_evidence")
        state["evidence_bundle"] = self.extract_evidence(list(state.get("collected_documents") or []), dict(state["evidence_bundle"]))

    def _evaluate_llm(self, state: RewardGraphState) -> None:
        self._mark_step(state, "evaluate_llm")
        try:
            state["evaluation"] = evaluate_with_pydantic_ai(
                dict(state["evidence_bundle"]),
                baseline_result=dict(state.get("evaluation") or {}),
                evaluator_client=self.evaluator_client,
            )
        except Exception as exc:
            state.setdefault("errors", []).append(
                {
                    "step": "evaluate_llm",
                    "failure_type": "model_unavailable",
                    "error_message": str(exc),
                }
            )
            state["status"] = "failed"
            state["evaluation"] = {
                **dict(state.get("evaluation") or {}),
                "source": "model_failed",
                "failure_type": "model_unavailable",
                "error_message": str(exc),
                "needs_investigation": True,
            }

    def _finalize(self, state: RewardGraphState) -> None:
        self._mark_step(state, "finalize")
        if state.get("status") == "failed":
            return
        evaluation = dict(state.get("evaluation") or {})
        state["status"] = "needs_follow_up" if evaluation.get("needs_investigation") else "classified"
