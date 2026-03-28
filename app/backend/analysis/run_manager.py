"""
Single-item orchestration for agent-analysis runs.
"""

from __future__ import annotations

from datetime import datetime
import logging

from analysis.context_builder import build_analysis_context
from analysis.policies import BudgetPolicy, ResearchPolicy, SafetyPolicy
from analysis.research_agent import ResearchAgent
from analysis.safety_gate import AnalysisSafetyGate
from analysis.screening_agent import ScreeningAgent
from analysis.template_compiler import compile_analysis_template
from analysis.verdict_agent import VerdictAgent

logger = logging.getLogger(__name__)


class AnalysisRunManager:
    def __init__(
        self,
        *,
        data_manager,
        screening_agent: ScreeningAgent | None = None,
        research_agent: ResearchAgent | None = None,
        verdict_agent: VerdictAgent | None = None,
        safety_gate: AnalysisSafetyGate | None = None,
    ) -> None:
        self.data_manager = data_manager
        self.screening_agent = screening_agent or ScreeningAgent()
        self.research_agent = research_agent or ResearchAgent()
        self.verdict_agent = verdict_agent or VerdictAgent()
        self.safety_gate = safety_gate or AnalysisSafetyGate()

    def _resolve_template(self, template_id: str | None) -> dict:
        template = (
            self.data_manager.get_analysis_template_by_id(template_id)
            if template_id
            else self.data_manager.get_default_analysis_template()
        )
        if template is None:
            raise ValueError("Analysis template not found")
        if not template.get("compiled_policy"):
            template["compiled_policy"] = compile_analysis_template(template).model_dump(mode="json")
        return template

    def run_single_job(
        self,
        *,
        activity_id: str,
        template_id: str | None = None,
        requested_by: str | None = None,
        trigger_type: str = "manual",
    ) -> dict:
        activity = self.data_manager.get_activity_by_id(activity_id)
        if activity is None:
            raise ValueError(f"Activity {activity_id} not found")

        template = self._resolve_template(template_id)
        compiled_policy = template["compiled_policy"]
        budget_policy = BudgetPolicy.model_validate(compiled_policy["budget_policy"])
        research_policy = ResearchPolicy.model_validate(compiled_policy["research_policy"])
        safety_policy = SafetyPolicy.model_validate(compiled_policy["safety_policy"])
        single_route = compiled_policy["route_policy"]["single_item"]
        screening_route = self.screening_agent.router.select(
            task_type="screening",
            budget_tier=single_route.get("model_tier") or "default",
        )
        verdict_route = self.verdict_agent.router.select(
            task_type=single_route.get("task_type") or "verdict",
            budget_tier=single_route.get("model_tier") or "default",
        )

        job = self.data_manager.create_analysis_job(
            trigger_type=trigger_type,
            scope_type="single",
            template_id=template["id"],
            route_policy=compiled_policy["route_policy"],
            budget_policy=budget_policy.model_dump(mode="json"),
            status="running",
            requested_by=requested_by,
        )
        item = self.data_manager.create_analysis_job_item(
            job_id=job.id,
            activity_id=activity.id,
            status="running",
            needs_research=False,
            screening_model=screening_route.primary_model,
            verdict_model=verdict_route.primary_model,
        )

        try:
            with self.data_manager._get_connection() as conn:
                source_row = self.data_manager._source_snapshot(conn, activity.source_id)
            context = build_analysis_context(activity, source_row, current_snapshot=None)
            context.metadata["template_id"] = template["id"]
            context.metadata["job_id"] = job.id

            screening = self.screening_agent.run(
                context,
                budget_tier=single_route.get("model_tier") or "default",
            )
            self.data_manager.create_analysis_step(
                job_item_id=item.id,
                step_type="screening",
                step_status="completed",
                input_digest=f"activity:{activity.id}",
                output_payload={
                    "result": screening.model_dump(mode="json"),
                    "route": screening_route.model_dump(mode="json"),
                },
                model_name=screening.model_name or screening_route.primary_model,
            )

            research = self.research_agent.run(
                context=context,
                screening_result=screening,
                policy=research_policy,
            )
            self.data_manager.create_analysis_step(
                job_item_id=item.id,
                step_type="research",
                step_status="completed" if research.state in {"completed", "not_requested"} else "warning",
                input_digest=f"screening:{item.id}",
                output_payload=research.model_dump(mode="json"),
                model_name="bounded-research-fetcher",
            )
            self.data_manager.replace_analysis_evidence(item.id, research.evidence)

            verdict = self.verdict_agent.run(
                context=context,
                screening_result=screening,
                research_result=research,
                task_type=single_route.get("task_type") or "verdict",
                budget_tier=single_route.get("model_tier") or "default",
            )
            verdict = verdict.model_copy(
                update={
                    "template_id": template["id"],
                    "current_run_id": job.id,
                    "updated_at": datetime.now(),
                }
            )
            self.data_manager.create_analysis_step(
                job_item_id=item.id,
                step_type="verdict",
                step_status="completed",
                input_digest=f"research:{item.id}",
                output_payload={
                    "draft": verdict.model_dump(mode="json"),
                    "route": verdict_route.model_dump(mode="json"),
                },
                model_name=verdict_route.primary_model,
            )

            gated = self.safety_gate.apply(
                draft=verdict,
                context=context,
                policy=safety_policy,
            ).model_copy(
                update={
                    "template_id": template["id"],
                    "current_run_id": job.id,
                    "updated_at": datetime.now(),
                }
            )
            self.data_manager.create_analysis_step(
                job_item_id=item.id,
                step_type="safety",
                step_status="completed",
                input_digest=f"verdict:{item.id}",
                output_payload={
                    "draft": gated.model_dump(mode="json"),
                    "policy": safety_policy.model_dump(mode="json"),
                },
                model_name="deterministic-safety-gate",
            )

            self.data_manager.update_analysis_job_item(
                item.id,
                status="completed",
                needs_research=bool(screening.structured.get("should_deep_research")),
                final_draft_status=gated.status,
                screening_model=screening_route.primary_model,
                research_model="bounded-research-fetcher" if research.state != "not_requested" else None,
                verdict_model=verdict_route.primary_model,
            )
            self.data_manager.update_analysis_job(job.id, status="completed")
        except Exception as exc:
            logger.exception("Agent-analysis single job failed for activity %s", activity.id)
            self.data_manager.create_analysis_step(
                job_item_id=item.id,
                step_type="orchestration",
                step_status="failed",
                input_digest=f"activity:{activity.id}",
                output_payload={"error": str(exc)},
                model_name="run-manager",
            )
            self.data_manager.update_analysis_job_item(item.id, status="failed")
            self.data_manager.update_analysis_job(job.id, status="failed")
            raise

        detail = self.data_manager.get_analysis_job_detail(job.id)
        if detail is None:
            raise ValueError(f"Analysis job {job.id} not found after execution")
        return detail
