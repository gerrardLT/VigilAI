"""
Verdict synthesis agent for final draft generation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from analysis.providers import AnalysisModelRouter, build_analysis_provider
from analysis.schemas import AnalysisContext, AnalysisSnapshot, ResearchResult, ScreeningResult

logger = logging.getLogger(__name__)


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_verdict_prompt(
    *,
    context: AnalysisContext,
    screening_result: ScreeningResult,
    research_result: ResearchResult,
) -> str:
    return "\n".join(
        [
            "You are the VigilAI verdict agent.",
            "Synthesize screening and bounded research into a final structured draft.",
            "Do not include hidden reasoning or chain-of-thought.",
            "",
            "Activity context:",
            json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2, default=_json_default),
            "",
            "Screening result:",
            json.dumps(screening_result.model_dump(mode="json"), ensure_ascii=False, indent=2, default=_json_default),
            "",
            "Research result:",
            json.dumps(research_result.model_dump(mode="json"), ensure_ascii=False, indent=2, default=_json_default),
        ]
    )


def verdict_from_inputs(
    *,
    context: AnalysisContext,
    screening_result: ScreeningResult,
    research_result: ResearchResult,
) -> AnalysisSnapshot:
    structured = dict(screening_result.structured)
    evidence_summary = research_result.summary
    research_state = research_result.state
    reasons = list(dict.fromkeys([*screening_result.reasons]))
    risk_flags = list(dict.fromkeys([*screening_result.risk_flags]))

    if research_result.state == "completed":
        avg_trust = (
            sum(item.trust_score or 0 for item in research_result.evidence) / len(research_result.evidence)
            if research_result.evidence
            else 0.0
        )
        structured["evidence_count"] = len(research_result.evidence)
        structured["evidence_domains"] = list(research_result.domains_used)
        if avg_trust:
            structured["evidence_trust_score"] = round(avg_trust, 2)
        if avg_trust >= 0.75 and screening_result.status == "watch":
            status = "pass"
        else:
            status = screening_result.status
        reasons.append("Bounded research evidence was reviewed before drafting.")
    elif research_result.state in {"research_unavailable", "insufficient_evidence"}:
        status = "insufficient_evidence"
        risk_flags.append(research_result.state)
        reasons.append("Evidence collection limits prevented a fully supported verdict.")
    else:
        status = screening_result.status

    confidence = screening_result.confidence
    if confidence is None:
        confidence = 0.55
    if research_result.state == "completed":
        confidence = min(0.95, confidence + 0.08)
    elif research_result.state in {"research_unavailable", "insufficient_evidence"}:
        confidence = max(0.25, confidence - 0.18)
    confidence = round(confidence, 2)

    if status == "pass":
        summary = "The opportunity looks strong after screening and available evidence synthesis."
        recommended_action = "approve_after_review"
    elif status == "reject":
        summary = "The opportunity remains too risky after synthesis and should be deprioritized."
        recommended_action = "reject_draft"
    elif status == "insufficient_evidence":
        summary = "The current draft cannot be promoted because supporting evidence is incomplete."
        recommended_action = "request_more_research"
    else:
        summary = "The opportunity is promising but still needs human review before approval."
        recommended_action = "manual_review"

    return AnalysisSnapshot(
        status=status,
        summary=summary,
        reasons=list(dict.fromkeys(reasons)),
        risk_flags=list(dict.fromkeys(risk_flags)),
        recommended_action=recommended_action,
        confidence=confidence,
        structured=structured,
        evidence_summary=evidence_summary,
        research_state=research_state,
        needs_manual_review=True,
        template_id=context.metadata.get("template_id"),
    )


class VerdictAgent:
    def __init__(self, *, provider=None, router: AnalysisModelRouter | None = None) -> None:
        self.provider = provider or build_analysis_provider()
        self.router = router or AnalysisModelRouter()

    def run(
        self,
        *,
        context: AnalysisContext,
        screening_result: ScreeningResult,
        research_result: ResearchResult,
        task_type: str = "verdict",
        budget_tier: str = "default",
    ) -> AnalysisSnapshot:
        route = self.router.select(task_type=task_type, budget_tier=budget_tier)
        heuristic = verdict_from_inputs(
            context=context,
            screening_result=screening_result,
            research_result=research_result,
        )

        try:
            response = self.provider.generate_structured(
                task_type=task_type,
                schema_name="analysis_snapshot",
                json_schema=AnalysisSnapshot.model_json_schema(),
                prompt=build_verdict_prompt(
                    context=context,
                    screening_result=screening_result,
                    research_result=research_result,
                ),
                model=route.primary_model,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Verdict provider failed for activity %s: %s", context.activity_id, exc)
            return heuristic

        merged = heuristic.model_dump(mode="json")
        provider_output = dict(response.output or {})
        structured = dict(heuristic.structured)
        structured.update(provider_output.get("structured") or {})
        merged.update(provider_output)
        merged["structured"] = structured
        merged["risk_flags"] = list(dict.fromkeys([*heuristic.risk_flags, *(provider_output.get("risk_flags") or [])]))
        merged["reasons"] = list(dict.fromkeys([*heuristic.reasons, *(provider_output.get("reasons") or [])]))

        try:
            return AnalysisSnapshot.model_validate(merged)
        except ValidationError as exc:
            logger.warning("Verdict provider returned invalid payload for activity %s: %s", context.activity_id, exc)
            return heuristic
