"""Trace and evaluation helpers for reward-opportunity agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
import uuid


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TraceRecorder:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.started_at = _now_iso()
        self.steps: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []

    def record_step(self, name: str, input_payload: dict[str, Any], output_payload: dict[str, Any], *, latency_ms: int = 0) -> None:
        self.steps.append(
            {
                "name": name,
                "input": input_payload,
                "output": output_payload,
                "latency_ms": latency_ms,
                "recorded_at": _now_iso(),
            }
        )

    def record_tool_call(self, tool_name: str, tool_input: dict[str, Any], tool_output: dict[str, Any], *, latency_ms: int = 0) -> None:
        self.tool_calls.append(
            {
                "tool_name": tool_name,
                "input": tool_input,
                "output": tool_output,
                "latency_ms": latency_ms,
                "failure_type": tool_output.get("failure_type") if isinstance(tool_output, dict) else None,
                "recorded_at": _now_iso(),
            }
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "steps": list(self.steps),
            "tool_calls": list(self.tool_calls),
        }

    def flush_to_langsmith(self, *, project_name: str = "reward-opportunity", client: Any | None = None) -> dict[str, Any]:
        if client is None:
            try:
                from langsmith import Client
            except Exception as exc:
                return {"ok": False, "failure_type": "unavailable", "error_message": str(exc)}
            client = Client()

        langsmith_run_id = uuid.uuid4()
        payload = self.to_payload()
        try:
            client.create_run(
                id=langsmith_run_id,
                name=f"reward-agent:{self.run_id}",
                run_type="chain",
                project_name=project_name,
                inputs={"run_id": self.run_id, "started_at": self.started_at},
            )
            client.update_run(
                langsmith_run_id,
                outputs=payload,
                events=[
                    {"name": "step", "time": step["recorded_at"], "kwargs": step}
                    for step in self.steps
                ]
                + [
                    {"name": "tool_call", "time": call["recorded_at"], "kwargs": call}
                    for call in self.tool_calls
                ],
            )
        except Exception as exc:
            return {"ok": False, "failure_type": "tool_error", "error_message": str(exc)}
        return {"ok": True, "run_id": str(langsmith_run_id), "project_name": project_name}


@dataclass(frozen=True)
class EvaluationMetrics:
    precision: float
    recall: float
    evidence_completeness: float
    duplicate_merge_accuracy: float = 0.0
    expired_opportunity_detection: float = 0.0
    tool_failure_rate: float = 0.0
    browser_success_rate: float = 0.0
    cost_per_accepted_opportunity: float = 0.0
    latency_per_investigation: float = 0.0

    @classmethod
    def from_cases(cls, cases: list[dict[str, Any]]) -> "EvaluationMetrics":
        true_positive = sum(1 for case in cases if case.get("expected") is True and case.get("actual") is True)
        false_positive = sum(1 for case in cases if case.get("expected") is False and case.get("actual") is True)
        false_negative = sum(1 for case in cases if case.get("expected") is True and case.get("actual") is False)
        complete = sum(1 for case in cases if case.get("evidence_complete") is True)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        evidence_completeness = complete / len(cases) if cases else 0.0
        return cls(precision=precision, recall=recall, evidence_completeness=evidence_completeness)
