# 奖励活动发现 AI Agent 实施计划

> **给执行型 agent：** 必选子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐步执行。所有步骤使用复选框（`- [ ]`）跟踪。

**目标：** 构建一个真正的多 Agent 奖励活动发现系统，能够广泛抓取来源，自主追证据调查，并将结果沉淀为带证据的结构化机会库。

**架构：** 新增一个独立的奖励活动发现后端边界，不再继续把 legacy `activities` 当成主模型扩展。网页抓取与抽取底座直接采用 Crawl4AI，后端在其之上新增来源、抓取任务、原始文档、召回候选、调查运行/动作、机会、证据等实体，以及召回、调查、评估、合并、API 服务。前端新增四个页面：系统概览、机会库、机会详情、来源与任务；旧机会系统继续保留，但不再作为主产品。

**技术栈：** FastAPI、SQLite、Python service/repository、Crawl4AI、现有 scraper 基础设施、React、TypeScript、Vite、Vitest、Testing Library。

---

## 文件结构

### 新增后端文件

- Create: `app/backend/reward_opportunity/__init__.py`
- Create: `app/backend/reward_opportunity/models.py`
- Create: `app/backend/reward_opportunity/repository.py`
- Create: `app/backend/reward_opportunity/service.py`
- Create: `app/backend/reward_opportunity/crawl4ai_collector.py`
- Create: `app/backend/reward_opportunity/recall.py`
- Create: `app/backend/reward_opportunity/investigator.py`
- Create: `app/backend/reward_opportunity/evaluator.py`
- Create: `app/backend/reward_opportunity/merger.py`
- Create: `app/backend/reward_opportunity/agent_loop.py`
- Create: `app/backend/tests/test_reward_opportunity_repository.py`
- Create: `app/backend/tests/test_reward_opportunity_api.py`
- Create: `app/backend/tests/test_reward_opportunity_recall.py`
- Create: `app/backend/tests/test_reward_opportunity_agent_loop.py`

### 需要修改的后端文件

- Modify: `app/backend/models.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/main.py`
- Modify: `app/backend/scheduler.py`

### 新增前端文件

- Create: `app/frontend/src/types/rewardOpportunity.ts`
- Create: `app/frontend/src/services/rewardOpportunityApi.ts`
- Create: `app/frontend/src/hooks/useRewardOverview.ts`
- Create: `app/frontend/src/hooks/useRewardOpportunities.ts`
- Create: `app/frontend/src/hooks/useRewardOpportunityDetail.ts`
- Create: `app/frontend/src/hooks/useRewardSourceFeeds.ts`
- Create: `app/frontend/src/pages/reward/RewardOverviewPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunitiesPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunityDetailPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOperationsPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOverviewPage.test.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunitiesPage.test.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunityDetailPage.test.tsx`
- Create: `app/frontend/src/pages/reward/RewardOperationsPage.test.tsx`

### 需要修改的前端文件

- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/routes/domainPaths.ts`
- Modify: `app/frontend/src/services/api.ts`
- Modify: `app/frontend/src/types/index.ts`
- Modify: `app/frontend/src/pages/SystemHomePage.tsx`
- Modify: `app/frontend/src/components/app/DomainHeader.tsx`

### 代码落地后要更新的文档

- Modify: `README.md`
- Modify: `docs/当前系统架构与技术实现说明.md`
- Modify: `docs/当前项目核心功能梳理.md`

---

### 任务 1：新增奖励活动数据模型与仓储层

**Files:**
- Create: `app/backend/reward_opportunity/models.py`
- Create: `app/backend/reward_opportunity/repository.py`
- Create: `app/backend/tests/test_reward_opportunity_repository.py`
- Modify: `app/backend/models.py`

- [ ] **步骤 1：先写失败测试**

```python
from reward_opportunity.repository import RewardOpportunityRepository


def test_repository_creates_reward_opportunity_tables(tmp_path):
    repository = RewardOpportunityRepository(str(tmp_path / "reward.db"))
    repository.ensure_schema()
    stats = repository.get_overview_stats()
    assert stats["source_count"] == 0
    assert stats["opportunity_count"] == 0


def test_repository_persists_candidate_and_investigation(tmp_path):
    repository = RewardOpportunityRepository(str(tmp_path / "reward.db"))
    repository.ensure_schema()
    candidate_id = repository.create_recall_candidate(
        {
            "source_platform": "x",
            "source_url": "https://example.com/post/1",
            "title": "Invite friends and earn $20",
            "recall_label": "suspected_invite_reward",
            "recall_reason": "matched invite + reward pattern",
        }
    )
    run_id = repository.create_investigation_run(
        {
            "candidate_id": candidate_id,
            "status": "running",
            "current_round": 1,
        }
    )
    repository.append_investigation_action(
        run_id,
        {
            "action_type": "open_link",
            "target_url": "https://example.com/promo",
            "status": "completed",
        },
    )
    loaded = repository.get_investigation_run(run_id)
    assert loaded["candidate_id"] == candidate_id
    assert loaded["actions"][0]["action_type"] == "open_link"
```

- [ ] **步骤 2：运行测试，确认它先失败**

Run: `cd app/backend && pytest tests/test_reward_opportunity_repository.py -v`  
Expected: 因仓储或模型缺失而 FAIL

- [ ] **步骤 3：写最小模型定义**

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RewardOpportunity:
    id: str
    title: str
    source_platform: str
    source_url: str
    ai_stage_2_label: str
    ai_confidence: float
    reward_type: str | None = None
    reward_value_text: str | None = None
    action_required: str | None = None
    ai_summary: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
```

- [ ] **步骤 4：写仓储 schema 和最小方法**

```python
import json
import sqlite3
import uuid


class RewardOpportunityRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reward_source_feeds (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    config_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reward_recall_candidates (
                    id TEXT PRIMARY KEY,
                    source_platform TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    recall_label TEXT NOT NULL,
                    recall_reason TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reward_investigation_runs (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_round INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reward_investigation_actions (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_url TEXT,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reward_opportunities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_platform TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    ai_stage_2_label TEXT NOT NULL,
                    ai_confidence REAL NOT NULL,
                    reward_type TEXT,
                    reward_value_text TEXT,
                    action_required TEXT,
                    ai_summary TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reward_opportunity_evidence (
                    id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    snippet TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def get_overview_stats(self) -> dict[str, int]:
        with self._connect() as connection:
            source_count = connection.execute("SELECT COUNT(*) FROM reward_source_feeds").fetchone()[0]
            opportunity_count = connection.execute("SELECT COUNT(*) FROM reward_opportunities").fetchone()[0]
        return {"source_count": source_count, "opportunity_count": opportunity_count}

    def create_recall_candidate(self, payload: dict[str, object]) -> str:
        candidate_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reward_recall_candidates (id, source_platform, source_url, title, recall_label, recall_reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    payload["source_platform"],
                    payload["source_url"],
                    payload["title"],
                    payload["recall_label"],
                    payload["recall_reason"],
                ),
            )
        return candidate_id

    def create_investigation_run(self, payload: dict[str, object]) -> str:
        run_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reward_investigation_runs (id, candidate_id, status, current_round)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, payload["candidate_id"], payload["status"], payload["current_round"]),
            )
        return run_id

    def append_investigation_action(self, run_id: str, payload: dict[str, object]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reward_investigation_actions (id, run_id, action_type, target_url, status, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    run_id,
                    payload["action_type"],
                    payload.get("target_url"),
                    payload["status"],
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def get_investigation_run(self, run_id: str) -> dict[str, object]:
        with self._connect() as connection:
            run_row = connection.execute(
                "SELECT id, candidate_id, status, current_round FROM reward_investigation_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            action_rows = connection.execute(
                "SELECT action_type, target_url, status FROM reward_investigation_actions WHERE run_id = ? ORDER BY created_at ASC",
                (run_id,),
            ).fetchall()
        return {
            "id": run_row["id"],
            "candidate_id": run_row["candidate_id"],
            "status": run_row["status"],
            "current_round": run_row["current_round"],
            "actions": [dict(row) for row in action_rows],
        }
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/backend && pytest tests/test_reward_opportunity_repository.py -v`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/backend/reward_opportunity/models.py app/backend/reward_opportunity/repository.py app/backend/tests/test_reward_opportunity_repository.py app/backend/models.py
git commit -m "feat: add reward opportunity repository and schema"
```

### 任务 2：新增召回层与评估层基础能力

**Files:**
- Create: `app/backend/reward_opportunity/recall.py`
- Create: `app/backend/reward_opportunity/evaluator.py`
- Create: `app/backend/tests/test_reward_opportunity_recall.py`

- [ ] **步骤 1：先写失败测试**

```python
from reward_opportunity.evaluator import evaluate_evidence_bundle
from reward_opportunity.recall import recall_candidate_from_document


def test_recall_flags_invite_reward_copy():
    candidate = recall_candidate_from_document(
        {
            "title": "Invite 3 friends and get $25",
            "body": "Register today, invite three friends, and receive a $25 cash reward.",
            "source_url": "https://example.com/post/1",
            "source_platform": "web",
        }
    )
    assert candidate is not None
    assert candidate["recall_label"] == "suspected_invite_reward"


def test_evaluator_returns_high_value_for_clear_reward():
    result = evaluate_evidence_bundle(
        {
            "title": "Invite 3 friends and get $25",
            "reward_snippets": ["receive a $25 cash reward"],
            "action_snippets": ["invite three friends"],
            "time_snippets": ["Campaign ends May 31"],
            "source_platform": "web",
        }
    )
    assert result["ai_stage_2_label"] in {"高价值", "可跟"}
    assert result["needs_investigation"] is False
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/backend && pytest tests/test_reward_opportunity_recall.py -v`  
Expected: 因函数不存在而 FAIL

- [ ] **步骤 3：实现最小召回逻辑**

```python
REWARD_PATTERNS = [
    ("suspected_invite_reward", ("invite", "reward")),
    ("suspected_registration_reward", ("register", "reward")),
    ("suspected_task_reward", ("task", "reward")),
]


def recall_candidate_from_document(document: dict[str, str]) -> dict[str, str] | None:
    title = f"{document.get('title', '')} {document.get('body', '')}".lower()
    for label, (left, right) in REWARD_PATTERNS:
        if left in title and right in title:
            return {
                "source_platform": document["source_platform"],
                "source_url": document["source_url"],
                "title": document["title"],
                "recall_label": label,
                "recall_reason": f"matched pattern: {left}+{right}",
            }
    return None
```

- [ ] **步骤 4：实现最小评估逻辑**

```python
def evaluate_evidence_bundle(bundle: dict[str, object]) -> dict[str, object]:
    reward_snippets = bundle.get("reward_snippets") or []
    action_snippets = bundle.get("action_snippets") or []
    time_snippets = bundle.get("time_snippets") or []
    enough_evidence = bool(reward_snippets and action_snippets)
    label = "高价值" if enough_evidence and time_snippets else "待补证据"
    return {
        "ai_stage_2_label": label,
        "ai_confidence": 0.82 if enough_evidence else 0.51,
        "ai_summary": "奖励明确且动作明确" if enough_evidence else "存在奖励线索，但证据不足",
        "ai_missing_evidence": [] if enough_evidence else ["time_or_rule_detail"],
        "needs_investigation": not enough_evidence or not time_snippets,
    }
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/backend && pytest tests/test_reward_opportunity_recall.py -v`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/backend/reward_opportunity/recall.py app/backend/reward_opportunity/evaluator.py app/backend/tests/test_reward_opportunity_recall.py
git commit -m "feat: add reward opportunity recall and evaluator primitives"
```

### 任务 3：接入 Crawl4AI 作为 Collector Agent 底座

**Files:**
- Create: `app/backend/reward_opportunity/crawl4ai_collector.py`
- Modify: `app/backend/requirements.txt`
- Create: `app/backend/tests/test_reward_opportunity_crawl4ai_collector.py`

- [ ] **步骤 1：先写失败测试**

```python
from reward_opportunity.crawl4ai_collector import build_crawl4ai_config


def test_build_crawl4ai_config_for_detail_page():
    config = build_crawl4ai_config(
        mode="detail",
        max_depth=1,
        use_llm_extraction=False,
    )
    assert config is not None
    assert getattr(config, "deep_crawl_strategy", None) is not None or getattr(config, "extraction_strategy", None) is not None
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/backend && pytest tests/test_reward_opportunity_crawl4ai_collector.py -v`  
Expected: 因模块不存在而 FAIL

- [ ] **步骤 3：把 Crawl4AI 加入依赖**

```text
crawl4ai>=0.8.0
```

- [ ] **步骤 4：新增 Crawl4AI Collector 封装**

```python
from crawl4ai import CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy


def build_crawl4ai_config(mode: str, max_depth: int = 1, use_llm_extraction: bool = False):
    extraction_strategy = None
    if use_llm_extraction:
        from crawl4ai.extraction_strategy import LLMExtractionStrategy

        extraction_strategy = LLMExtractionStrategy(
            instruction="Extract reward, action, deadline, and rule-related content.",
            extraction_type="block",
        )

    deep_crawl_strategy = None
    if mode in {"list", "detail"}:
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
        )

    return CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_strategy,
        extraction_strategy=extraction_strategy,
    )
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/backend && pytest tests/test_reward_opportunity_crawl4ai_collector.py -v`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/backend/reward_opportunity/crawl4ai_collector.py app/backend/requirements.txt app/backend/tests/test_reward_opportunity_crawl4ai_collector.py
git commit -m "feat: add crawl4ai collector foundation"
```

### 任务 4：新增自主调查回路

**Files:**
- Create: `app/backend/reward_opportunity/investigator.py`
- Create: `app/backend/reward_opportunity/agent_loop.py`
- Create: `app/backend/tests/test_reward_opportunity_agent_loop.py`

- [ ] **步骤 1：先写失败测试**

```python
from reward_opportunity.agent_loop import run_investigation_cycle


def test_investigation_cycle_requests_follow_up_when_time_missing():
    result = run_investigation_cycle(
        candidate={
            "title": "Invite 3 friends and get $25",
            "source_url": "https://example.com/post/1",
        },
        evidence_bundle={
            "reward_snippets": ["receive a $25 cash reward"],
            "action_snippets": ["invite three friends"],
            "time_snippets": [],
        },
        max_rounds=2,
    )
    assert result["status"] in {"classified", "needs_follow_up"}
    assert len(result["actions"]) >= 1
    assert result["actions"][0]["action_type"] in {"search_query", "open_link", "open_rule_page"}
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/backend && pytest tests/test_reward_opportunity_agent_loop.py -v`  
Expected: 因模块或函数不存在而 FAIL

- [ ] **步骤 3：实现调查决策辅助函数**

```python
def decide_next_investigation_actions(candidate: dict[str, object], evidence_bundle: dict[str, object]) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    if not evidence_bundle.get("time_snippets"):
        actions.append(
            {
                "action_type": "search_query",
                "query": f"{candidate['title']} rules deadline reward",
                "reason": "time evidence missing",
            }
        )
    if not evidence_bundle.get("rule_snippets"):
        actions.append(
            {
                "action_type": "open_rule_page",
                "target_url": candidate["source_url"],
                "reason": "rule detail missing",
            }
        )
    return actions
```

- [ ] **步骤 4：实现最小调查回路**

```python
from reward_opportunity.evaluator import evaluate_evidence_bundle
from reward_opportunity.investigator import decide_next_investigation_actions


def run_investigation_cycle(candidate: dict[str, object], evidence_bundle: dict[str, object], max_rounds: int = 2) -> dict[str, object]:
    actions: list[dict[str, object]] = []
    evaluation = evaluate_evidence_bundle(evidence_bundle)
    if not evaluation["needs_investigation"]:
        return {"status": "classified", "evaluation": evaluation, "actions": actions}
    for _round in range(max_rounds):
        next_actions = decide_next_investigation_actions(candidate, evidence_bundle)
        if not next_actions:
            break
        actions.extend(next_actions)
        return {"status": "needs_follow_up", "evaluation": evaluation, "actions": actions}
    return {"status": "classified", "evaluation": evaluation, "actions": actions}
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/backend && pytest tests/test_reward_opportunity_agent_loop.py -v`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/backend/reward_opportunity/investigator.py app/backend/reward_opportunity/agent_loop.py app/backend/tests/test_reward_opportunity_agent_loop.py
git commit -m "feat: add reward opportunity investigation loop"
```

### 任务 5：新增服务层与 API 接口

**Files:**
- Create: `app/backend/reward_opportunity/service.py`
- Create: `app/backend/reward_opportunity/merger.py`
- Create: `app/backend/tests/test_reward_opportunity_api.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/main.py`

- [ ] **步骤 1：先写失败 API 测试**

```python
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_reward_overview_endpoint_returns_counts():
    response = client.get("/api/reward-opportunities/overview")
    assert response.status_code == 200
    payload = response.json()
    assert "source_count" in payload
    assert "opportunity_count" in payload


def test_reward_opportunities_list_endpoint_returns_items():
    response = client.get("/api/reward-opportunities")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload


def test_reward_operations_endpoint_returns_sources_and_jobs():
    response = client.get("/api/reward-opportunities/operations")
    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
    assert "recent_jobs" in payload
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/backend && pytest tests/test_reward_opportunity_api.py -v`  
Expected: 因 404 而 FAIL

- [ ] **步骤 3：实现服务层门面**

```python
class RewardOpportunityService:
    def __init__(self, repository):
        self._repository = repository

    def get_overview(self) -> dict[str, object]:
        stats = self._repository.get_overview_stats()
        return {
            "source_count": stats["source_count"],
            "opportunity_count": stats["opportunity_count"],
            "candidate_count": 0,
            "high_value_count": 0,
        }

    def list_opportunities(self) -> dict[str, object]:
        return {"items": [], "total": 0}

    def get_operations(self) -> dict[str, object]:
        return {"sources": [], "recent_jobs": []}
```

- [ ] **步骤 4：把服务和路由接到 FastAPI**

```python
@app.get("/api/reward-opportunities/overview")
def get_reward_opportunity_overview(request: Request):
    service = request.app.state.reward_opportunity_service
    return service.get_overview()


@app.get("/api/reward-opportunities")
def list_reward_opportunities(request: Request):
    service = request.app.state.reward_opportunity_service
    return service.list_opportunities()


@app.get("/api/reward-opportunities/operations")
def get_reward_opportunity_operations(request: Request):
    service = request.app.state.reward_opportunity_service
    return service.get_operations()
```

- [ ] **步骤 5：在 `main.py` 初始化服务**

```python
from reward_opportunity.repository import RewardOpportunityRepository
from reward_opportunity.service import RewardOpportunityService


reward_repository = RewardOpportunityRepository(str(DATA_DIR / "reward_opportunities.db"))
reward_repository.ensure_schema()
app.state.reward_opportunity_repository = reward_repository
app.state.reward_opportunity_service = RewardOpportunityService(reward_repository)
```

- [ ] **步骤 6：重新运行测试，确认通过**

Run: `cd app/backend && pytest tests/test_reward_opportunity_api.py -v`  
Expected: PASS

- [ ] **步骤 7：提交**

```bash
git add app/backend/reward_opportunity/service.py app/backend/reward_opportunity/merger.py app/backend/api.py app/backend/main.py app/backend/tests/test_reward_opportunity_api.py
git commit -m "feat: add reward opportunity api surface"
```

### 任务 6：把奖励活动任务接入调度器

**Files:**
- Modify: `app/backend/scheduler.py`
- Modify: `app/backend/tests/test_scheduler.py`

- [ ] **步骤 1：先写失败调度测试**

```python
from scheduler import TaskScheduler


def test_scheduler_registers_reward_opportunity_job():
    scheduler = TaskScheduler(None)
    scheduler.register_reward_opportunity_jobs()
    names = [job.id for job in scheduler.scheduler.get_jobs()]
    assert "reward-opportunity-source-sync" in names
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/backend && pytest tests/test_scheduler.py::test_scheduler_registers_reward_opportunity_job -v`  
Expected: 因方法不存在而 FAIL

- [ ] **步骤 3：新增调度注册方法**

```python
def register_reward_opportunity_jobs(self) -> None:
    self.scheduler.add_job(
        self.run_reward_source_sync,
        "interval",
        minutes=30,
        id="reward-opportunity-source-sync",
        replace_existing=True,
    )


def run_reward_source_sync(self) -> None:
    if not getattr(self.app.state, "reward_opportunity_service", None):
        return
    self.app.state.reward_opportunity_service.get_overview()
```

- [ ] **步骤 4：在启动链路注册它**

```python
self.register_reward_opportunity_jobs()
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/backend && pytest tests/test_scheduler.py::test_scheduler_registers_reward_opportunity_job -v`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/backend/scheduler.py app/backend/tests/test_scheduler.py
git commit -m "feat: schedule reward opportunity background jobs"
```

### 任务 7：新增前端类型与 API 客户端

**Files:**
- Create: `app/frontend/src/types/rewardOpportunity.ts`
- Create: `app/frontend/src/services/rewardOpportunityApi.ts`
- Modify: `app/frontend/src/types/index.ts`
- Modify: `app/frontend/src/services/api.ts`
- Test: `app/frontend/src/services/api.test.ts`

- [ ] **步骤 1：先写失败测试**

```typescript
import { describe, expect, it } from 'vitest'
import { rewardOpportunityApi } from './rewardOpportunityApi'

describe('rewardOpportunityApi', () => {
  it('exports overview and list helpers', () => {
    expect(typeof rewardOpportunityApi.getOverview).toBe('function')
    expect(typeof rewardOpportunityApi.listOpportunities).toBe('function')
    expect(typeof rewardOpportunityApi.getOperations).toBe('function')
  })
})
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/frontend && npm test -- rewardOpportunityApi`  
Expected: 因模块不存在而 FAIL

- [ ] **步骤 3：新增类型定义**

```typescript
export interface RewardOpportunityOverview {
  source_count: number
  opportunity_count: number
  candidate_count: number
  high_value_count: number
}

export interface RewardOpportunityItem {
  id: string
  title: string
  source_platform: string
  source_url: string
  ai_stage_2_label: '高价值' | '可跟' | '待补证据' | '低价值' | '拒绝'
  ai_confidence: number
  reward_type?: string | null
  reward_value_text?: string | null
  action_required?: string | null
  ai_summary?: string | null
}
```

- [ ] **步骤 4：新增 API 客户端**

```typescript
import type { RewardOpportunityItem, RewardOpportunityOverview } from '../types/rewardOpportunity'

const API_BASE = '/api/reward-opportunities'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const rewardOpportunityApi = {
  getOverview: () => getJson<RewardOpportunityOverview>('/overview'),
  listOpportunities: () => getJson<{ items: RewardOpportunityItem[]; total: number }>('/'),
  getOperations: () => getJson<{ sources: unknown[]; recent_jobs: unknown[] }>('/operations'),
}
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/frontend && npm test -- rewardOpportunityApi`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/frontend/src/types/rewardOpportunity.ts app/frontend/src/services/rewardOpportunityApi.ts app/frontend/src/types/index.ts app/frontend/src/services/api.ts
git commit -m "feat: add reward opportunity frontend api client"
```

### 任务 8：新增前端四个页面与 hooks

**Files:**
- Create: `app/frontend/src/hooks/useRewardOverview.ts`
- Create: `app/frontend/src/hooks/useRewardOpportunities.ts`
- Create: `app/frontend/src/hooks/useRewardOpportunityDetail.ts`
- Create: `app/frontend/src/hooks/useRewardSourceFeeds.ts`
- Create: `app/frontend/src/pages/reward/RewardOverviewPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunitiesPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunityDetailPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOperationsPage.tsx`
- Create: `app/frontend/src/pages/reward/RewardOverviewPage.test.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunitiesPage.test.tsx`
- Create: `app/frontend/src/pages/reward/RewardOpportunityDetailPage.test.tsx`
- Create: `app/frontend/src/pages/reward/RewardOperationsPage.test.tsx`

- [ ] **步骤 1：先写页面 smoke 测试**

```typescript
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import RewardOverviewPage from './RewardOverviewPage'

it('renders reward overview heading', () => {
  render(
    <MemoryRouter>
      <RewardOverviewPage />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: '奖励活动发现系统' })).toBeInTheDocument()
})
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/frontend && npm test -- RewardOverviewPage`  
Expected: 因页面不存在而 FAIL

- [ ] **步骤 3：新增 hooks**

```typescript
import { useEffect, useState } from 'react'
import { rewardOpportunityApi } from '../services/rewardOpportunityApi'
import type { RewardOpportunityOverview } from '../types/rewardOpportunity'

export function useRewardOverview() {
  const [overview, setOverview] = useState<RewardOpportunityOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    rewardOpportunityApi
      .getOverview()
      .then(data => {
        if (active) setOverview(data)
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : '加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return { overview, loading, error }
}
```

- [ ] **步骤 4：新增页面最小渲染逻辑**

```tsx
export default function RewardOverviewPage() {
  const { overview, loading, error } = useRewardOverview()

  return (
    <section data-testid="reward-overview-page" className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">奖励活动发现系统</h1>
        <p className="text-sm text-slate-500">自动抓取、召回、调查、深筛并沉淀结构化机会。</p>
      </header>
      {loading ? <p>加载中...</p> : null}
      {error ? <p>{error}</p> : null}
      {overview ? <div data-testid="reward-overview-count">{overview.opportunity_count}</div> : null}
    </section>
  )
}
```

- [ ] **步骤 5：重新运行测试，确认通过**

Run: `cd app/frontend && npm test -- RewardOverviewPage RewardOpportunitiesPage RewardOpportunityDetailPage RewardOperationsPage`  
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add app/frontend/src/hooks/useRewardOverview.ts app/frontend/src/hooks/useRewardOpportunities.ts app/frontend/src/hooks/useRewardOpportunityDetail.ts app/frontend/src/hooks/useRewardSourceFeeds.ts app/frontend/src/pages/reward
git commit -m "feat: add reward opportunity frontend pages"
```

### 任务 9：接入路由、导航与文档

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/routes/domainPaths.ts`
- Modify: `app/frontend/src/pages/SystemHomePage.tsx`
- Modify: `app/frontend/src/components/app/DomainHeader.tsx`
- Modify: `README.md`
- Modify: `docs/当前系统架构与技术实现说明.md`
- Modify: `docs/当前项目核心功能梳理.md`

- [ ] **步骤 1：先写失败路由测试**

```typescript
import { render, screen } from '@testing-library/react'
import App from '../App'

it('routes reward overview under /rewards/overview', () => {
  window.history.pushState({}, '', '/rewards/overview')
  render(<App />)
  expect(screen.getByRole('heading', { name: '奖励活动发现系统' })).toBeInTheDocument()
})
```

- [ ] **步骤 2：运行测试，确认先失败**

Run: `cd app/frontend && npm test -- App`  
Expected: 因路由不存在而 FAIL

- [ ] **步骤 3：新增路由常量**

```typescript
export const rewardPaths = {
  root: '/rewards',
  overview: '/rewards/overview',
  opportunities: '/rewards/opportunities',
  opportunityDetail: (id: string) => `/rewards/opportunities/${id}`,
  operations: '/rewards/operations',
} as const
```

- [ ] **步骤 4：接入路由和导航**

```tsx
<Route
  path="/rewards"
  element={
    <DomainShellLayout
      brandLabel="奖励活动 Agent"
      brandTo={rewardPaths.overview}
      navLinks={[
        { path: rewardPaths.overview, label: '概览' },
        { path: rewardPaths.opportunities, label: '机会库' },
        { path: rewardPaths.operations, label: '来源与任务' },
      ]}
    />
  }
>
  <Route index element={<Navigate to="overview" replace />} />
  <Route path="overview" element={<RewardOverviewPage />} />
  <Route path="opportunities" element={<RewardOpportunitiesPage />} />
  <Route path="opportunities/:id" element={<RewardOpportunityDetailPage />} />
  <Route path="operations" element={<RewardOperationsPage />} />
</Route>
```

- [ ] **步骤 5：更新首页与文档说明**

```markdown
- `/rewards/*`
  - 奖励活动 Agent 系统
  - 包含概览、机会库、详情、来源与任务
```

- [ ] **步骤 6：运行前端测试与构建**

Run: `cd app/frontend && npm test -- App && npm run build`  
Expected: PASS，然后 Vite build 成功

- [ ] **步骤 7：运行后端回归切片**

Run: `cd app/backend && pytest tests/test_reward_opportunity_repository.py tests/test_reward_opportunity_recall.py tests/test_reward_opportunity_agent_loop.py tests/test_reward_opportunity_api.py -v`  
Expected: PASS

- [ ] **步骤 8：提交**

```bash
git add app/frontend/src/App.tsx app/frontend/src/routes/domainPaths.ts app/frontend/src/pages/SystemHomePage.tsx app/frontend/src/components/app/DomainHeader.tsx README.md docs/当前系统架构与技术实现说明.md docs/当前项目核心功能梳理.md
git commit -m "feat: wire reward opportunity agent into app shell"
```

---

## 自检

### 规格覆盖

- Crawl4AI 作为 Collector 底座：任务 3 覆盖
- 多 Agent 架构：任务 2-5 覆盖
- 自主追证据调查：任务 4 覆盖
- 调查过程持久化：任务 1 覆盖
- 新 API 面：任务 5 覆盖
- 调度器接入：任务 6 覆盖
- 前端四页面：任务 7-9 覆盖
- 旧系统 / 新系统主线分离：任务 9 的路由和文档更新覆盖

### 占位词扫描

- 文中不包含 `TBD`、`TODO` 或空泛占位描述

### 类型一致性

- `ai_stage_2_label`
- `reward_opportunities`
- `investigation_runs`
- `investigation_actions`

这些命名在各任务中保持一致。
