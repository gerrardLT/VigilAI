# VigilAI

VigilAI is now structured as a shared agent platform with two bounded contexts:

- `opportunity`: developer opportunity discovery, analysis, and follow-up
- `product_selection`: Taobao / Xianyu product research, shortlist, compare, and tracking

The system keeps the legacy opportunity workbench intact while introducing a unified `/agent` entry that can route work into either domain.

## Architecture Summary

### Backend

- `app/backend/agent_platform/`
  - shared session, turn, artifact, job, and tool-routing primitives
  - conversation engine for `/api/agent/*`
- `app/backend/opportunity_domain/`
  - wraps existing activity data and tracking flows as agent tools
- `app/backend/product_selection/`
  - isolated bounded context for platform-selection research, scoring, tracking, and compare
- `app/backend/api.py`
  - legacy APIs remain available
  - new shared agent endpoints and product-selection endpoints are additive

### Frontend

- `/agent`
  - shared agent workspace
  - domain switch between `opportunity` and `product_selection`
- `/selection/*`
  - structured workbench for product-selection research
- existing `/workspace`, `/activities`, `/tracking`, `/digests`, `/sources`, `/analysis/*`
  - remain supported

## Compatibility Rules

- Old routes remain supported. The new agent platform is additive.
- Old tables remain readable. Existing opportunity data stays in place.
- New platform tables are additive:
  - `agent_sessions`
  - `agent_turns`
  - `agent_artifacts`
  - `agent_jobs_v2`
  - `selection_queries`
  - `selection_opportunities`
  - `selection_opportunity_signals`
  - `selection_tracking_items`
- `product_selection` is isolated from `Activity` and does not reuse the legacy opportunity tables as its primary store.

## Key API Surfaces

### Shared agent platform

- `POST /api/agent/sessions`
- `GET /api/agent/sessions`
- `GET /api/agent/sessions/{id}`
- `POST /api/agent/sessions/{id}/turns`
- `GET /api/agent/sessions/{id}/turns`
- `GET /api/agent/sessions/{id}/artifacts`

### Opportunity domain

- `GET /api/activities`
- `GET /api/activities/{activity_id}`
- `POST /api/activities/ai-filter`
- `GET /api/tracking`
- `POST /api/tracking/{activity_id}`
- `PATCH /api/tracking/{activity_id}`
- `DELETE /api/tracking/{activity_id}`

### Product selection domain

- `POST /api/product-selection/research-jobs`
- `GET /api/product-selection/research-jobs/{job_id}`
- `GET /api/product-selection/opportunities`
- `GET /api/product-selection/opportunities/{id}`
- `GET /api/product-selection/tracking`
- `POST /api/product-selection/tracking/{id}`
- `PATCH /api/product-selection/tracking/{id}`
- `DELETE /api/product-selection/tracking/{id}`
- `GET /api/product-selection/workspace`

## Current Behavior Notes

- `/agent` now supports recent-session history and session restore per domain, not only new-session chat.
- `data_manager.py` has been split into `app/backend/data_manager_components/` mixins while keeping the external `DataManager` bootstrap surface stable.
- Product-selection opportunities and tracking items expose provenance fields such as `source_mode`, `source_summary`, and `fallback_reason`.
- The Taobao / Xianyu integration is truth-first:
  - the backend attempts live extraction where possible
  - when a page is shell-heavy, weak, or otherwise unreliable, the result is marked as `fallback`
  - `fallback` means the item should be read as a conservative estimate, not as verified live marketplace data

### Logged-in marketplace fixtures

- Real marketplace regression work should prefer logged-in rendered DOM fixtures over public shell HTML.
- Operator workflow: [docs/product_selection_logged_in_fixture_workflow.md](docs/product_selection_logged_in_fixture_workflow.md)
- The live adapter can consume:
  - direct HTTP fetches with cookie JSON
  - rendered DOM snapshots via `rendered_snapshot_html`

## Local Development

### Backend

```bash
cd app/backend
pip install -r requirements.txt
python main.py
```

Backend default: `http://localhost:8000`

### Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Frontend default: `http://localhost:5173`

## Verification

### Backend

```bash
cd app/backend
pytest tests/test_agent_platform_repository.py tests/test_agent_platform_api.py tests/test_opportunity_agent_tools.py tests/test_product_selection_repository.py tests/test_product_selection_api.py tests/test_product_selection_agent_tools.py tests/test_agent_platform_smoke.py -v
```

### Frontend

```bash
cd app/frontend
npm test -- AgentWorkspacePage.test.tsx SelectionOpportunitiesPage.test.tsx
npm run build
```
