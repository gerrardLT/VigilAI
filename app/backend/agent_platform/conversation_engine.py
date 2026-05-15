"""Conversation engine for shared agent sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .artifact_service import ArtifactDraft
from .orchestration_service import ExecutionPlanDraft, OrchestrationService
from .models import AgentMemory, AgentReflection, AgentSession, AgentTurn
from .safety_service import AgentSafetyService, SafetyDecision
from .session_intelligence import InsightDraft, SessionIntelligenceService, SessionStateDraft, ThinkingStepDraft
from .tool_router import ToolRouter


class ConversationReply(BaseModel):
    assistant_turn: str
    next_state: str = "active"
    artifacts: list[ArtifactDraft] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    execution_plan: ExecutionPlanDraft
    session_state: SessionStateDraft = Field(default_factory=SessionStateDraft)
    insights: list[InsightDraft] = Field(default_factory=list)
    thinking_steps: list[ThinkingStepDraft] = Field(default_factory=list)


class ConversationEngine:
    def __init__(
        self,
        tool_router: ToolRouter | None = None,
        orchestration_service: OrchestrationService | None = None,
        intelligence_service: SessionIntelligenceService | None = None,
        safety_service: AgentSafetyService | None = None,
    ):
        self.tool_router = tool_router or ToolRouter()
        self.orchestration_service = orchestration_service or OrchestrationService(tool_router=self.tool_router)
        self.intelligence_service = intelligence_service or SessionIntelligenceService()
        self.safety_service = safety_service or AgentSafetyService()

    def reply(
        self,
        *,
        session: AgentSession,
        user_turn: AgentTurn,
        recalled_memories: list[AgentMemory] | None = None,
        recalled_reflections: list[AgentReflection] | None = None,
    ) -> ConversationReply:
        recalled_memories = recalled_memories or []
        recalled_reflections = recalled_reflections or []
        tool_names = self.tool_router.resolve_tools(
            domain_type=session.domain_type,
            user_message=user_turn.content,
        )
        safety = self.safety_service.evaluate(
            session=session,
            user_message=user_turn.content,
            tool_names=tool_names,
        )
        execution_plan = self.orchestration_service.build_plan(
            session=session,
            user_message=user_turn.content,
            tool_names=tool_names,
            safety=safety,
        )
        if not safety.allowed:
            blocked_tool_names = safety.blocked_tool_names or tool_names
            blocked_tool_calls = [
                {
                    "tool_name": tool_name,
                    "status": "blocked",
                    "risk_flags": safety.risk_flags,
                }
                for tool_name in blocked_tool_names
            ]
            assistant_text = safety.blocked_reason or "I cannot continue with that request."
            session_state, insights, thinking_steps = self.intelligence_service.build(
                session=session,
                user_turn=user_turn,
                assistant_turn=assistant_text,
                tool_calls=blocked_tool_calls,
                tool_results={},
            )
            thinking_steps.insert(
                0,
                ThinkingStepDraft(
                    phase="orchestration",
                    summary=execution_plan.summary,
                    payload=execution_plan.model_dump(mode="json"),
                ),
            )
            thinking_steps.insert(
                0,
                ThinkingStepDraft(
                    phase="safety",
                    summary="Blocked the turn because it triggered safety policy checks.",
                    payload={"risk_flags": safety.risk_flags},
                ),
            )
            insights.append(
                InsightDraft(
                    insight_type="safety",
                    content="The turn was blocked by safety policy checks.",
                    importance=0.95,
                    payload={"risk_flags": safety.risk_flags},
                )
            )
            return ConversationReply(
                assistant_turn=assistant_text,
                next_state="active",
                artifacts=[
                    ArtifactDraft(
                        artifact_type="safety",
                        title="Safety Guardrail",
                        content=assistant_text,
                        payload={"risk_flags": safety.risk_flags},
                    ),
                    self._build_orchestration_artifact(execution_plan),
                ],
                tool_calls=blocked_tool_calls,
                execution_plan=execution_plan,
                session_state=session_state,
                insights=insights,
                thinking_steps=thinking_steps,
            )

        tool_calls, tool_results = self._run_tools(
            session=session,
            user_turn=user_turn,
            tool_names=tool_names,
            safety=safety,
        )

        artifacts = [self._build_checklist_artifact(session.domain_type)]
        artifacts.append(self._build_orchestration_artifact(execution_plan))
        context_artifact = self._build_context_artifact(recalled_memories, recalled_reflections)
        if context_artifact is not None:
            artifacts.append(context_artifact)
        if safety.mode == "guarded" and safety.blocked_reason:
            artifacts.append(
                ArtifactDraft(
                    artifact_type="safety",
                    title="Safety Guardrail",
                    content=safety.blocked_reason,
                    payload={
                        "risk_flags": safety.risk_flags,
                        "blocked_tool_names": safety.blocked_tool_names,
                        "mode": safety.mode,
                    },
                )
            )
        artifacts.extend(self._build_domain_artifacts(session.domain_type, tool_results))
        assistant_text = self._build_assistant_text(
            session.domain_type,
            tool_results,
            recalled_memories=recalled_memories,
            recalled_reflections=recalled_reflections,
            safety=safety,
        )
        session_state, insights, thinking_steps = self.intelligence_service.build(
            session=session,
            user_turn=user_turn,
            assistant_turn=assistant_text,
            tool_calls=tool_calls,
            tool_results=tool_results,
        )
        if recalled_memories or recalled_reflections:
            thinking_steps.insert(
                0,
                ThinkingStepDraft(
                    phase="orchestration",
                    summary=execution_plan.summary,
                    payload=execution_plan.model_dump(mode="json"),
                ),
            )
            thinking_steps.insert(
                0,
                ThinkingStepDraft(
                    phase="memory_recall",
                    summary=(
                        f"Loaded {len(recalled_memories)} memory item(s) and "
                        f"{len(recalled_reflections)} reflection item(s) before tool execution."
                    ),
                    payload={
                        "memory_count": len(recalled_memories),
                        "reflection_count": len(recalled_reflections),
                    },
                ),
            )
        if safety.mode == "guarded":
            thinking_steps.insert(
                0,
                ThinkingStepDraft(
                    phase="safety",
                    summary="Executed the turn with safety guardrails and restricted it to compliant read-only tools.",
                    payload={
                        "risk_flags": safety.risk_flags,
                        "blocked_tool_names": safety.blocked_tool_names,
                    },
                ),
            )
            insights.append(
                InsightDraft(
                    insight_type="safety",
                    content="The turn was executed with safety guardrails due to sensitive request phrasing.",
                    importance=0.75,
                    payload={
                        "risk_flags": safety.risk_flags,
                        "blocked_tool_names": safety.blocked_tool_names,
                    },
                )
            )

        return ConversationReply(
            assistant_turn=assistant_text,
            next_state="active",
            artifacts=artifacts,
            tool_calls=tool_calls,
            execution_plan=execution_plan,
            session_state=session_state,
            insights=insights,
            thinking_steps=thinking_steps,
        )

    def _build_orchestration_artifact(self, execution_plan: ExecutionPlanDraft) -> ArtifactDraft:
        lines = [execution_plan.summary]
        for step in execution_plan.requested_steps:
            lines.append(
                " - "
                + f"{step.tool_name}: {step.intent} | {step.policy_decision} | {step.rationale}"
            )
        if execution_plan.risk_flags:
            lines.append("Risk flags: " + ", ".join(execution_plan.risk_flags))
        return ArtifactDraft(
            artifact_type="orchestration",
            title="Execution Plan",
            content="\n".join(lines),
            payload=execution_plan.model_dump(mode="json"),
        )

    def _run_tools(
        self,
        *,
        session: AgentSession,
        user_turn: AgentTurn,
        tool_names: list[str],
        safety: SafetyDecision,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        tool_calls: list[dict[str, Any]] = []
        tool_results: dict[str, dict[str, Any]] = {}

        for tool_name in safety.blocked_tool_names:
            tool_calls.append(
                {
                    "tool_name": tool_name,
                    "status": "blocked",
                    "risk_flags": safety.risk_flags,
                }
            )

        runnable_tool_names = safety.safe_tool_names or tool_names
        for tool_name in runnable_tool_names:
            tool = self.tool_router.get_tool(tool_name)
            if tool is None:
                tool_calls.append({"tool_name": tool_name, "status": "planned"})
                continue

            try:
                result = tool.run(session=session, user_message=user_turn.content)
            except Exception as exc:
                tool_calls.append({"tool_name": tool_name, "status": "failed", "error": str(exc)})
                continue

            tool_results[tool_name] = result
            tool_calls.append(
                {
                    "tool_name": tool_name,
                    "status": "completed",
                    "result_summary": self._build_tool_call_summary(tool_name, result),
                }
            )

        return tool_calls, tool_results

    def _build_context_artifact(
        self,
        recalled_memories: list[AgentMemory],
        recalled_reflections: list[AgentReflection],
    ) -> ArtifactDraft | None:
        if not recalled_memories and not recalled_reflections:
            return None

        lines: list[str] = []
        for memory in recalled_memories[:3]:
            lines.append(f"Memory: {memory.content}")
        for reflection in recalled_reflections[:2]:
            line = f"Reflection: {reflection.summary}"
            if reflection.action_item:
                line += f" | Action: {reflection.action_item}"
            lines.append(line)
        return ArtifactDraft(
            artifact_type="context",
            title="Recalled Context",
            content="\n".join(lines),
            payload={
                "memory_ids": [item.id for item in recalled_memories[:3]],
                "reflection_ids": [item.id for item in recalled_reflections[:2]],
            },
        )

    def _build_tool_call_summary(self, tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "opportunity_search":
            return {"item_count": len(result.get("items") or [])}
        if tool_name in {"opportunity_explain", "opportunity_next_action"}:
            return {
                "matched": bool(result.get("matched")),
                "activity_id": result.get("activity_id"),
            }
        if tool_name in {"selection_query", "selection_compare"}:
            return {
                "job_id": result.get("job", {}).get("id"),
                "item_count": len(result.get("shortlist") or result.get("items") or []),
            }
        return {}

    def _build_checklist_artifact(self, domain_type: str) -> ArtifactDraft:
        if domain_type == "product_selection":
            return ArtifactDraft(
                artifact_type="checklist",
                title="Selection Intake Checklist",
                content="Add target platform, budget range, sourcing model, and expected margin.",
                payload={"domain_type": domain_type},
            )

        if domain_type == "opportunity":
            return ArtifactDraft(
                artifact_type="checklist",
                title="Opportunity Intake Checklist",
                content="Add budget, time window, target category, and execution constraints.",
                payload={"domain_type": domain_type},
            )

        return ArtifactDraft(
            artifact_type="checklist",
            title="Conversation Intake Checklist",
            content="Add the goal, hard constraints, timing, and expected output format.",
            payload={"domain_type": domain_type},
        )

    def _build_domain_artifacts(
        self,
        domain_type: str,
        tool_results: dict[str, dict[str, Any]],
    ) -> list[ArtifactDraft]:
        if domain_type == "opportunity":
            return self._build_opportunity_artifacts(tool_results)
        if domain_type == "product_selection":
            return self._build_product_selection_artifacts(tool_results)
        return []

    def _build_opportunity_artifacts(
        self,
        tool_results: dict[str, dict[str, Any]],
    ) -> list[ArtifactDraft]:
        artifacts: list[ArtifactDraft] = []

        search_result = tool_results.get("opportunity_search")
        if search_result and search_result.get("items"):
            artifacts.append(
                ArtifactDraft(
                    artifact_type="shortlist",
                    title="Opportunity Shortlist",
                    content=self._format_opportunity_shortlist(search_result["items"]),
                    payload=search_result,
                )
            )

        explain_result = tool_results.get("opportunity_explain")
        if explain_result and explain_result.get("matched"):
            artifacts.append(
                ArtifactDraft(
                    artifact_type="explanation",
                    title="Opportunity Assessment",
                    content=self._format_opportunity_explanation(explain_result),
                    payload=explain_result,
                )
            )

        next_action_result = tool_results.get("opportunity_next_action")
        if next_action_result and next_action_result.get("matched"):
            artifacts.append(
                ArtifactDraft(
                    artifact_type="next_action",
                    title="Recommended Next Action",
                    content=self._format_opportunity_next_action(next_action_result),
                    payload=next_action_result,
                )
            )

        return artifacts

    def _build_product_selection_artifacts(
        self,
        tool_results: dict[str, dict[str, Any]],
    ) -> list[ArtifactDraft]:
        artifacts: list[ArtifactDraft] = []
        shortlist_result = tool_results.get("selection_query") or tool_results.get("selection_compare")
        if shortlist_result and shortlist_result.get("shortlist"):
            artifacts.append(
                ArtifactDraft(
                    artifact_type="shortlist",
                    title="Selection Shortlist",
                    content=self._format_selection_shortlist(shortlist_result["shortlist"]),
                    payload=shortlist_result,
                )
            )

        compare_result = tool_results.get("selection_compare")
        if compare_result and compare_result.get("compare_rows"):
            artifacts.append(
                ArtifactDraft(
                    artifact_type="comparison",
                    title="Cross-Platform Comparison",
                    content=self._format_selection_comparison(compare_result["compare_rows"]),
                    payload=compare_result,
                )
            )

        return artifacts

    def _build_assistant_text(
        self,
        domain_type: str,
        tool_results: dict[str, dict[str, Any]],
        *,
        recalled_memories: list[AgentMemory],
        recalled_reflections: list[AgentReflection],
        safety: SafetyDecision,
    ) -> str:
        sections: list[str] = []
        if recalled_memories or recalled_reflections:
            sections.append(self._build_context_text(recalled_memories, recalled_reflections))
        if safety.mode == "guarded" and safety.blocked_reason:
            sections.append(safety.blocked_reason)
        if domain_type == "product_selection":
            sections.append(self._build_product_selection_text(tool_results))
        elif domain_type == "opportunity":
            sections.append(self._build_opportunity_text(tool_results))
        else:
            sections.append("I can help scope this decision. Tell me the goal, constraints, and expected output.")
        return "\n\n".join(section for section in sections if section)

    def _build_context_text(
        self,
        recalled_memories: list[AgentMemory],
        recalled_reflections: list[AgentReflection],
    ) -> str:
        lines = ["Context carried forward:"]
        for memory in recalled_memories[:2]:
            lines.append(f"- Memory: {memory.content}")
        for reflection in recalled_reflections[:1]:
            line = f"- Reflection: {reflection.summary}"
            if reflection.action_item:
                line += f" | Action: {reflection.action_item}"
            lines.append(line)
        return "\n".join(lines)

    def _build_opportunity_text(self, tool_results: dict[str, dict[str, Any]]) -> str:
        parts = [
            "I scoped an initial opportunity pass. Tell me whether you care most about reward size, deadline, or solo execution."
        ]

        search_result = tool_results.get("opportunity_search")
        if search_result:
            items = search_result.get("items") or []
            if items:
                parts.append("First shortlist:\n" + self._format_opportunity_shortlist(items))
            else:
                parts.append(
                    "I did not find a strong direct match yet. Add a tighter category, reward size, or deadline filter."
                )

        explain_result = tool_results.get("opportunity_explain")
        if explain_result and explain_result.get("matched"):
            parts.append(self._format_opportunity_explanation(explain_result))

        next_action_result = tool_results.get("opportunity_next_action")
        if next_action_result and next_action_result.get("matched"):
            parts.append(self._format_opportunity_next_action(next_action_result))

        return "\n\n".join(parts)

    def _build_product_selection_text(self, tool_results: dict[str, dict[str, Any]]) -> str:
        parts = [
            "I started a product-selection pass. Tell me whether margin, sell-through speed, or after-sales risk matters most."
        ]

        shortlist_result = tool_results.get("selection_query") or tool_results.get("selection_compare")
        if shortlist_result:
            shortlist = shortlist_result.get("shortlist") or []
            if shortlist:
                parts.append("First shortlist:\n" + self._format_selection_shortlist(shortlist))
            else:
                parts.append(
                    "I did not find a strong shortlist yet. Add a tighter keyword, platform scope, or price band."
                )

        compare_result = tool_results.get("selection_compare")
        if compare_result and compare_result.get("compare_rows"):
            parts.append(self._format_selection_comparison(compare_result["compare_rows"]))

        return "\n\n".join(parts)

    def _format_opportunity_shortlist(self, items: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            fragments = [f"{index}. {item['title']}"]
            if item.get("category"):
                fragments.append(f"Category {item['category']}")
            if item.get("score") is not None:
                fragments.append(f"Score {item['score']}")
            deadline = self._format_deadline(item.get("deadline"))
            if deadline:
                fragments.append(f"Deadline {deadline}")
            prize = self._format_prize(item.get("prize"))
            if prize:
                fragments.append(f"Prize {prize}")
            lines.append(" | ".join(fragments))
        return "\n".join(lines)

    def _format_opportunity_explanation(self, explain_result: dict[str, Any]) -> str:
        activity = explain_result.get("activity") or {}
        analysis = explain_result.get("analysis") or {}
        lines = [f"Opportunity assessment: {activity.get('title', '')}".strip()]
        if analysis.get("summary"):
            lines.append(str(analysis["summary"]))
        reasons = analysis.get("reasons") or []
        if reasons:
            lines.append("Reasons: " + "; ".join(str(reason) for reason in reasons[:3]))
        risk_flags = analysis.get("risk_flags") or []
        if risk_flags:
            lines.append("Risks: " + "; ".join(str(flag) for flag in risk_flags[:3]))
        if analysis.get("recommended_action"):
            lines.append("Recommended action: " + str(analysis["recommended_action"]))
        return "\n".join(lines)

    def _format_opportunity_next_action(self, next_action_result: dict[str, Any]) -> str:
        lines = [
            f"Recommended next action: {next_action_result.get('next_action', '')}".strip(),
            (
                f"Urgency: {next_action_result.get('urgency', 'medium')} | "
                f"Tracking: {next_action_result.get('tracking_status', 'saved')}"
            ),
        ]
        deadline = self._format_deadline(next_action_result.get("deadline"))
        if deadline:
            lines.append(f"Deadline: {deadline}")
        if next_action_result.get("notes"):
            lines.append("Notes: " + str(next_action_result["notes"]))
        reasons = next_action_result.get("analysis_reasons") or []
        if reasons:
            lines.append("Basis: " + "; ".join(str(reason) for reason in reasons[:2]))
        return "\n".join(lines)

    def _format_selection_shortlist(self, items: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            fragments = [
                f"{index}. {item['title']}",
                f"Platform {item.get('platform')}",
                f"Opportunity {item.get('opportunity_score')}",
                f"Confidence {item.get('confidence_score')}",
            ]
            if item.get("recommended_action"):
                fragments.append(f"Recommended {item['recommended_action']}")
            lines.append(" | ".join(str(fragment) for fragment in fragments))
        return "\n".join(lines)

    def _format_selection_comparison(self, compare_rows: list[dict[str, Any]]) -> str:
        lines = ["Cross-platform comparison:"]
        for row in compare_rows:
            lines.append(
                " - "
                + f"{row['platform']}: {row['title']} | Opportunity {row['opportunity_score']} | "
                + f"Confidence {row['confidence_score']} | Recommended {row.get('recommended_action') or 'N/A'}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_prize(prize: dict[str, Any] | None) -> str | None:
        if not prize:
            return None
        amount = prize.get("amount")
        currency = prize.get("currency") or ""
        description = prize.get("description")
        if amount is not None:
            return f"{amount:g} {currency}".strip()
        if description:
            return str(description)
        return None

    @staticmethod
    def _format_deadline(deadline_raw: str | None) -> str | None:
        if not deadline_raw:
            return None
        try:
            return datetime.fromisoformat(deadline_raw).date().isoformat()
        except ValueError:
            return deadline_raw
