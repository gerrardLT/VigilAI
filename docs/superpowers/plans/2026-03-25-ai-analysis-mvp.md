# AI Intelligent Analysis MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a configurable, template-driven AI analysis layer that helps users filter opportunities for low-effort, fast-return, high-ROI “搞钱” outcomes.

**Architecture:** Add a backend analysis domain that stores template rules, generates AI-assisted analysis fields, and runs layered filtering and ranking over opportunities. Expose the results through additive APIs, then surface them in the existing `工作台 / 机会池 / 详情页` flows with a new template-center management UI.

**Tech Stack:** FastAPI, SQLite, Pydantic, React, TypeScript, existing hooks/service layer, Vitest, pytest.

---

## File Structure

### Backend

- Create: `app/backend/analysis/__init__.py`
- Create: `app/backend/analysis/template_defaults.py`
- Create: `app/backend/analysis/rule_engine.py`
- Create: `app/backend/analysis/ai_enrichment.py`
- Modify: `app/backend/models.py`
- Modify: `app/backend/data_manager.py`
- Modify: `app/backend/api.py`
- Test: `app/backend/tests/test_analysis_templates.py`
- Test: `app/backend/tests/test_analysis_rule_engine.py`
- Test: `app/backend/tests/test_analysis_api.py`

### Frontend

- Create: `app/frontend/src/types/analysis.ts`
- Modify: `app/frontend/src/types/index.ts`
- Modify: `app/frontend/src/services/api.ts`
- Create: `app/frontend/src/hooks/useAnalysisTemplates.ts`
- Create: `app/frontend/src/hooks/useAnalysisResults.ts`
- Create: `app/frontend/src/components/analysis/TemplateSummaryBar.tsx`
- Create: `app/frontend/src/components/analysis/UnsavedChangesBar.tsx`
- Create: `app/frontend/src/components/analysis/LayeredFilterPanel.tsx`
- Create: `app/frontend/src/components/analysis/AnalysisResultBadge.tsx`
- Create: `app/frontend/src/components/analysis/ReasonChainCollapse.tsx`
- Create: `app/frontend/src/pages/TemplateCenterPage.tsx`
- Create: `app/frontend/src/pages/TemplateCenterPage.test.tsx`
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`
- Modify: `app/frontend/src/pages/ActivityDetailPage.tsx`
- Modify: `app/frontend/src/pages/ActivityDetailActions.test.tsx`
- Modify: `app/frontend/src/pages/WorkspacePage.tsx`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/Header.tsx`

### Docs

- Reference: `docs/AI智能分析交互设计方案.md`

---

### Task 1: Add analysis template data models and persistence

**Files:**
- Create: `app/backend/tests/test_analysis_templates.py`
- Modify: `app/backend/models.py`
- Modify: `app/backend/data_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_data_manager_creates_default_analysis_templates():
    dm = DataManager(db_path=temp_db)
    templates = dm.get_analysis_templates()
    assert {item["slug"] for item in templates} >= {
        "quick-money",
        "low-effort-high-roi",
        "safe-trust",
    }


def test_data_manager_can_duplicate_and_activate_template():
    clone = dm.duplicate_analysis_template(default_id, "Fast money v2")
    dm.set_default_analysis_template(clone["id"])
    assert dm.get_default_analysis_template()["id"] == clone["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_templates.py -q`  
Expected: FAIL because analysis template APIs and storage do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement:
- new Pydantic models for analysis templates, layers, conditions, and runtime adjustments
- SQLite tables in `DataManager._init_db()`
- default template seeding in `template_defaults.py`
- `get_analysis_templates()`, `get_default_analysis_template()`, `create_analysis_template()`, `duplicate_analysis_template()`, `set_default_analysis_template()`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_templates.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/models.py app/backend/data_manager.py app/backend/analysis/template_defaults.py app/backend/tests/test_analysis_templates.py
git commit -m "feat: add analysis template persistence"
```

### Task 2: Build layered rule engine

**Files:**
- Create: `app/backend/tests/test_analysis_rule_engine.py`
- Create: `app/backend/analysis/rule_engine.py`
- Modify: `app/backend/data_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_rule_engine_filters_activity_at_hard_gate_layer():
    result = run_analysis(activity, template)
    assert result.status == "rejected"
    assert result.failed_layer == "hard_gate"


def test_rule_engine_marks_borderline_activity_as_watchlist():
    result = run_analysis(activity, template)
    assert result.status == "watch"
    assert result.layer_results[1]["decision"] == "borderline"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_rule_engine.py -q`  
Expected: FAIL because no rule engine exists.

- [ ] **Step 3: Write minimal implementation**

Implement:
- layered evaluation in `rule_engine.py`
- support four layers: `hard_gate`, `roi`, `trust`, `priority`
- support rule properties: `enabled`, `threshold`, `strictness`, `hard_fail`
- output a normalized result object containing:
  - status
  - failed layer
  - layer decisions
  - score breakdown
  - folded summary reasons

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_rule_engine.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/analysis/rule_engine.py app/backend/tests/test_analysis_rule_engine.py app/backend/data_manager.py
git commit -m "feat: add layered analysis rule engine"
```

### Task 3: Add AI enrichment fields before rule evaluation

**Files:**
- Modify: `app/backend/models.py`
- Create: `app/backend/analysis/ai_enrichment.py`
- Modify: `app/backend/data_manager.py`
- Extend: `app/backend/tests/test_analysis_rule_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ai_enrichment_extracts_money_and_effort_fields():
    fields = enrich_activity_for_analysis(activity)
    assert fields["roi_level"] in {"low", "medium", "high"}
    assert fields["solo_friendliness"] == "solo_friendly"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_rule_engine.py -q`  
Expected: FAIL because enrichment fields are missing.

- [ ] **Step 3: Write minimal implementation**

Implement:
- AI-enrichment service that converts activity text into normalized analysis fields
- first version should be deterministic/rule-assisted placeholders, not external LLM dependency
- persist analysis field payload on each activity analysis result
- store confidence per field

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_rule_engine.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/models.py app/backend/analysis/ai_enrichment.py app/backend/data_manager.py app/backend/tests/test_analysis_rule_engine.py
git commit -m "feat: add ai enrichment fields for analysis"
```

### Task 4: Expose analysis APIs and bind them to existing opportunity reads

**Files:**
- Create: `app/backend/tests/test_analysis_api.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/data_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_get_analysis_templates_endpoint(client):
    response = client.get("/api/analysis/templates")
    assert response.status_code == 200


def test_preview_template_returns_pass_watch_reject_buckets(client):
    response = client.post("/api/analysis/templates/default/preview", json={"overrides": {...}})
    body = response.json()
    assert "passed" in body
    assert "watch" in body
    assert "rejected" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_api.py -q`  
Expected: FAIL because analysis endpoints do not exist.

- [ ] **Step 3: Write minimal implementation**

Add endpoints:
- `GET /api/analysis/templates`
- `POST /api/analysis/templates`
- `PATCH /api/analysis/templates/{id}`
- `POST /api/analysis/templates/{id}/duplicate`
- `POST /api/analysis/templates/{id}/preview`
- `POST /api/analysis/run`
- `GET /api/analysis/results`
- `GET /api/analysis/results/{activity_id}`

Also:
- add current template context to opportunity list/detail payloads
- return folded reasons plus expandable reason chain

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_api.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/api.py app/backend/data_manager.py app/backend/tests/test_analysis_api.py
git commit -m "feat: add analysis api surface"
```

### Task 5: Add frontend analysis types and data hooks

**Files:**
- Create: `app/frontend/src/types/analysis.ts`
- Modify: `app/frontend/src/types/index.ts`
- Modify: `app/frontend/src/services/api.ts`
- Create: `app/frontend/src/hooks/useAnalysisTemplates.ts`
- Create: `app/frontend/src/hooks/useAnalysisResults.ts`

- [ ] **Step 1: Write the failing tests**

Add/extend tests for hooks and API methods:

```ts
it('loads templates and default template context', async () => {
  const { result } = renderHook(() => useAnalysisTemplates())
  await waitFor(() => expect(result.current.templates.length).toBeGreaterThan(0))
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/hooks/useAnalysisTemplates.test.tsx src/hooks/useAnalysisResults.test.tsx`  
Expected: FAIL because hooks/types do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:
- analysis template/result types
- API client methods for new analysis endpoints
- hooks for loading templates, previewing overrides, and reading per-activity analysis result

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/hooks/useAnalysisTemplates.test.tsx src/hooks/useAnalysisResults.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/types/analysis.ts app/frontend/src/types/index.ts app/frontend/src/services/api.ts app/frontend/src/hooks/useAnalysisTemplates.ts app/frontend/src/hooks/useAnalysisResults.ts
git commit -m "feat: add frontend analysis data layer"
```

### Task 6: Build reusable analysis UI components

**Files:**
- Create: `app/frontend/src/components/analysis/TemplateSummaryBar.tsx`
- Create: `app/frontend/src/components/analysis/UnsavedChangesBar.tsx`
- Create: `app/frontend/src/components/analysis/LayeredFilterPanel.tsx`
- Create: `app/frontend/src/components/analysis/AnalysisResultBadge.tsx`
- Create: `app/frontend/src/components/analysis/ReasonChainCollapse.tsx`
- Create: component tests alongside or in page tests

- [ ] **Step 1: Write the failing tests**

Add tests covering:
- summary bar shows active template and overrides
- unsaved changes bar appears only when runtime overrides exist
- reason chain remains collapsed by default

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/components/analysis/*.test.tsx`  
Expected: FAIL because components do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement focused reusable components with existing Tailwind patterns.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/components/analysis/*.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/components/analysis
git commit -m "feat: add reusable analysis ui components"
```

### Task 7: Add template-center management UI

**Files:**
- Create: `app/frontend/src/pages/TemplateCenterPage.tsx`
- Create: `app/frontend/src/pages/TemplateCenterPage.test.tsx`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/Header.tsx`

- [ ] **Step 1: Write the failing tests**

```ts
it('duplicates a template and sets a new default', async () => {
  render(<TemplateCenterPage />)
  await user.click(screen.getByRole('button', { name: /复制模板/i }))
  expect(api.duplicateAnalysisTemplate).toHaveBeenCalled()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/pages/TemplateCenterPage.test.tsx`  
Expected: FAIL because page and route do not exist.

- [ ] **Step 3: Write minimal implementation**

Add:
- template list
- duplicate, rename, set default, delete
- preview before save
- route and nav entry

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/pages/TemplateCenterPage.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/pages/TemplateCenterPage.tsx app/frontend/src/pages/TemplateCenterPage.test.tsx app/frontend/src/App.tsx app/frontend/src/components/Header.tsx
git commit -m "feat: add analysis template center"
```

### Task 8: Integrate analysis into opportunity pool

**Files:**
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- active template banner
- left-side layered filter panel
- result buckets: pass/watch/reject
- runtime override indicator
- save-as-template action

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/pages/OpportunityPoolPage.test.tsx`  
Expected: FAIL because analysis UI is not integrated.

- [ ] **Step 3: Write minimal implementation**

Implement:
- template summary bar
- layered filter panel on the left
- opportunity cards showing result badge and folded reasons
- runtime overrides workflow

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/pages/OpportunityPoolPage.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/pages/ActivitiesPage.tsx app/frontend/src/pages/OpportunityPoolPage.test.tsx
git commit -m "feat: add analysis-driven opportunity pool"
```

### Task 9: Integrate analysis into detail page and workspace

**Files:**
- Modify: `app/frontend/src/pages/ActivityDetailPage.tsx`
- Modify: `app/frontend/src/pages/ActivityDetailActions.test.tsx`
- Modify: `app/frontend/src/pages/WorkspacePage.tsx`
- Modify: `app/frontend/src/pages/WorkspacePage.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- detail page shows folded analysis decision and expandable reason chain
- workspace shows active template and today’s high-ROI picks

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/pages/ActivityDetailActions.test.tsx src/pages/WorkspacePage.test.tsx`  
Expected: FAIL because analysis panels are not wired in.

- [ ] **Step 3: Write minimal implementation**

Implement:
- detail page decision panel above summary
- workspace summary of current template and rejected reason distribution
- links from detail page back to opportunity pool with template context

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/pages/ActivityDetailActions.test.tsx src/pages/WorkspacePage.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/pages/ActivityDetailPage.tsx app/frontend/src/pages/ActivityDetailActions.test.tsx app/frontend/src/pages/WorkspacePage.tsx app/frontend/src/pages/WorkspacePage.test.tsx
git commit -m "feat: surface analysis in detail and workspace"
```

### Task 10: Final verification and docs alignment

**Files:**
- Verify: `docs/AI智能分析交互设计方案.md`
- Verify: `docs/superpowers/plans/2026-03-25-ai-analysis-mvp.md`

- [ ] **Step 1: Run backend test suite**

Run: `python -m pytest tests -q`  
Expected: PASS

- [ ] **Step 2: Run frontend targeted suites**

Run: `npm test -- --run src/pages/TemplateCenterPage.test.tsx src/pages/OpportunityPoolPage.test.tsx src/pages/ActivityDetailActions.test.tsx src/pages/WorkspacePage.test.tsx`  
Expected: PASS

- [ ] **Step 3: Run frontend build**

Run: `npm run build`  
Expected: PASS, or the known Windows `spawn EPERM` issue documented if still present.

- [ ] **Step 4: Update docs if implementation drift appears**

Make sure the interaction design doc still matches shipped behavior.

- [ ] **Step 5: Commit**

```bash
git add docs/AI智能分析交互设计方案.md docs/superpowers/plans/2026-03-25-ai-analysis-mvp.md
git commit -m "docs: finalize ai analysis mvp plan"
```

---

## Implementation Notes

- Keep AI enrichment deterministic in MVP; do not block the system on external model calls.
- Treat `watch` as a first-class bucket, not a UI afterthought.
- Keep template overrides ephemeral until the user explicitly saves them.
- Default all reason chains to collapsed in UI.
- Preserve current V2 route structure; add template center without removing existing pages.

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
