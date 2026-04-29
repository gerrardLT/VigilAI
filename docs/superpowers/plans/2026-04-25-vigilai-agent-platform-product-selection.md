# VigilAI Agent Platform + Product Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade VigilAI from an `Activity`-centric workbench into an agent-native intelligence platform, then add product-selection as a second bounded context on top of the shared platform.

**Architecture:** Build a shared agent platform layer with session, turn, artifact, job, and tool-routing primitives while keeping current opportunity flows running. Integrate the current developer-opportunity domain as the first domain adapter, then add a separate `product_selection` domain with its own tables, APIs, pages, and scoring logic.

**Tech Stack:** FastAPI, Python, SQLite, React 18, TypeScript, Vite, existing OpenAI provider router, existing APScheduler/scraper stack.

---

### Task 1: Establish Shared Agent Platform Schema And Repositories

**Files:**
- Create: `app/backend/agent_platform/__init__.py`
- Create: `app/backend/agent_platform/models.py`
- Create: `app/backend/agent_platform/repository.py`
- Create: `app/backend/agent_platform/state_machine.py`
- Create: `app/backend/tests/test_agent_platform_repository.py`
- Modify: `app/backend/data_manager.py`
- Modify: `app/backend/models.py`

- [x] **Step 1: Write the failing repository tests**

```python
def test_create_agent_session_persists_default_status():
    repo = AgentPlatformRepository(temp_db_path)
    session = repo.create_session(domain_type="opportunity", entry_mode="chat")
    assert session.status == "active"


def test_append_turn_and_list_turns_for_session():
    repo = AgentPlatformRepository(temp_db_path)
    session = repo.create_session(domain_type="opportunity", entry_mode="chat")
    repo.append_turn(session.id, role="user", content="Find solo-friendly grants")
    turns = repo.list_turns(session.id)
    assert len(turns) == 1
    assert turns[0].role == "user"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd app/backend; pytest tests/test_agent_platform_repository.py -v`
Expected: FAIL with missing module or missing repository methods.

- [x] **Step 3: Write minimal shared platform models and repository**

```python
class AgentSession(BaseModel):
    id: str
    domain_type: str
    entry_mode: str
    status: str


class AgentPlatformRepository:
    def create_session(self, *, domain_type: str, entry_mode: str) -> AgentSession: ...
    def append_turn(self, session_id: str, *, role: str, content: str) -> AgentTurn: ...
    def list_turns(self, session_id: str) -> list[AgentTurn]: ...
```

- [x] **Step 4: Extend SQLite initialization with new tables**

Add tables:
- `agent_sessions`
- `agent_turns`
- `agent_artifacts`
- `agent_jobs_v2`

Expected behavior:
- Existing app startup still works
- Old business tables remain unchanged
- New tables are created automatically on boot

- [x] **Step 5: Run tests to verify repository behavior**

Run: `cd app/backend; pytest tests/test_agent_platform_repository.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/backend/agent_platform app/backend/data_manager.py app/backend/models.py app/backend/tests/test_agent_platform_repository.py
git commit -m "feat: add shared agent platform schema and repository"
```

### Task 2: Add Conversation Engine And Agent Platform APIs

**Files:**
- Create: `app/backend/agent_platform/conversation_engine.py`
- Create: `app/backend/agent_platform/tool_router.py`
- Create: `app/backend/agent_platform/artifact_service.py`
- Create: `app/backend/tests/test_agent_platform_api.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/main.py`

- [x] **Step 1: Write failing API tests for session and turn endpoints**

```python
def test_create_agent_session_returns_session_id(client):
    response = client.post("/api/agent/sessions", json={"domain_type": "opportunity", "entry_mode": "chat"})
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_post_turn_returns_assistant_reply_and_turns(client):
    session = client.post("/api/agent/sessions", json={"domain_type": "opportunity", "entry_mode": "chat"}).json()
    response = client.post(f"/api/agent/sessions/{session['id']}/turns", json={"content": "帮我找 grant"})
    assert response.status_code == 200
    assert "assistant_turn" in response.json()
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd app/backend; pytest tests/test_agent_platform_api.py -v`
Expected: FAIL with 404 endpoints.

- [x] **Step 3: Implement minimal conversation engine and state machine**

```python
class ConversationEngine:
    def reply(self, *, session, user_turn) -> ConversationReply:
        return ConversationReply(
            assistant_turn="我先帮你明确筛选目标。",
            next_state="active",
            artifacts=[],
            tool_calls=[],
        )
```

- [x] **Step 4: Add `/api/agent/*` routes**

Required endpoints:
- `POST /api/agent/sessions`
- `GET /api/agent/sessions/{id}`
- `POST /api/agent/sessions/{id}/turns`
- `GET /api/agent/sessions/{id}/turns`
- `GET /api/agent/sessions/{id}/artifacts`

- [x] **Step 5: Run API tests**

Run: `cd app/backend; pytest tests/test_agent_platform_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/backend/agent_platform app/backend/api.py app/backend/main.py app/backend/tests/test_agent_platform_api.py
git commit -m "feat: add shared agent platform conversation api"
```

### Task 3: Add Frontend Agent Workspace Shell

**Files:**
- Create: `app/frontend/src/types/agentPlatform.ts`
- Create: `app/frontend/src/services/agentPlatformApi.ts`
- Create: `app/frontend/src/hooks/useAgentSession.ts`
- Create: `app/frontend/src/pages/AgentWorkspacePage.tsx`
- Create: `app/frontend/src/pages/AgentWorkspacePage.test.tsx`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/Header.tsx`

- [x] **Step 1: Write failing page test**

```tsx
it('creates a session and sends a user turn', async () => {
  render(<AgentWorkspacePage />)
  await user.type(screen.getByRole('textbox'), '帮我找值得跟进的 grant')
  await user.click(screen.getByRole('button', { name: '发送' }))
  expect(await screen.findByText(/帮我明确筛选目标/)).toBeInTheDocument()
})
```

- [x] **Step 2: Run the page test**

Run: `cd app/frontend; npm test -- AgentWorkspacePage.test.tsx`
Expected: FAIL with missing page or missing mocked API.

- [x] **Step 3: Implement minimal page, hook, and API service**

```tsx
export function AgentWorkspacePage() {
  const { turns, sendTurn, createSession } = useAgentSession('opportunity')
  return <main>{/* chat shell + turns + input */}</main>
}
```

- [x] **Step 4: Register route and nav link**

Add:
- `/agent`
- header link label like `Agent`

- [x] **Step 5: Run the frontend test**

Run: `cd app/frontend; npm test -- AgentWorkspacePage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/types/agentPlatform.ts app/frontend/src/services/agentPlatformApi.ts app/frontend/src/hooks/useAgentSession.ts app/frontend/src/pages/AgentWorkspacePage.tsx app/frontend/src/pages/AgentWorkspacePage.test.tsx app/frontend/src/App.tsx app/frontend/src/components/Header.tsx
git commit -m "feat: add frontend agent workspace shell"
```

### Task 4: Integrate Current Opportunity Domain As First Agent Toolset

**Files:**
- Create: `app/backend/opportunity_domain/__init__.py`
- Create: `app/backend/opportunity_domain/service.py`
- Create: `app/backend/opportunity_domain/tools.py`
- Create: `app/backend/tests/test_opportunity_agent_tools.py`
- Modify: `app/backend/agent_platform/tool_router.py`
- Modify: `app/backend/analysis/run_manager.py`
- Modify: `app/backend/data_manager.py`

- [x] **Step 1: Write failing tool-router tests**

```python
def test_router_uses_opportunity_search_tool_for_opportunity_session():
    router = ToolRouter(tool_registry=build_default_registry())
    selected = router.resolve_tools(domain_type="opportunity", user_message="帮我找值得跟进的赏金")
    assert "opportunity_search" in selected
```

- [x] **Step 2: Run tests to verify tool selection is missing**

Run: `cd app/backend; pytest tests/test_opportunity_agent_tools.py -v`
Expected: FAIL with no registered opportunity tools.

- [x] **Step 3: Implement opportunity domain service and tools**

```python
class OpportunitySearchTool:
    name = "opportunity_search"

    def run(self, *, query: str, filters: dict | None = None) -> dict:
        return {"items": [...], "summary": "..."}
```

- [x] **Step 4: Connect tool router to existing activities/tracking capability**

Non-goals:
- Do not rewrite `/api/activities`
- Do not delete current agent-analysis endpoints

Goals:
- Agent session can search activities
- Agent session can explain an activity
- Agent session can suggest a next action

- [x] **Step 5: Run tests**

Run: `cd app/backend; pytest tests/test_opportunity_agent_tools.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/backend/opportunity_domain app/backend/agent_platform/tool_router.py app/backend/analysis/run_manager.py app/backend/data_manager.py app/backend/tests/test_opportunity_agent_tools.py
git commit -m "feat: integrate opportunity domain with shared agent tools"
```

### Task 5: Add Product Selection Backend Bounded Context

**Files:**
- Create: `app/backend/product_selection/__init__.py`
- Create: `app/backend/product_selection/models.py`
- Create: `app/backend/product_selection/repository.py`
- Create: `app/backend/product_selection/service.py`
- Create: `app/backend/product_selection/scoring.py`
- Create: `app/backend/product_selection/ai_explainer.py`
- Create: `app/backend/product_selection/adapters/taobao.py`
- Create: `app/backend/product_selection/adapters/xianyu.py`
- Create: `app/backend/tests/test_product_selection_repository.py`
- Create: `app/backend/tests/test_product_selection_api.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/data_manager.py`

- [x] **Step 1: Write failing repository tests for selection queries and opportunities**

```python
def test_create_selection_query_persists_platform_scope():
    repo = ProductSelectionRepository(temp_db_path)
    query = repo.create_query(query_type="keyword", query_text="蓝牙标签", platform_scope="both")
    assert query.platform_scope == "both"


def test_store_selection_opportunity_links_to_query():
    repo = ProductSelectionRepository(temp_db_path)
    query = repo.create_query(query_type="keyword", query_text="蓝牙标签", platform_scope="both")
    item = repo.create_opportunity(query_id=query.id, platform="taobao", title="蓝牙防丢器")
    assert item.query_id == query.id
```

- [x] **Step 2: Run the repository test**

Run: `cd app/backend; pytest tests/test_product_selection_repository.py -v`
Expected: FAIL because repository and tables do not exist.

- [x] **Step 3: Implement bounded-context tables and repository**

Required tables:
- `selection_queries`
- `selection_opportunities`
- `selection_opportunity_signals`
- `selection_tracking_items`

- [x] **Step 4: Add first API slice**

Required endpoints:
- `POST /api/product-selection/research-jobs`
- `GET /api/product-selection/research-jobs/{job_id}`
- `GET /api/product-selection/opportunities`
- `GET /api/product-selection/opportunities/{id}`
- `POST/PATCH/DELETE /api/product-selection/tracking/{id}`
- `GET /api/product-selection/workspace`

- [x] **Step 5: Run repository and API tests**

Run: `cd app/backend; pytest tests/test_product_selection_repository.py tests/test_product_selection_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/backend/product_selection app/backend/api.py app/backend/data_manager.py app/backend/tests/test_product_selection_repository.py app/backend/tests/test_product_selection_api.py
git commit -m "feat: add product selection backend bounded context"
```

### Task 6: Add Product Selection Frontend Workbench

**Files:**
- Create: `app/frontend/src/types/productSelection.ts`
- Create: `app/frontend/src/services/productSelectionApi.ts`
- Create: `app/frontend/src/hooks/useProductSelection.ts`
- Create: `app/frontend/src/hooks/useProductSelectionTracking.ts`
- Create: `app/frontend/src/pages/selection/SelectionWorkspacePage.tsx`
- Create: `app/frontend/src/pages/selection/SelectionOpportunitiesPage.tsx`
- Create: `app/frontend/src/pages/selection/SelectionOpportunityDetailPage.tsx`
- Create: `app/frontend/src/pages/selection/SelectionComparePage.tsx`
- Create: `app/frontend/src/pages/selection/SelectionTrackingPage.tsx`
- Create: `app/frontend/src/pages/selection/SelectionOpportunitiesPage.test.tsx`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/Header.tsx`

- [x] **Step 1: Write failing workbench tests**

```tsx
it('renders product selection opportunities with platform filters', async () => {
  render(<SelectionOpportunitiesPage />)
  expect(await screen.findByText('平台')).toBeInTheDocument()
  expect(await screen.findByText(/机会分/)).toBeInTheDocument()
})
```

- [x] **Step 2: Run the page test**

Run: `cd app/frontend; npm test -- SelectionOpportunitiesPage.test.tsx`
Expected: FAIL because page and service do not exist.

- [x] **Step 3: Implement selection types, service, hooks, and pages**

Minimum pages:
- workspace
- list
- detail
- compare
- tracking

- [x] **Step 4: Register `/selection/*` routes**

Add routes:
- `/selection/workspace`
- `/selection/opportunities`
- `/selection/opportunities/:id`
- `/selection/compare`
- `/selection/tracking`

- [x] **Step 5: Run the frontend tests**

Run: `cd app/frontend; npm test -- SelectionOpportunitiesPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/types/productSelection.ts app/frontend/src/services/productSelectionApi.ts app/frontend/src/hooks/useProductSelection.ts app/frontend/src/hooks/useProductSelectionTracking.ts app/frontend/src/pages/selection app/frontend/src/App.tsx app/frontend/src/components/Header.tsx
git commit -m "feat: add product selection frontend workbench"
```

### Task 7: Register Product Selection As Second Agent Toolset

**Files:**
- Create: `app/backend/product_selection/tools.py`
- Create: `app/backend/tests/test_product_selection_agent_tools.py`
- Modify: `app/backend/agent_platform/tool_router.py`
- Modify: `app/backend/agent_platform/conversation_engine.py`
- Modify: `app/frontend/src/pages/AgentWorkspacePage.tsx`

- [x] **Step 1: Write failing tests for selection-domain tool routing**

```python
def test_router_uses_selection_query_tool_for_selection_session():
    router = ToolRouter(tool_registry=build_default_registry())
    selected = router.resolve_tools(domain_type="product_selection", user_message="淘宝上的宠物饮水机还值得做吗")
    assert "selection_query" in selected
```

- [x] **Step 2: Run test to verify selection tools are not wired**

Run: `cd app/backend; pytest tests/test_product_selection_agent_tools.py -v`
Expected: FAIL because selection tools are unregistered.

- [x] **Step 3: Implement selection tool adapter set**

```python
class SelectionQueryTool:
    name = "selection_query"

    def run(self, *, query: str) -> dict:
        return {"shortlist": [...], "artifacts": [...]}
```

- [x] **Step 4: Update conversation engine and frontend session creation**

Goals:
- Agent workspace can start `domain_type="product_selection"` sessions
- Assistant can ask follow-up questions before querying
- Returned shortlist/artifacts can deep-link into `/selection/*`

- [x] **Step 5: Run backend and frontend tests**

Run: `cd app/backend; pytest tests/test_product_selection_agent_tools.py -v`
Run: `cd app/frontend; npm test -- AgentWorkspacePage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/backend/product_selection/tools.py app/backend/agent_platform/tool_router.py app/backend/agent_platform/conversation_engine.py app/backend/tests/test_product_selection_agent_tools.py app/frontend/src/pages/AgentWorkspacePage.tsx
git commit -m "feat: add product selection agent tool routing"
```

### Task 8: Stabilization, Migration Notes, And Documentation

**Files:**
- Create: `app/backend/tests/test_agent_platform_smoke.py`
- Modify: `README.md`
- Modify: `docs/当前系统架构与技术实现说明.md`
- Modify: `docs/MirrorMind_V2_架构映射与平台选品改造方案.md`

- [x] **Step 1: Write a smoke test covering both domains**

```python
def test_agent_platform_supports_opportunity_and_selection_domains(client):
    opportunity = client.post("/api/agent/sessions", json={"domain_type": "opportunity", "entry_mode": "chat"})
    selection = client.post("/api/agent/sessions", json={"domain_type": "product_selection", "entry_mode": "chat"})
    assert opportunity.status_code == 200
    assert selection.status_code == 200
```

- [ ] **Step 2: Run the smoke test**

Run: `cd app/backend; pytest tests/test_agent_platform_smoke.py -v`
Expected: FAIL until both domains are wired.

- [x] **Step 3: Document migration rules**

Must document:
- old routes remain supported
- old tables remain readable
- new platform tables are additive
- product selection is isolated from `Activity`

- [ ] **Step 4: Run the full targeted verification set**

Run: `cd app/backend; pytest tests/test_agent_platform_repository.py tests/test_agent_platform_api.py tests/test_opportunity_agent_tools.py tests/test_product_selection_repository.py tests/test_product_selection_api.py tests/test_product_selection_agent_tools.py tests/test_agent_platform_smoke.py -v`

Run: `cd app/frontend; npm test -- AgentWorkspacePage.test.tsx SelectionOpportunitiesPage.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/tests/test_agent_platform_smoke.py README.md docs/当前系统架构与技术实现说明.md docs/MirrorMind_V2_架构映射与平台选品改造方案.md
git commit -m "docs: finalize agent platform migration notes"
```
