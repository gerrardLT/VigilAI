# VigilAI Agent Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade VigilAI from the current rule-driven analysis MVP into a real harness-based AI agent system that supports manual deep analysis, scheduled batch screening, human-reviewed writeback, and observable multi-step runs.

**Architecture:** Keep the current `activities`, `analysis templates`, and UI routes as the user-facing shell, but add a new `agent-analysis` domain behind them. The backend should introduce a central run manager, typed agent steps, provider routing, research guardrails, and review/writeback persistence; the frontend should upgrade the existing detail, pool, results, template, and workspace pages into agent-analysis surfaces instead of replacing them.

**Tech Stack:** FastAPI, SQLite, Pydantic, React, TypeScript, existing VigilAI data manager/service layer, pytest, Vitest.

---

## Scope Check

This spec spans backend orchestration, persistence, APIs, and UI, but they are all part of one coherent subsystem: the `agent-analysis` upgrade. Do not split this into separate plans. Instead, deliver it in vertical slices so that each backend milestone exposes a stable API before the corresponding frontend task consumes it.

## File Structure

### Backend

- Modify: `app/backend/config.py`
  Responsibility: load provider keys, route-policy defaults, budget caps, research limits, and scheduler toggles for the new harness.
- Modify: `app/backend/.env.example`
  Responsibility: document the environment variables needed for real model providers and batch-analysis scheduling.
- Modify: `app/backend/models.py`
  Responsibility: add typed Pydantic models for approved snapshots, jobs, items, steps, evidence, reviews, compiled template preferences, and job request payloads.
- Modify: `app/backend/data_manager.py`
  Responsibility: add SQLite tables, migration/backfill logic, CRUD for jobs/items/evidence/reviews, and projection of approved snapshots back into `activities`.
- Modify: `app/backend/api.py`
  Responsibility: expose additive `/api/agent-analysis/*` APIs and extend existing activity/workspace payloads with approved snapshot + latest draft metadata.
- Modify: `app/backend/scheduler.py`
  Responsibility: trigger scheduled batch jobs without coupling the scheduler to model/provider details.
- Modify: `app/backend/analysis/ai_enrichment.py`
  Responsibility: demote the current deterministic extractor into a fallback `heuristic_signals` role used when providers are unavailable or as precomputed hints for prompts.
- Modify: `app/backend/analysis/rule_engine.py`
  Responsibility: repurpose deterministic rules into a reusable safety-policy layer rather than the primary analysis engine.
- Modify: `app/backend/analysis/template_defaults.py`
  Responsibility: ship business-preference templates that compile into route, budget, and safety policies instead of directly exposing low-level model controls.
- Create: `app/backend/analysis/schemas.py`
  Responsibility: central typed payloads for context, screening result, research result, verdict draft, evidence, and review actions.
- Create: `app/backend/analysis/policies.py`
  Responsibility: typed route policy, budget policy, research policy, and safety policy helpers.
- Create: `app/backend/analysis/template_compiler.py`
  Responsibility: convert business template preferences into compiled execution policies and safety gates.
- Create: `app/backend/analysis/context_builder.py`
  Responsibility: build the per-item context package from activity content, source health, tracking state, and existing snapshot data.
- Create: `app/backend/analysis/providers/__init__.py`
  Responsibility: provider registry exports.
- Create: `app/backend/analysis/providers/base.py`
  Responsibility: provider protocol and shared request/response types for structured model calls.
- Create: `app/backend/analysis/providers/router.py`
  Responsibility: choose provider/model by task type and budget tier, with explicit downgrade logging.
- Create: `app/backend/analysis/providers/openai_provider.py`
  Responsibility: real model implementation for structured outputs and tool-backed research calls.
- Create: `app/backend/analysis/providers/deterministic_provider.py`
  Responsibility: deterministic provider used by tests and explicit local dry runs.
- Create: `app/backend/analysis/screening_agent.py`
  Responsibility: low-cost first-pass structured analysis using stored content only.
- Create: `app/backend/analysis/research_fetcher.py`
  Responsibility: bounded URL retrieval and source normalization for research mode.
- Create: `app/backend/analysis/research_agent.py`
  Responsibility: optional evidence-gathering step with caps on URLs, domains, and elapsed time.
- Create: `app/backend/analysis/verdict_agent.py`
  Responsibility: normalize screening + research output into the strict final draft schema.
- Create: `app/backend/analysis/safety_gate.py`
  Responsibility: apply deterministic policy overrides after verdict generation.
- Create: `app/backend/analysis/run_manager.py`
  Responsibility: orchestrate single-item and batch job lifecycles, step execution, status updates, retries, and downgrade events.
- Create: `app/backend/analysis/review_service.py`
  Responsibility: approve/edit/reject drafts and write approved snapshots back into `activities`.
- Create: `app/backend/tests/test_agent_analysis_models.py`
- Create: `app/backend/tests/test_agent_analysis_template_compiler.py`
- Create: `app/backend/tests/test_agent_analysis_provider_router.py`
- Create: `app/backend/tests/test_agent_analysis_screening.py`
- Create: `app/backend/tests/test_agent_analysis_research.py`
- Create: `app/backend/tests/test_agent_analysis_single_job_api.py`
- Create: `app/backend/tests/test_agent_analysis_review_api.py`
- Create: `app/backend/tests/test_agent_analysis_batch_jobs.py`
- Create: `app/backend/tests/test_agent_analysis_eval_replay.py`
  Responsibility: isolate new harness behavior from the existing rule-only MVP tests.

### Frontend

- Create: `app/frontend/src/types/agentAnalysis.ts`
  Responsibility: typed request/response contracts for jobs, items, evidence, reviews, and approved snapshots.
- Modify: `app/frontend/src/types/index.ts`
  Responsibility: export the new agent-analysis types and extend existing activity/workspace types with approved snapshot + draft metadata.
- Modify: `app/frontend/src/services/api.ts`
  Responsibility: add client methods for `/api/agent-analysis/*` and updated activity/detail payloads.
- Create: `app/frontend/src/hooks/useAgentAnalysisJobs.ts`
  Responsibility: load and refresh job lists, job detail, and batch operations.
- Create: `app/frontend/src/hooks/useAgentAnalysisItem.ts`
  Responsibility: load single-item draft/evidence/step state and expose rerun helpers.
- Create: `app/frontend/src/hooks/useAgentAnalysisReview.ts`
  Responsibility: approve, reject, and edit drafts with optimistic UI-safe state handling.
- Create: `app/frontend/src/components/analysis/AgentVerdictCard.tsx`
- Create: `app/frontend/src/components/analysis/StructuredFactorCard.tsx`
- Create: `app/frontend/src/components/analysis/EvidencePanel.tsx`
- Create: `app/frontend/src/components/analysis/ExecutionTracePanel.tsx`
- Create: `app/frontend/src/components/analysis/ReviewActionBar.tsx`
- Create: `app/frontend/src/components/analysis/JobStatusBanner.tsx`
- Create: `app/frontend/src/components/analysis/DraftBatchToolbar.tsx`
  Responsibility: reusable building blocks for the new agent-analysis UI surfaces.
- Modify: `app/frontend/src/pages/ActivityDetailPage.tsx`
  Responsibility: make this the primary single-item deep-analysis console.
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
  Responsibility: turn the opportunity pool into the batch draft review surface.
- Modify: `app/frontend/src/pages/AnalysisResultsPage.tsx`
  Responsibility: reposition the page as the job operations console.
- Modify: `app/frontend/src/pages/AnalysisTemplatesPage.tsx`
  Responsibility: change templates from low-level rule editors into business-preference editors with preview.
- Modify: `app/frontend/src/pages/WorkspacePage.tsx`
  Responsibility: summarize active template, batch-health, low-confidence workload, and blocked opportunities.
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/pages/index.ts`
  Responsibility: keep route wiring consistent while page roles evolve.
- Modify: `app/frontend/src/pages/ActivityDetailActions.test.tsx`
- Modify: `app/frontend/src/pages/AnalysisResultsPage.test.tsx`
- Modify: `app/frontend/src/pages/AnalysisTemplatesPage.test.tsx`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`
- Modify: `app/frontend/src/pages/WorkspacePage.test.tsx`
- Create: `app/frontend/src/hooks/useAgentAnalysisJobs.test.tsx`
- Create: `app/frontend/src/hooks/useAgentAnalysisItem.test.tsx`
  Responsibility: cover the new API-driven UI flows without destabilizing unrelated pages.

### Docs and Fixtures

- Create: `app/backend/tests/fixtures/agent_analysis_eval_set.json`
  Responsibility: golden input/output examples for replay-based regression tests.
- Modify: `docs/AI智能分析交互设计方案.md`
  Responsibility: mark the old rule-first design as historical context and point readers to the new agent-analysis architecture.
- Modify: `docs/superpowers/specs/2026-03-27-vigilai-agent-analysis-design.md`
  Responsibility: only if implementation decisions materially diverge from the approved spec.

---

### Task 1: Add agent-analysis persistence models and database schema

**Files:**
- Create: `app/backend/tests/test_agent_analysis_models.py`
- Create: `app/backend/analysis/schemas.py`
- Modify: `app/backend/models.py`
- Modify: `app/backend/data_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_data_manager_initializes_agent_analysis_tables(temp_db):
    data_manager = DataManager(db_path=temp_db)

    with data_manager._get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "analysis_jobs",
        "analysis_job_items",
        "analysis_item_steps",
        "analysis_evidence",
        "analysis_reviews",
    } <= tables


def test_analysis_snapshot_round_trips_with_structured_fields():
    snapshot = AnalysisSnapshot(
        status="watch",
        summary="Need manual review",
        reasons=["Reward clarity is incomplete"],
        structured={"should_deep_research": True},
    )

    assert snapshot.model_dump()["structured"]["should_deep_research"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_models.py -q`
Expected: FAIL because the new tables, snapshot model, and typed agent-analysis records do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class AnalysisSnapshot(BaseModel):
    status: Literal["pass", "watch", "reject", "insufficient_evidence"]
    summary: str
    reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    confidence: float | None = None
    structured: dict[str, Any] = Field(default_factory=dict)
    template_id: str | None = None
    current_run_id: str | None = None
    updated_at: datetime | None = None
```

Implement:
- SQLite migration helpers for `analysis_jobs`, `analysis_job_items`, `analysis_item_steps`, `analysis_evidence`, `analysis_reviews`
- approved snapshot columns on `activities`
- `AnalysisJob`, `AnalysisJobItem`, `AnalysisStep`, `AnalysisEvidence`, `AnalysisReview` models
- serialization helpers in `DataManager`

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/schemas.py app/backend/models.py app/backend/data_manager.py app/backend/tests/test_agent_analysis_models.py
git commit -m "feat: add agent analysis persistence foundation"
```

### Task 2: Compile business templates into route, budget, and safety policies

**Files:**
- Create: `app/backend/tests/test_agent_analysis_template_compiler.py`
- Create: `app/backend/analysis/policies.py`
- Create: `app/backend/analysis/template_compiler.py`
- Modify: `app/backend/analysis/template_defaults.py`
- Modify: `app/backend/data_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_template_compiler_maps_business_preferences_to_execution_policy():
    compiled = compile_analysis_template(
        {
            "name": "Money first",
            "preference_profile": "money_first",
            "risk_tolerance": "balanced",
            "research_mode": "layered",
        }
    )

    assert compiled.route_policy.single_item.task_type == "deep_analysis"
    assert compiled.route_policy.batch.task_type == "screening"
    assert compiled.safety_policy.writeback_mode == "human_review"
    assert compiled.research_policy.default_mode == "layered"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_template_compiler.py -q`
Expected: FAIL because templates are still low-level layer bundles and there is no compiler.

- [ ] **Step 3: Write minimal implementation**

```python
def compile_analysis_template(raw_template: dict[str, Any]) -> CompiledAnalysisTemplate:
    return CompiledAnalysisTemplate(
        route_policy=build_route_policy(raw_template),
        budget_policy=build_budget_policy(raw_template),
        research_policy=build_research_policy(raw_template),
        safety_policy=build_safety_policy(raw_template),
    )
```

Implement:
- `RoutePolicy`, `BudgetPolicy`, `ResearchPolicy`, `SafetyPolicy` models
- business-preference defaults in `template_defaults.py`
- persistence updates so template records store friendly fields and compiled policy JSON
- compatibility adapters so existing template reads still work during migration

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_template_compiler.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/policies.py app/backend/analysis/template_compiler.py app/backend/analysis/template_defaults.py app/backend/data_manager.py app/backend/tests/test_agent_analysis_template_compiler.py
git commit -m "feat: compile business analysis templates into policies"
```

### Task 3: Add provider registry and multi-model routing

**Files:**
- Create: `app/backend/tests/test_agent_analysis_provider_router.py`
- Create: `app/backend/analysis/providers/__init__.py`
- Create: `app/backend/analysis/providers/base.py`
- Create: `app/backend/analysis/providers/router.py`
- Create: `app/backend/analysis/providers/openai_provider.py`
- Create: `app/backend/analysis/providers/deterministic_provider.py`
- Modify: `app/backend/config.py`
- Modify: `app/backend/.env.example`

- [ ] **Step 1: Write the failing tests**

```python
def test_model_router_selects_models_by_task_type_and_budget():
    router = AnalysisModelRouter(
        {
            "screening": {"low": "screening-cheap", "default": "screening-main"},
            "research": {"default": "research-main", "fallback": "research-backup"},
        }
    )

    route = router.select(task_type="screening", budget_tier="low")

    assert route.primary_model == "screening-cheap"
    assert route.task_type == "screening"


def test_deterministic_test_provider_returns_structured_payload_for_contract_tests():
    provider = DeterministicTestProvider(
        screening_payload={"status": "pass", "confidence": 0.83}
    )

    response = provider.generate_structured(task_type="screening", schema_name="screening_result", prompt="...")

    assert response.output["status"] == "pass"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_provider_router.py -q`
Expected: FAIL because there is no provider abstraction, router, or env-driven model config.

- [ ] **Step 3: Write minimal implementation**

```python
class AnalysisProvider(Protocol):
    def generate_structured(
        self,
        *,
        task_type: str,
        schema_name: str,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse: ...
```

Implement:
- provider protocol and response types
- provider registry with `test`/compat `mock` and `openai`
- explicit downgrade logging in the router
- env config for `ANALYSIS_PROVIDER`, `ANALYSIS_SCREENING_MODEL`, `ANALYSIS_RESEARCH_MODEL`, `ANALYSIS_VERDICT_MODEL`, backup models, and budget caps

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_provider_router.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/config.py app/backend/.env.example app/backend/analysis/providers/__init__.py app/backend/analysis/providers/base.py app/backend/analysis/providers/router.py app/backend/analysis/providers/openai_provider.py app/backend/analysis/providers/deterministic_provider.py app/backend/tests/test_agent_analysis_provider_router.py
git commit -m "feat: add agent analysis provider routing"
```

### Task 4: Build the context builder and screening agent

**Files:**
- Create: `app/backend/tests/test_agent_analysis_screening.py`
- Create: `app/backend/analysis/context_builder.py`
- Create: `app/backend/analysis/screening_agent.py`
- Modify: `app/backend/analysis/ai_enrichment.py`
- Modify: `app/backend/analysis/schemas.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_context_builder_prefers_stored_activity_content_and_source_health():
    context = build_analysis_context(activity, source_row, current_snapshot=None)

    assert context.activity_id == activity.id
    assert context.content.full_text.startswith(activity.title)
    assert context.source_health["freshness_level"] in {"fresh", "aging", "stale", "critical", "never"}


def test_screening_agent_returns_structured_first_pass_without_research():
    result = screening_agent.run(context)

    assert result.status in {"pass", "watch", "reject"}
    assert result.research_state == "not_requested"
    assert "should_deep_research" in result.structured
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_screening.py -q`
Expected: FAIL because there is no context builder or screening agent.

- [ ] **Step 3: Write minimal implementation**

```python
def build_analysis_context(
    activity: Activity,
    source_row: sqlite3.Row | None,
    current_snapshot: AnalysisSnapshot | None,
) -> AnalysisContext:
    return AnalysisContext(
        activity_id=activity.id,
        title=activity.title,
        full_text="\n\n".join(filter(None, [activity.title, activity.description, activity.full_content])),
        source_health=build_source_health_payload(source_row),
        heuristic_signals=extract_heuristic_signals(activity),
        current_snapshot=current_snapshot,
    )
```

Implement:
- `AnalysisContext` schema
- prompt assembly based on stored/internal content only
- screening-agent contract using the routed provider
- fallback heuristics from `ai_enrichment.py` when provider calls are unavailable

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_screening.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/context_builder.py app/backend/analysis/screening_agent.py app/backend/analysis/ai_enrichment.py app/backend/analysis/schemas.py app/backend/tests/test_agent_analysis_screening.py
git commit -m "feat: add context builder and screening agent"
```

### Task 5: Add guarded research mode and evidence storage

**Files:**
- Create: `app/backend/tests/test_agent_analysis_research.py`
- Create: `app/backend/analysis/research_fetcher.py`
- Create: `app/backend/analysis/research_agent.py`
- Modify: `app/backend/data_manager.py`
- Modify: `app/backend/analysis/schemas.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_research_agent_respects_url_budget_and_allowed_source_classes():
    result = research_agent.run(
        context=context,
        screening_result=screening_result,
        policy=ResearchPolicy(max_urls_per_item=2, allowed_source_classes=["official", "search"]),
    )

    assert len(result.evidence) <= 2
    assert all(item.source_type in {"official", "search"} for item in result.evidence)


def test_research_agent_marks_unavailable_state_when_budget_is_exhausted():
    result = research_agent.run(
        context=context,
        screening_result=screening_result,
        policy=ResearchPolicy(max_urls_per_item=0),
    )

    assert result.state == "research_unavailable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_research.py -q`
Expected: FAIL because research mode, fetch limits, and evidence records do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class ResearchFetcher:
    def fetch_candidates(self, query: str, *, limit: int, allowed_source_classes: set[str]) -> list[FetchedDocument]:
        ...


class ResearchAgent:
    def run(self, *, context: AnalysisContext, screening_result: ScreeningResult, policy: ResearchPolicy) -> ResearchResult:
        ...
```

Implement:
- research escalation only when `should_deep_research` or manual deep-analysis policy requires it
- hard caps on URLs, domains, and elapsed time
- `analysis_evidence` persistence
- explicit `research_unavailable` and `insufficient_evidence` states

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_research.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/research_fetcher.py app/backend/analysis/research_agent.py app/backend/data_manager.py app/backend/analysis/schemas.py app/backend/tests/test_agent_analysis_research.py
git commit -m "feat: add guarded research mode"
```

### Task 6: Add verdict generation, safety gating, and manual single-item jobs

**Files:**
- Create: `app/backend/tests/test_agent_analysis_single_job_api.py`
- Create: `app/backend/analysis/verdict_agent.py`
- Create: `app/backend/analysis/safety_gate.py`
- Create: `app/backend/analysis/run_manager.py`
- Modify: `app/backend/analysis/rule_engine.py`
- Modify: `app/backend/data_manager.py`
- Modify: `app/backend/api.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_manual_single_job_runs_screening_research_verdict_and_safety(client, seeded_activity):
    response = client.post(
        "/api/agent-analysis/jobs",
        json={"scope_type": "single", "trigger_type": "manual", "activity_ids": [seeded_activity.id]},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["scope_type"] == "single"
    assert body["items"][0]["draft"]["status"] in {"pass", "watch", "reject", "insufficient_evidence"}
    assert {step["step_type"] for step in body["items"][0]["steps"]} >= {"screening", "verdict"}
    assert "raw_chain_of_thought" not in body["items"][0]["draft"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_single_job_api.py -q`
Expected: FAIL because `/api/agent-analysis/jobs` and the full orchestration path do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class AnalysisRunManager:
    def run_single_job(self, *, activity_id: str, template_id: str | None, requested_by: str | None) -> AnalysisJobDetail:
        screening = self.screening_agent.run(context)
        research = self.research_agent.run_if_needed(context, screening)
        verdict = self.verdict_agent.run(context, screening, research)
        gated = self.safety_gate.apply(verdict, compiled_template)
        return self._persist_single_item_job(...)
```

Implement:
- `/api/agent-analysis/jobs`
- `/api/agent-analysis/jobs/{job_id}`
- `/api/agent-analysis/items/{item_id}`
- verdict normalization and safety overrides
- explicit logging of downgrade and retry events in `analysis_item_steps`

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_single_job_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/verdict_agent.py app/backend/analysis/safety_gate.py app/backend/analysis/run_manager.py app/backend/analysis/rule_engine.py app/backend/data_manager.py app/backend/api.py app/backend/tests/test_agent_analysis_single_job_api.py
git commit -m "feat: add manual agent analysis job orchestration"
```

### Task 7: Add review/writeback workflow and approved snapshot projection

**Files:**
- Create: `app/backend/tests/test_agent_analysis_review_api.py`
- Create: `app/backend/analysis/review_service.py`
- Modify: `app/backend/data_manager.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/models.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_approve_item_writes_draft_snapshot_back_to_activity(client, completed_job_item):
    response = client.post(
        f"/api/agent-analysis/items/{completed_job_item.id}/approve",
        json={"review_note": "Looks good"},
    )

    body = response.json()
    refreshed = client.get(f"/api/activities/{completed_job_item.activity_id}").json()

    assert response.status_code == 200
    assert body["review_action"] == "approved"
    assert refreshed["analysis_status"] == body["snapshot"]["status"]
    assert refreshed["analysis_current_run_id"] == completed_job_item.job_id


def test_reject_item_keeps_activity_snapshot_unchanged(client, completed_job_item):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_review_api.py -q`
Expected: FAIL because there are no approve/reject/edit review endpoints or writeback logic.

- [ ] **Step 3: Write minimal implementation**

```python
class ReviewService:
    def approve_item(self, item_id: str, *, review_note: str | None, edited_snapshot: dict[str, Any] | None = None) -> AnalysisReview:
        final_snapshot = edited_snapshot or self.data_manager.get_latest_draft_snapshot(item_id)
        self.data_manager.write_activity_snapshot(activity_id, final_snapshot)
        return self.data_manager.insert_review(...)
```

Implement:
- `/api/agent-analysis/items/{item_id}/approve`
- `/api/agent-analysis/items/{item_id}/reject`
- optional edit-then-approve payload
- `analysis_reviews` persistence
- writeback only on explicit approval

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_review_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/review_service.py app/backend/data_manager.py app/backend/api.py app/backend/models.py app/backend/tests/test_agent_analysis_review_api.py
git commit -m "feat: add agent analysis review and writeback"
```

### Task 8: Add scheduled batch jobs and job operations APIs

**Files:**
- Create: `app/backend/tests/test_agent_analysis_batch_jobs.py`
- Modify: `app/backend/analysis/run_manager.py`
- Modify: `app/backend/data_manager.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/scheduler.py`
- Modify: `app/backend/config.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_scheduled_batch_job_selects_new_updated_and_stale_items(client, seeded_batch_activities):
    response = client.post(
        "/api/agent-analysis/jobs",
        json={"scope_type": "batch", "trigger_type": "scheduled"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["scope_type"] == "batch"
    assert body["item_count"] >= 1
    assert any(item["needs_research"] for item in body["items"])


def test_job_list_endpoint_returns_batch_health(client):
    response = client.get("/api/agent-analysis/jobs")
    assert response.status_code == 200
    assert "items" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_batch_jobs.py -q`
Expected: FAIL because scheduled candidate selection and job list APIs do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def select_batch_candidates(conn: sqlite3.Connection, *, stale_before_hours: int, max_items: int) -> list[str]:
    ...


async def run_scheduled_agent_analysis(self) -> None:
    job = self.run_manager.create_batch_job(trigger_type="scheduled")
    self.run_manager.execute_job(job.id)
```

Implement:
- batch candidate selection based on new/updated/stale activities
- `/api/agent-analysis/jobs`
- scheduler hook controlled by config flags
- summarized job health for UI consumption

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_batch_jobs.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/run_manager.py app/backend/data_manager.py app/backend/api.py app/backend/scheduler.py app/backend/config.py app/backend/tests/test_agent_analysis_batch_jobs.py
git commit -m "feat: add scheduled batch agent analysis jobs"
```

### Task 9: Add frontend types, API client methods, and hooks for agent-analysis

**Files:**
- Create: `app/frontend/src/types/agentAnalysis.ts`
- Modify: `app/frontend/src/types/index.ts`
- Modify: `app/frontend/src/services/api.ts`
- Create: `app/frontend/src/hooks/useAgentAnalysisJobs.ts`
- Create: `app/frontend/src/hooks/useAgentAnalysisItem.ts`
- Create: `app/frontend/src/hooks/useAgentAnalysisReview.ts`
- Create: `app/frontend/src/hooks/useAgentAnalysisJobs.test.tsx`
- Create: `app/frontend/src/hooks/useAgentAnalysisItem.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
it('loads agent-analysis jobs and exposes refresh state', async () => {
  const { result } = renderHook(() => useAgentAnalysisJobs())

  await waitFor(() => expect(result.current.jobs.length).toBeGreaterThan(0))
  expect(result.current.loading).toBe(false)
})


it('approves an item through the review hook', async () => {
  const { result } = renderHook(() => useAgentAnalysisReview())

  await act(async () => {
    await result.current.approveItem('item-1', { review_note: 'approved' })
  })

  expect(api.approveAgentAnalysisItem).toHaveBeenCalledWith('item-1', { review_note: 'approved' })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm test -- --run src/hooks/useAgentAnalysisJobs.test.tsx src/hooks/useAgentAnalysisItem.test.tsx`
Expected: FAIL because the new types, API methods, and hooks do not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
export interface AgentAnalysisJob {
  id: string
  trigger_type: 'manual' | 'scheduled'
  scope_type: 'single' | 'batch'
  status: string
  item_count: number
}
```

Implement:
- frontend contracts for jobs, items, evidence, review actions, and snapshots
- API methods for all `/api/agent-analysis/*` endpoints
- hooks for job list, item detail, rerun, approve, reject, and edit-approve flows

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm test -- --run src/hooks/useAgentAnalysisJobs.test.tsx src/hooks/useAgentAnalysisItem.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/types/agentAnalysis.ts app/frontend/src/types/index.ts app/frontend/src/services/api.ts app/frontend/src/hooks/useAgentAnalysisJobs.ts app/frontend/src/hooks/useAgentAnalysisItem.ts app/frontend/src/hooks/useAgentAnalysisReview.ts app/frontend/src/hooks/useAgentAnalysisJobs.test.tsx app/frontend/src/hooks/useAgentAnalysisItem.test.tsx
git commit -m "feat: add frontend agent analysis data layer"
```

### Task 10: Turn the activity detail page into the deep-analysis workbench

**Files:**
- Create: `app/frontend/src/components/analysis/AgentVerdictCard.tsx`
- Create: `app/frontend/src/components/analysis/StructuredFactorCard.tsx`
- Create: `app/frontend/src/components/analysis/EvidencePanel.tsx`
- Create: `app/frontend/src/components/analysis/ExecutionTracePanel.tsx`
- Create: `app/frontend/src/components/analysis/ReviewActionBar.tsx`
- Modify: `app/frontend/src/pages/ActivityDetailPage.tsx`
- Modify: `app/frontend/src/pages/ActivityDetailActions.test.tsx`
- Modify: `app/frontend/src/pages/ActivityDetailPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
it('starts a manual deep-analysis job from the detail page', async () => {
  render(<ActivityDetailPage />)

  await user.click(screen.getByRole('button', { name: /deep analysis/i }))

  expect(api.createAgentAnalysisJob).toHaveBeenCalled()
})


it('shows evidence and review actions for a completed draft', async () => {
  render(<ActivityDetailPage />)

  expect(await screen.findByTestId('agent-analysis-evidence-panel')).toBeInTheDocument()
  expect(screen.getByTestId('agent-analysis-review-bar')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm test -- --run src/pages/ActivityDetailActions.test.tsx src/pages/ActivityDetailPage.test.tsx`
Expected: FAIL because the detail page still only renders the old rule-based analysis panel.

- [ ] **Step 3: Write minimal implementation**

```tsx
<AgentVerdictCard snapshot={item.latest_draft_snapshot} onRerun={handleRerun} />
<StructuredFactorCard structured={item.latest_draft_snapshot?.structured ?? {}} />
<EvidencePanel evidence={item.evidence} />
<ExecutionTracePanel steps={item.steps} />
<ReviewActionBar onApprove={approveItem} onReject={rejectItem} />
```

Implement:
- manual deep-analysis trigger
- verdict, structured factors, evidence, and execution trace panels
- review/writeback buttons
- graceful empty/loading/error states

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm test -- --run src/pages/ActivityDetailActions.test.tsx src/pages/ActivityDetailPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/components/analysis/AgentVerdictCard.tsx app/frontend/src/components/analysis/StructuredFactorCard.tsx app/frontend/src/components/analysis/EvidencePanel.tsx app/frontend/src/components/analysis/ExecutionTracePanel.tsx app/frontend/src/components/analysis/ReviewActionBar.tsx app/frontend/src/pages/ActivityDetailPage.tsx app/frontend/src/pages/ActivityDetailActions.test.tsx app/frontend/src/pages/ActivityDetailPage.test.tsx
git commit -m "feat: add deep analysis detail workbench"
```

### Task 11: Upgrade the opportunity pool and results page into batch-review surfaces

**Files:**
- Create: `app/frontend/src/components/analysis/JobStatusBanner.tsx`
- Create: `app/frontend/src/components/analysis/DraftBatchToolbar.tsx`
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
- Modify: `app/frontend/src/pages/AnalysisResultsPage.tsx`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`
- Modify: `app/frontend/src/pages/AnalysisResultsPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
it('shows the latest batch job banner and draft-only filters', async () => {
  render(<ActivitiesPage />)

  expect(await screen.findByTestId('agent-analysis-job-banner')).toBeInTheDocument()
  expect(screen.getByTestId('agent-analysis-filter-draft-only')).toBeInTheDocument()
})


it('supports batch approval from the opportunity pool', async () => {
  render(<ActivitiesPage />)

  await user.click(screen.getByTestId('agent-analysis-batch-approve'))

  expect(api.approveAgentAnalysisBatch).toHaveBeenCalled()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm test -- --run src/pages/OpportunityPoolPage.test.tsx src/pages/AnalysisResultsPage.test.tsx`
Expected: FAIL because the pool/results pages still target the old rule-preview flow.

- [ ] **Step 3: Write minimal implementation**

```tsx
<JobStatusBanner job={latestBatchJob} />
<DraftBatchToolbar
  selectedIds={selectedIds}
  onApprove={handleBatchApprove}
  onReject={handleBatchReject}
  onDeepResearch={handleBatchDeepResearch}
/>
```

Implement:
- latest batch job banner
- draft-only, low-confidence, and review-state filters
- batch approve/reject/deep-research actions
- results page job list + per-item failure view instead of only pass/watch/reject cards

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm test -- --run src/pages/OpportunityPoolPage.test.tsx src/pages/AnalysisResultsPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/components/analysis/JobStatusBanner.tsx app/frontend/src/components/analysis/DraftBatchToolbar.tsx app/frontend/src/pages/ActivitiesPage.tsx app/frontend/src/pages/AnalysisResultsPage.tsx app/frontend/src/pages/OpportunityPoolPage.test.tsx app/frontend/src/pages/AnalysisResultsPage.test.tsx
git commit -m "feat: add batch agent analysis review surfaces"
```

### Task 12: Reposition templates and workspace for the new agent system

**Files:**
- Modify: `app/frontend/src/pages/AnalysisTemplatesPage.tsx`
- Modify: `app/frontend/src/pages/WorkspacePage.tsx`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/pages/index.ts`
- Modify: `app/frontend/src/pages/AnalysisTemplatesPage.test.tsx`
- Modify: `app/frontend/src/pages/WorkspacePage.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
it('edits business template preferences instead of raw model routing', async () => {
  render(<AnalysisTemplatesPage />)

  expect(await screen.findByLabelText(/risk tolerance/i)).toBeInTheDocument()
  expect(screen.queryByText(/screening_model/i)).not.toBeInTheDocument()
})


it('shows active template and draft-review workload on the workspace', async () => {
  render(<WorkspacePage />)

  expect(await screen.findByTestId('workspace-agent-analysis-summary')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm test -- --run src/pages/AnalysisTemplatesPage.test.tsx src/pages/WorkspacePage.test.tsx`
Expected: FAIL because templates still expose low-level rule editing and the workspace only shows rule-era summaries.

- [ ] **Step 3: Write minimal implementation**

```tsx
<select aria-label="Risk tolerance" value={draft.risk_tolerance} onChange={...} />
<select aria-label="Research mode" value={draft.research_mode} onChange={...} />
<section data-testid="workspace-agent-analysis-summary">...</section>
```

Implement:
- business-preference controls on the template page
- preview counts and example outcomes based on compiled policies
- workspace summary for active template, pending drafts, low-confidence items, and recent batch health
- route labels/navigation copy updates if needed

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm test -- --run src/pages/AnalysisTemplatesPage.test.tsx src/pages/WorkspacePage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/pages/AnalysisTemplatesPage.tsx app/frontend/src/pages/WorkspacePage.tsx app/frontend/src/App.tsx app/frontend/src/pages/index.ts app/frontend/src/pages/AnalysisTemplatesPage.test.tsx app/frontend/src/pages/WorkspacePage.test.tsx
git commit -m "feat: reposition templates and workspace for agent analysis"
```

### Task 13: Add replay-based evaluation and run full verification

**Files:**
- Create: `app/backend/tests/fixtures/agent_analysis_eval_set.json`
- Create: `app/backend/tests/test_agent_analysis_eval_replay.py`
- Modify: `docs/AI智能分析交互设计方案.md`
- Modify: `docs/superpowers/specs/2026-03-27-vigilai-agent-analysis-design.md` (only if needed for implementation drift notes)

- [ ] **Step 1: Write the failing tests**

```python
def test_eval_replay_matches_expected_status_and_risk_flags(eval_fixture):
    report = replay_eval_set(eval_fixture)

    assert report["total"] >= 5
    assert report["status_match_rate"] >= 0.8
    assert report["risk_flag_match_rate"] >= 0.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_eval_replay.py -q`
Expected: FAIL because the replay fixture and evaluation harness do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def replay_eval_set(cases: list[dict[str, Any]]) -> dict[str, float]:
    ...
```

Implement:
- small human-reviewed eval fixture
- replay test that exercises screening, research, verdict, and safety paths with the deterministic test provider
- docs cleanup so the old rule-only design is clearly marked as superseded

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_agent_analysis_eval_replay.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/tests/fixtures/agent_analysis_eval_set.json app/backend/tests/test_agent_analysis_eval_replay.py docs/AI智能分析交互设计方案.md docs/superpowers/specs/2026-03-27-vigilai-agent-analysis-design.md
git commit -m "test: add agent analysis replay evaluation"
```

### Task 14: Final verification and release-readiness pass

**Files:**
- Verify: `app/backend/tests/test_analysis_api.py`
- Verify: `app/backend/tests/test_analysis_rule_engine.py`
- Verify: `app/backend/tests/test_analysis_templates.py`
- Verify: `app/backend/tests/test_agent_analysis_*.py`
- Verify: `app/frontend/src/pages/ActivityDetailActions.test.tsx`
- Verify: `app/frontend/src/pages/AnalysisResultsPage.test.tsx`
- Verify: `app/frontend/src/pages/AnalysisTemplatesPage.test.tsx`
- Verify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`
- Verify: `app/frontend/src/pages/WorkspacePage.test.tsx`
- Verify: `app/frontend/src/hooks/useAgentAnalysisJobs.test.tsx`
- Verify: `app/frontend/src/hooks/useAgentAnalysisItem.test.tsx`
- Verify: `app/frontend/src/services/api.test.ts`

- [ ] **Step 1: Run the backend analysis suites**

Run: `Set-Location app/backend; python -m pytest tests/test_analysis_api.py tests/test_analysis_rule_engine.py tests/test_analysis_templates.py tests/test_agent_analysis_models.py tests/test_agent_analysis_template_compiler.py tests/test_agent_analysis_provider_router.py tests/test_agent_analysis_screening.py tests/test_agent_analysis_research.py tests/test_agent_analysis_single_job_api.py tests/test_agent_analysis_review_api.py tests/test_agent_analysis_batch_jobs.py tests/test_agent_analysis_eval_replay.py -q`
Expected: PASS

- [ ] **Step 2: Run the frontend targeted suites**

Run: `Set-Location app/frontend; npm test -- --run src/pages/ActivityDetailActions.test.tsx src/pages/AnalysisResultsPage.test.tsx src/pages/AnalysisTemplatesPage.test.tsx src/pages/OpportunityPoolPage.test.tsx src/pages/WorkspacePage.test.tsx src/hooks/useAgentAnalysisJobs.test.tsx src/hooks/useAgentAnalysisItem.test.tsx src/services/api.test.ts`
Expected: PASS

- [ ] **Step 3: Run the frontend build**

Run: `Set-Location app/frontend; npm run build`
Expected: PASS

- [ ] **Step 4: Run the backend smoke start**

Run: `Set-Location app/backend; python api.py`
Expected: API starts without missing-config or migration errors; stop it after the startup check.

- [ ] **Step 5: Commit**

```bash
git status --short
# Add only the files touched while fixing verification fallout in this task.
git add <exact-files-fixed-during-verification>
git commit -m "chore: finalize agent analysis verification fixes"
```

---

## Implementation Notes

- Keep `/api/analysis/templates` as the business-template API and add `/api/agent-analysis/*` for execution, evidence, and review flows.
- Do not remove the old rule-engine helpers until the new safety gate is green and legacy template previews still pass.
- Approved snapshots are the only data shown as activity truth on list/detail pages; latest drafts stay separate and must remain reviewable.
- Never persist raw hidden reasoning or full chain-of-thought in `analysis_item_steps`; store only prompts/outputs that are safe to audit.
- Research must default off for screening and must never silently claim success when budgets or network access block it.
- Use the deterministic test provider in automated tests so replay coverage is deterministic and cheap.
- This repository can be dirty while implementation is in progress, so never use `git add .` or broad cleanup commands during execution. Stage only the files touched by the current task.

## Suggested Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8
9. Task 9
10. Task 10
11. Task 11
12. Task 12
13. Task 13
14. Task 14
