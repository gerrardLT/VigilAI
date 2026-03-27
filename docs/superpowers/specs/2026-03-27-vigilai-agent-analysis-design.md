# VigilAI Agent Analysis System Design

## Summary

VigilAI already has an analysis-shaped product surface: analysis pages, template management, pass/watch/reject states, and a deterministic rule engine. What it does not yet have is a real AI agent system.

This design upgrades the current implementation from a rule-first "AI-style analysis UI" into a harness-driven agent system:

- multi-step, multi-agent analysis
- layered evidence collection
- task-type-aware model routing
- budget and network controls
- human review before writeback
- observable, replayable runs

The first release targets two workflows:

1. single-opportunity deep analysis
2. batch opportunity-pool screening

The system uses a `C-lite` architecture: a central harness orchestrates a small set of specialist agents rather than a fully decentralized agent network.

## Problem Statement

The current system gives users the shape of AI analysis without the substance:

- analysis results are primarily rule-derived
- "AI enrichment" is deterministic keyword logic
- there is no true model orchestration
- there is no evidence collection flow
- there is no research-vs-screening split
- there is no reviewable draft pipeline before writeback

The goal is not to bolt a single prompt onto the existing UI. The goal is to create a stable operational layer around models so VigilAI can reliably analyze opportunities in production.

## Goals

- Add a real agent execution layer for opportunity analysis.
- Support both low-cost batch screening and higher-cost single-item deep analysis.
- Default to using stored activity content; escalate to web research only when needed.
- Return deep structured analysis results, not just a single score.
- Keep the current UI investment by upgrading existing pages into agent operation surfaces.
- Require human approval before AI results overwrite activity-level analysis snapshots.
- Make runs observable, auditable, replayable, and budget-controlled.

## Non-Goals

- Fully autonomous writeback in the first release
- unrestricted multi-agent peer-to-peer collaboration
- persistent conversational agents with memory across unrelated jobs
- storing full chain-of-thought or raw hidden reasoning
- unrestricted web browsing or arbitrary crawling
- user-configurable low-level model routing from the template editor

## Product Principles

### Harness First

Models are components inside a controlled system. The harness, not the model, owns:

- task sequencing
- routing
- budget enforcement
- network access policy
- schema validation
- retry and downgrade behavior
- review gating

### Agent First, Rules as Safety Gate

Agent outputs drive product value. Rules remain important, but mainly as:

- hard-stop protections
- minimum policy enforcement
- consistency checks

This replaces the current pattern where rules act as the primary intelligence layer.

### Layered Research

The system should not research every item by default.

- batch screening uses stored content first
- high-value, low-confidence, or conflicting cases escalate to research
- manual deep analysis can directly trigger research

### Draft Before Snapshot

Agent results should first land as drafts. Approved snapshots are what activity list and detail views use as their current truth.

### Strong Structured Output

Final outputs must conform to a strict schema. Free-form model prose is a rendering detail, not the system of record.

## Current-State Mapping

The following current components stay relevant:

- ingestion and source refresh pipeline
- activity persistence and detail payloads
- existing analysis pages and route structure
- existing rule engine and templates, repurposed as safety and policy layers

The following current components are redefined:

- `analysis.ai_enrichment` stops being the "AI layer"
- `analysis.rule_engine` becomes `Safety Gate` / policy enforcement
- analysis template pages become business-preference editors, not low-level model routers

## Proposed Architecture

### Top-Level Components

1. `Analysis Run Manager`
2. `Context Builder`
3. `Screening Agent`
4. `Research Agent`
5. `Verdict Agent`
6. `Safety Gate`
7. `Human Review + Writeback`

### Component Responsibilities

#### 1. Analysis Run Manager

Owns lifecycle of jobs and job items.

Responsibilities:

- create jobs for manual and scheduled triggers
- split batch jobs into item tasks
- assign route and budget policy
- track status and retries
- record model usage and downgrade events
- expose run health for UI and debugging

#### 2. Context Builder

Builds the input package for agent steps.

Inputs:

- activity title, summary, description, full content
- source metadata and source health
- current analysis snapshot
- tracking state
- related items or historical context where relevant

Outputs:

- standardized agent context payload
- lightweight context digest for tracing

#### 3. Screening Agent

Low-cost first pass for both batch and single-item flows.

Outputs:

- `pass/watch/reject`
- structured opportunity fields
- short summary
- top reasons
- recommended next action
- confidence
- `should_deep_research`

Constraints:

- no default web research
- cheap model tier only
- strict schema output

#### 4. Research Agent

Optional escalation step.

Trigger conditions:

- high-value opportunity
- low confidence from screening
- information conflict
- reward ambiguity
- organizer ambiguity
- manual deep analysis request

Responsibilities:

- gather targeted external evidence
- summarize supporting and conflicting evidence
- score source reliability
- avoid broad web wandering

#### 5. Verdict Agent

Synthesizes screening and research outputs into one normalized final draft.

Responsibilities:

- produce final structured result
- normalize language and severity
- surface top recommendation
- clearly mark evidence limitations

#### 6. Safety Gate

Runs deterministic safety and policy checks after the verdict draft.

Examples:

- explicit no-reward opportunity
- hard team-only restriction
- obvious trust failure
- policy-defined rejection conditions

Possible effects:

- force `reject`
- downgrade `pass` to `watch`
- mark `manual_review_required`

#### 7. Human Review + Writeback

Makes the first release safe to ship.

Review actions:

- approve and write back
- edit then approve
- reject AI result
- rerun analysis

## Execution Flows

### Flow A: Scheduled Batch Screening

1. scheduler creates `analysis_job(trigger=scheduled, scope=batch)`
2. run manager selects candidate activities:
   - new activities
   - updated content
   - stale prior analysis
   - optionally score-prioritized items
3. context builder prepares context
4. screening agent runs on all selected items
5. only flagged items escalate to research
6. verdict agent produces final drafts
7. safety gate enforces hard policy
8. drafts are stored
9. UI exposes items for review and approval

### Flow B: Manual Single-Item Deep Analysis

1. user clicks deep analysis on the detail page
2. system creates `analysis_job(trigger=manual, scope=single)`
3. context builder prepares rich context
4. screening agent runs
5. research agent runs immediately or conditionally, depending on route policy
6. verdict agent produces a final draft
7. safety gate applies overrides if necessary
8. result is shown in detail view
9. user approves, edits, or rejects

### Flow C: Batch Review and Writeback

1. user filters to draft items in the opportunity pool
2. user selects one or many items
3. user approves writeback
4. system writes a complete approved snapshot to the activity record
5. review action is logged

## Data Model

### Data Strategy

Use a mixed model:

- `activities` store approved current analysis snapshot only
- run execution, evidence, and review data live in dedicated new tables
- list pages read snapshots
- detail pages can read current snapshot plus latest draft/run detail

### Activity Snapshot Fields

Extend activity-level analysis snapshot with:

- `analysis_status`
- `analysis_summary`
- `analysis_reasons`
- `analysis_risk_flags`
- `analysis_recommended_action`
- `analysis_confidence`
- `analysis_structured`
- `analysis_template_id`
- `analysis_current_run_id`
- `analysis_updated_at`

`analysis_structured` is JSON and includes:

- `roi_level`
- `effort_level`
- `payout_speed`
- `reward_clarity`
- `source_credibility`
- `solo_fit`
- `urgency`
- `should_deep_research`

### New Tables

#### `analysis_jobs`

Represents a top-level run.

Suggested fields:

- `id`
- `trigger_type` (`manual`, `scheduled`)
- `scope_type` (`single`, `batch`)
- `template_id`
- `route_policy`
- `budget_policy`
- `status`
- `requested_by`
- `created_at`
- `finished_at`

#### `analysis_job_items`

Represents a single opportunity inside a job.

Suggested fields:

- `id`
- `job_id`
- `activity_id`
- `status`
- `needs_research`
- `final_draft_status`
- `screening_model`
- `research_model`
- `verdict_model`
- `started_at`
- `finished_at`

#### `analysis_item_steps`

Stores structured execution trace by step.

Suggested fields:

- `id`
- `job_item_id`
- `step_type`
- `step_status`
- `input_digest`
- `output_payload`
- `latency_ms`
- `cost_tokens_in`
- `cost_tokens_out`
- `model_name`
- `created_at`

#### `analysis_evidence`

Stores evidence gathered during research.

Suggested fields:

- `id`
- `job_item_id`
- `source_type`
- `url`
- `title`
- `snippet`
- `relevance_score`
- `trust_score`
- `supports_claim`
- `created_at`

#### `analysis_reviews`

Stores human review and approval actions.

Suggested fields:

- `id`
- `job_item_id`
- `activity_id`
- `review_action`
- `review_note`
- `reviewed_by`
- `created_at`

## Output Schema

The final draft returned by the verdict layer must be strongly typed.

Minimum fields:

- `status`: `pass | watch | reject`
- `summary`
- `reasons[]`
- `risk_flags[]`
- `recommended_action`
- `confidence`
- `structured`
- `evidence_summary`
- `research_state`
- `needs_manual_review`

### Structured Sub-Object

Suggested fields:

- `roi_level`
- `effort_level`
- `payout_speed`
- `reward_clarity`
- `source_credibility`
- `solo_fit`
- `urgency`
- `reward_estimate_present`
- `trust_red_flags`
- `should_deep_research`

## Model Routing Strategy

### Routing Dimensions

The first release uses:

- task type
- budget cap

Each job carries:

- `route_policy`
- `budget_policy`

### Model Roles

#### `screening_model`

Use for:

- low-cost batch screening
- first-pass structured extraction

Requirements:

- low latency
- low cost
- stable structured output

#### `research_model`

Use for:

- evidence collection
- web-grounded comparison
- multi-document reasoning

Requirements:

- strong long-context support
- tool-use friendliness
- robust summarization across evidence sources

#### `verdict_model`

Use for:

- final structured normalization
- summary consolidation
- consistency enforcement

Requirements:

- stable JSON output
- good instruction compliance

### Downgrade Rules

- batch screening may downgrade to a cheaper backup model
- research may downgrade to a standard backup if primary fails
- verdict may retry once, then mark incomplete
- downgrade events must be logged explicitly

No silent fallback is allowed.

## Budget Strategy

### Budget Layers

1. `job_budget`
2. `item_budget`
3. `step_budget`

### Hard Limits

The first release should define:

- max model calls per item
- max URLs fetched per item
- max pages per domain
- max research time per item

### Failure Semantics

If research fails due to budget or network:

- do not silently pretend the item was fully researched
- downgrade result to `watch` or `insufficient_evidence`
- mark `research_unavailable` or similar explicit state

## Network Access Policy

### Default Behavior

Screening does not browse by default.

### Research Escalation Conditions

Escalate only when one or more apply:

- high-value opportunity
- low screening confidence
- conflicting signals
- reward ambiguity
- organizer ambiguity
- manual deep-analysis request

### Allowed External Source Classes

The first release should limit research to:

- original activity page / official site
- directly relevant search results
- a small set of trusted public sources

### Evidence Priority

Evidence should be weighted roughly in this order:

1. official event page or official site
2. organizer site or historical official pages
3. reputable media or trusted communities
4. forums and social supplements

Low-priority evidence should not easily override high-priority official evidence.

## Frontend Design

### Opportunity Pool

Upgrade the opportunity pool into a batch review surface.

Add:

- latest batch job banner
- draft-only and low-confidence filters
- batch approve / reject / deep-research actions
- richer analysis card content

### Activity Detail

Use detail view as the primary single-item analysis surface.

Add:

- AI verdict card
- structured factor card
- evidence panel
- execution summary panel
- review and writeback actions

### Analysis Results

Reposition this page as a job operations console.

It should show:

- job list
- job health
- job detail and per-item failures

### Templates

Reposition templates as business-preference templates, not low-level routing editors.

Template scope:

- money-first vs trust-first preference
- preferred risk tolerance
- preferred opportunity profile

Not template scope:

- provider-specific model routing
- hard infrastructure budget knobs

### Status Model

Keep analysis outcome and review state separate.

- `analysis_result_status`: `pass | watch | reject`
- `review_status`: `draft | approved | rejected | edited`

## API Surface

Additive APIs should support the new harness rather than overwrite the current app shape.

Recommended areas:

- create and query jobs
- get job item detail
- get step trace summary
- get evidence records
- approve / edit / reject drafts
- rerun one item or one job

Examples:

- `POST /api/agent-analysis/jobs`
- `GET /api/agent-analysis/jobs`
- `GET /api/agent-analysis/jobs/{job_id}`
- `GET /api/agent-analysis/items/{item_id}`
- `POST /api/agent-analysis/items/{item_id}/approve`
- `POST /api/agent-analysis/items/{item_id}/reject`
- `POST /api/agent-analysis/items/{item_id}/rerun`

The existing activity detail and list endpoints should expose approved snapshot fields only, plus latest-draft metadata where appropriate.

## Observability

The system must expose enough information to debug routing, cost, and reliability.

### Required Metrics

#### Job Level

- total jobs
- success rate
- average latency
- draft counts
- deep-research rate

#### Item Level

- steps completed
- failure step
- research triggered or not
- downgrade occurred or not

#### Step Level

- model name
- latency
- token usage
- retry count
- schema-valid or not

## Testing Strategy

### Test Layers

1. unit tests
2. agent contract tests
3. orchestration flow tests
4. frontend/backend integration tests
5. evaluation-set replay tests

### Evaluation Set

Build a small manually reviewed corpus of real opportunities and use it to compare:

- `pass/watch/reject`
- structured outputs
- risk recognition
- recommended action quality

This becomes the regression guardrail for prompt, routing, and model changes.

## Safety Boundaries

The first release must enforce:

- no direct autonomous writeback to approved snapshots
- no unrestricted browsing
- no acceptance of invalid structured outputs
- no display of raw hidden reasoning
- no silent downgrade
- no merging of partial analysis into approved snapshot

Only approved results update activity-level snapshot fields.

## Versioning and Governance

Each run should record:

- `prompt_version`
- `route_policy_version`
- `budget_policy_version`
- `schema_version`
- `model_version`

This allows investigation when output quality shifts after system changes.

## Rollout Plan

### Phase 1

- introduce run manager and draft model
- add screening agent
- add manual single-item deep analysis
- keep writeback human-gated

### Phase 2

- enable scheduled batch screening
- enable conditional research escalation
- expose job operations console

### Phase 3

- improve review ergonomics
- expand evidence ranking
- use review feedback for prompt and routing optimization

## Risks

### Over-Engineering

Risk:
first release becomes too heavy if the agent graph is too flexible.

Mitigation:
ship `C-lite` with central orchestration and fixed specialist roles.

### Cost Creep

Risk:
research step triggers too often.

Mitigation:
strict thresholds, item budgets, URL caps, and downgrade behavior.

### False Confidence

Risk:
users trust model output without enough evidence.

Mitigation:
show evidence state explicitly, require human approval, separate draft from approved snapshot.

### UI Confusion

Risk:
users mix AI result status with human review state.

Mitigation:
keep those states separate in both storage and UI.

## Open Decisions Deferred to Implementation Planning

- exact provider abstraction interface for multi-model routing
- detailed database migration sequencing
- whether evidence fetching should reuse current scraping utilities or use a separate research fetcher
- exact job scheduling cadence and candidate selection rules
- exact approval UX for batch edits vs single-item edits

## Recommendation

Proceed with implementation planning using this architecture:

- central harness
- specialist agents
- layered research
- strict structured output
- rules as safety gate
- human review before writeback

This preserves the product work already done while replacing the fake-AI core with a real, operable agent system.
