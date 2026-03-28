"""
Single-item and batch orchestration for agent-analysis runs.
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

    def _prepare_policy_bundle(self, template_id: str | None) -> tuple[dict, BudgetPolicy, ResearchPolicy, SafetyPolicy]:
        template = self._resolve_template(template_id)
        compiled_policy = template["compiled_policy"]
        return (
            template,
            BudgetPolicy.model_validate(compiled_policy["budget_policy"]),
            ResearchPolicy.model_validate(compiled_policy["research_policy"]),
            SafetyPolicy.model_validate(compiled_policy["safety_policy"]),
        )

    def _execute_activity_pipeline(
        self,
        *,
        job,
        activity,
        template: dict,
        route_target: dict,
        research_policy: ResearchPolicy,
        safety_policy: SafetyPolicy,
    ) -> dict:
        screening_route = self.screening_agent.router.select(
            task_type="screening",
            budget_tier=route_target.get("model_tier") or "default",
        )
        verdict_task_type = route_target.get("task_type") or "verdict"
        if verdict_task_type == "screening":
            verdict_task_type = "verdict"
        verdict_route = self.verdict_agent.router.select(
            task_type=verdict_task_type,
            budget_tier=route_target.get("model_tier") or "default",
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
                budget_tier=route_target.get("model_tier") or "default",
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
                task_type=verdict_task_type,
                budget_tier=route_target.get("model_tier") or "default",
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
        except Exception as exc:
            logger.exception("Agent-analysis item pipeline failed for activity %s", activity.id)
            self.data_manager.create_analysis_step(
                job_item_id=item.id,
                step_type="orchestration",
                step_status="failed",
                input_digest=f"activity:{activity.id}",
                output_payload={"error": str(exc)},
                model_name="run-manager",
            )
            self.data_manager.update_analysis_job_item(item.id, status="failed")
            raise

        detail = self.data_manager.get_analysis_item_detail(item.id)
        if detail is None:
            raise ValueError(f"Analysis item {item.id} not found after execution")
        return detail

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

        template, budget_policy, research_policy, safety_policy = self._prepare_policy_bundle(template_id)
        compiled_policy = template["compiled_policy"]
        route_target = compiled_policy["route_policy"]["single_item"]

        job = self.data_manager.create_analysis_job(
            trigger_type=trigger_type,
            scope_type="single",
            template_id=template["id"],
            route_policy=compiled_policy["route_policy"],
            budget_policy=budget_policy.model_dump(mode="json"),
            status="running",
            requested_by=requested_by,
        )
        try:
            self._execute_activity_pipeline(
                job=job,
                activity=activity,
                template=template,
                route_target=route_target,
                research_policy=research_policy,
                safety_policy=safety_policy,
            )
            self.data_manager.update_analysis_job(job.id, status="completed")
        except Exception:
            self.data_manager.update_analysis_job(job.id, status="failed")
            raise

        detail = self.data_manager.get_analysis_job_detail(job.id)
        if detail is None:
            raise ValueError(f"Analysis job {job.id} not found after execution")
        return detail

    def run_batch_job(
        self,
        *,
        template_id: str | None = None,
        requested_by: str | None = None,
        trigger_type: str = "scheduled",
        activity_ids: list[str] | None = None,
        max_items: int = 25,
        stale_before_hours: int = 72,
    ) -> dict:
        template, budget_policy, research_policy, safety_policy = self._prepare_policy_bundle(template_id)
        compiled_policy = template["compiled_policy"]
        route_target = compiled_policy["route_policy"]["batch"]
        candidate_ids = activity_ids or self.data_manager.select_batch_candidates(
            stale_before_hours=stale_before_hours,
            max_items=max_items,
        )
        if not candidate_ids:
            raise ValueError("No eligible activities found for batch agent analysis")

        job = self.data_manager.create_analysis_job(
            trigger_type=trigger_type,
            scope_type="batch",
            template_id=template["id"],
            route_policy=compiled_policy["route_policy"],
            budget_policy=budget_policy.model_dump(mode="json"),
            status="running",
            requested_by=requested_by,
        )

        completed = 0
        for activity_id in candidate_ids:
            activity = self.data_manager.get_activity_by_id(activity_id)
            if activity is None:
                continue
            try:
                self._execute_activity_pipeline(
                    job=job,
                    activity=activity,
                    template=template,
                    route_target=route_target,
                    research_policy=research_policy,
                    safety_policy=safety_policy,
                )
                completed += 1
            except Exception:
                continue

        self.data_manager.update_analysis_job(job.id, status="completed" if completed else "failed")
        detail = self.data_manager.get_analysis_job_detail(job.id)
        if detail is None:
            raise ValueError(f"Analysis job {job.id} not found after execution")
        return detail
