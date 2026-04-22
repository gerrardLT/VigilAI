"""
Deterministic safety gate applied after verdict generation.
"""

from __future__ import annotations

from analysis.policies import SafetyPolicy
from analysis.rule_engine import derive_safety_gate_decision
from analysis.schemas import AnalysisContext, AnalysisSnapshot


class AnalysisSafetyGate:
    def apply(
        self,
        *,
        draft: AnalysisSnapshot,
        context: AnalysisContext,
        policy: SafetyPolicy,
    ) -> AnalysisSnapshot:
        gated = draft.model_copy(deep=True)
        decision = derive_safety_gate_decision(
            structured=gated.structured,
            source_health=context.source_health,
        )

        if decision.force_status == "reject":
            gated.status = "reject"
        elif decision.force_status == "watch" and gated.status == "pass":
            gated.status = "watch"

        gated.risk_flags = list(dict.fromkeys([*gated.risk_flags, *decision.risk_flags]))
        gated.reasons = list(dict.fromkeys([*gated.reasons, *decision.reasons]))

        if policy.writeback_mode == "human_review" or decision.manual_review_required:
            gated.needs_manual_review = True

        if gated.status != draft.status and gated.recommended_action == "approve_after_review":
            gated.recommended_action = "manual_review"

        return gated
