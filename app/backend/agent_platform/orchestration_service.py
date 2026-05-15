"""Tool-orchestration planning for shared agent sessions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .models import AgentSession, AgentExecutionPlanStep
from .safety_service import SafetyDecision
from .tool_router import ToolRouter, ToolSelection


class ExecutionPlanDraft(BaseModel):
    mode: str = "allow"
    summary: str
    requested_steps: list[AgentExecutionPlanStep] = Field(default_factory=list)
    runnable_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    reasoning: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class OrchestrationService:
    def __init__(self, tool_router: ToolRouter | None = None) -> None:
        self.tool_router = tool_router or ToolRouter()

    def build_plan(
        self,
        *,
        session: AgentSession,
        user_message: str,
        tool_names: list[str],
        safety: SafetyDecision,
    ) -> ExecutionPlanDraft:
        selections = self.tool_router.explain_selection(
            domain_type=session.domain_type,
            user_message=user_message,
            tool_names=tool_names,
        )
        requested_steps = [self._to_plan_step(selection, safety) for selection in selections]
        summary = self._build_summary(session, requested_steps, safety)
        reasoning = self._build_reasoning(session, requested_steps, safety)

        return ExecutionPlanDraft(
            mode=safety.mode,
            summary=summary,
            requested_steps=requested_steps,
            runnable_tools=safety.safe_tool_names,
            blocked_tools=safety.blocked_tool_names,
            risk_flags=safety.risk_flags,
            reasoning=reasoning,
            payload={
                "domain_type": session.domain_type,
                "requested_tool_count": len(requested_steps),
                "runnable_tool_count": len(safety.safe_tool_names),
                "blocked_tool_count": len(safety.blocked_tool_names),
            },
        )

    def _to_plan_step(
        self,
        selection: ToolSelection,
        safety: SafetyDecision,
    ) -> AgentExecutionPlanStep:
        policy = safety.tool_policies.get(selection.tool_name, {})
        return AgentExecutionPlanStep(
            tool_name=selection.tool_name,
            intent=selection.intent,
            rationale=selection.rationale,
            priority=selection.priority,
            stage=selection.stage,
            access_mode=str(policy.get("access_mode", selection.access_mode)),
            policy_decision=str(policy.get("decision", "allow")),
            metadata={
                **selection.metadata,
                "policy_reason": policy.get("reason"),
                "data_scope": policy.get("data_scope"),
                "risk_tier": policy.get("risk_tier"),
            },
        )

    @staticmethod
    def _build_summary(
        session: AgentSession,
        requested_steps: list[AgentExecutionPlanStep],
        safety: SafetyDecision,
    ) -> str:
        if not requested_steps:
            return f"No concrete tool plan was produced for domain {session.domain_type}."

        tool_names = ", ".join(step.tool_name for step in requested_steps)
        if safety.mode == "block":
            return f"Blocked orchestration plan for {session.domain_type}: {tool_names}."
        if safety.mode == "guarded":
            return f"Guarded orchestration plan for {session.domain_type}: {tool_names}."
        return f"Prepared orchestration plan for {session.domain_type}: {tool_names}."

    @staticmethod
    def _build_reasoning(
        session: AgentSession,
        requested_steps: list[AgentExecutionPlanStep],
        safety: SafetyDecision,
    ) -> str | None:
        if not requested_steps:
            return None

        step_fragments = [
            f"{step.tool_name} -> {step.intent} ({step.policy_decision})"
            for step in requested_steps
        ]
        if safety.risk_flags:
            return (
                f"The {session.domain_type} session produced the following tool route: "
                + "; ".join(step_fragments)
                + f". Risk flags: {', '.join(safety.risk_flags)}."
            )
        return (
            f"The {session.domain_type} session produced the following tool route: "
            + "; ".join(step_fragments)
            + "."
        )
