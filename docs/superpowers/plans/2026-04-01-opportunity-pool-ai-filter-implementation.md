# Opportunity Pool AI Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 VigilAI 机会池补齐固定针对性筛选，并新增基于自然语言的 AI 精筛能力，让用户可以先用稳定条件缩小范围，再只保留符合 AI 条件的机会。

**Architecture:** 继续复用现有 `ActivitiesPage -> useActivities -> api.getActivities -> DataManager.get_activities()` 主链路，先扩展固定筛选合同，再新增一个独立的 `/api/activities/ai-filter` 接口完成 AI 精筛。后端 AI 精筛保持为一个小而独立的服务层，输入是当前候选机会集和用户中文条件，输出是严格结构化的保留结果；前端只在 AI 精筛成功时切换为“仅展示保留结果”的结果模式。

**Tech Stack:** FastAPI, SQLite, Pydantic, React, TypeScript, Vitest, pytest, 现有 VigilAI 数据管理与活动列表架构。

---

## Scope Check

这份规格属于同一个垂直功能，不需要拆成多个实现计划。实现时按“后端固定筛选 -> 后端 AI 精筛 -> 前端合同与状态 -> 前端界面 -> 回归验证”的顺序推进，保证每一段都能独立验证。

## File Structure

### Backend

- Modify: `app/backend/api.py`
  Responsibility: 扩展 `/api/activities` 查询参数，并新增 `POST /api/activities/ai-filter` 接口。
- Modify: `app/backend/data_manager.py`
  Responsibility: 补齐固定筛选逻辑，包括奖金区间、独立开发者友好、奖励明确性、投入成本、线上/远程。
- Modify: `app/backend/config.py`
  Responsibility: 增加 AI 精筛相关开关、模型名、超时和候选数上限配置。
- Modify: `app/backend/.env.example`
  Responsibility: 记录 AI 精筛所需环境变量，避免实现后无法配置。
- Modify: `app/backend/requirements.txt`
  Responsibility: 如果当前仓库没有可复用的 LLM SDK，则补充 AI 精筛所需 SDK 依赖。
- Create: `app/backend/analysis/opportunity_ai_filter.py`
  Responsibility: 负责候选机会打包、调用 LLM、解析结构化响应、返回仅保留结果。
- Create: `app/backend/tests/test_opportunity_ai_filter.py`
  Responsibility: 覆盖 AI 精筛服务、候选数上限、模型失败兜底和接口成功场景。
- Modify: `app/backend/tests/test_v2_foundation.py`
  Responsibility: 为固定筛选新增端到端测试，确保列表接口合同被真实打通。

### Frontend

- Modify: `app/frontend/src/types/index.ts`
  Responsibility: 扩展固定筛选字段，并增加 AI 精筛请求/响应类型。
- Modify: `app/frontend/src/services/api.ts`
  Responsibility: 增加新的列表查询字段和 `aiFilterActivities()` 客户端方法。
- Modify: `app/frontend/src/services/api.test.ts`
  Responsibility: 验证新增 query string 字段与 AI 精筛 POST 请求格式。
- Modify: `app/frontend/src/hooks/useActivities.ts`
  Responsibility: 让扩展后的筛选字段进入现有活动列表获取链路。
- Modify: `app/frontend/src/utils/constants.ts`
  Responsibility: 补齐固定筛选选项的中文枚举。
- Modify: `app/frontend/src/components/FilterBar.tsx`
  Responsibility: 将当前筛选栏升级为面向机会判断的固定针对性筛选器。
- Create: `app/frontend/src/components/OpportunityAiFilterPanel.tsx`
  Responsibility: 承载 AI 精筛输入框、触发按钮、摘要、错误和清除操作。
- Create: `app/frontend/src/components/OpportunityAiFilterPanel.test.tsx`
  Responsibility: 覆盖 AI 精筛面板的输入、禁用、清除和摘要展示。
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
  Responsibility: 串联固定筛选、AI 精筛状态、结果切换、中文提示和空状态。
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`
  Responsibility: 覆盖机会池从固定筛选到 AI 精筛的主要交互流。
- Modify: `app/frontend/src/types/index.test.ts`
  Responsibility: 验证新增类型合同与 AI 精筛响应结构。

### Docs

- Modify: `docs/superpowers/specs/2026-04-01-opportunity-pool-ai-filter-design.md`
  Responsibility: 仅当实现过程中发现必须偏离已批准规格时再同步更新。

---

### Task 1: 打通后端固定针对性筛选

**Files:**
- Modify: `app/backend/tests/test_v2_foundation.py`
- Modify: `app/backend/api.py`
- Modify: `app/backend/data_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_activity_list_supports_extended_fixed_filters(data_manager):
    solo = create_activity(
        data_manager,
        url="https://example.com/solo-remote",
        title="Solo Remote Hackathon",
        description="Individual developers can submit a small fix with guaranteed reward payout.",
    )
    team = create_activity(
        data_manager,
        url="https://example.com/team-offline",
        title="Team Offline Contest",
        description="Team required and long-form application review cycle.",
    )
    data_manager.add_activity(solo)
    data_manager.add_activity(team)

    matched, total = data_manager.get_activities(
        filters={
            "solo_friendliness": "solo_friendly",
            "reward_clarity": "high",
            "effort_level": "low",
            "remote_mode": "remote",
        }
    )

    assert total == 1
    assert matched[0].id == solo.id


def test_activity_list_endpoint_accepts_extended_fixed_filters(client, data_manager):
    activity = create_activity(
        data_manager,
        url="https://example.com/high-prize",
        description="Individual developers can join remotely for a guaranteed reward payout.",
    )
    data_manager.add_activity(activity)

    response = client.get(
        "/api/activities",
        params={
            "prize_range": "500-2000",
            "solo_friendliness": "solo_friendly",
            "reward_clarity": "high",
            "effort_level": "low",
            "remote_mode": "remote",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_v2_foundation.py -k "extended_fixed_filters or accepts_extended_fixed_filters" -q`
Expected: FAIL because the API and `DataManager.get_activities()` do not yet understand the new filter fields.

- [ ] **Step 3: Write minimal implementation**

```python
@app.get("/api/activities")
async def list_activities(
    request: Request,
    prize_range: Optional[str] = Query(None),
    solo_friendliness: Optional[str] = Query(None),
    reward_clarity: Optional[str] = Query(None),
    effort_level: Optional[str] = Query(None),
    remote_mode: Optional[str] = Query(None),
):
    if prize_range:
        filters["prize_range"] = prize_range
```

Implement:
- query 参数接入 `prize_range`、`solo_friendliness`、`reward_clarity`、`effort_level`、`remote_mode`
- 在 `DataManager` 中新增小范围私有 helper，例如：
  - `_matches_prize_range(activity, prize_range)`
  - `_normalize_remote_mode(location)`
  - `_matches_analysis_field(activity, key, expected)`
- 保持 SQL 初筛不变，对 `analysis_fields` 与远程模式采用 Python 侧二次过滤
- 明确支持 `prize_range` 值：
  - `unknown`
  - `0-500`
  - `500-2000`
  - `2000-10000`
  - `10000+`

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_v2_foundation.py -k "extended_fixed_filters or accepts_extended_fixed_filters" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/api.py app/backend/data_manager.py app/backend/tests/test_v2_foundation.py
git commit -m "feat: add extended fixed filters for opportunities"
```

### Task 2: 新增后端 AI 精筛服务与接口

**Files:**
- Modify: `app/backend/config.py`
- Modify: `app/backend/.env.example`
- Modify: `app/backend/requirements.txt`
- Modify: `app/backend/api.py`
- Create: `app/backend/analysis/opportunity_ai_filter.py`
- Create: `app/backend/tests/test_opportunity_ai_filter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ai_filter_returns_only_matched_items(data_manager, client, monkeypatch):
    activity = create_activity(
        data_manager,
        url="https://example.com/ai-filter-target",
        description="Individual developers can submit remotely for a guaranteed cash prize.",
    )
    data_manager.add_activity(activity)

    monkeypatch.setattr(
        "analysis.opportunity_ai_filter.filter_candidates_with_ai",
        lambda **_: {
            "query": "只保留适合独立开发者的机会",
            "parsed_intent_summary": "筛选适合单人开发的机会",
            "candidate_count": 1,
            "matched_count": 1,
            "discarded_count": 0,
            "items": [
                {
                    "id": activity.id,
                    "ai_match_reason": "适合单人开发，且支持远程参与",
                    "ai_match_confidence": "high",
                }
            ],
        },
    )

    response = client.post(
        "/api/activities/ai-filter",
        json={
            "base_filters": {"category": "hackathon"},
            "query": "只保留适合独立开发者的机会",
        },
    )

    assert response.status_code == 200
    assert response.json()["matched_count"] == 1


def test_ai_filter_rejects_large_candidate_sets(data_manager):
    with pytest.raises(ValueError, match="candidate limit"):
        filter_candidates_with_ai(
            candidates=[{"id": str(index)} for index in range(201)],
            query="筛选",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/backend; python -m pytest tests/test_opportunity_ai_filter.py -q`
Expected: FAIL because the AI filter module and endpoint do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def filter_candidates_with_ai(*, candidates: list[dict], query: str) -> dict:
    if len(candidates) > AI_FILTER_MAX_CANDIDATES:
        raise ValueError("candidate limit exceeded")

    # 第一步先通过 provider 函数返回严格 JSON；测试中用 monkeypatch 替身
    result = _call_ai_provider(candidates=candidates, query=query)
    return _normalize_ai_filter_result(result)
```

Implement:
- 在 `config.py` 增加：
  - `AI_FILTER_ENABLED`
  - `AI_FILTER_MODEL`
  - `AI_FILTER_MAX_CANDIDATES`
  - `AI_FILTER_TIMEOUT_SECONDS`
  - `OPENAI_API_KEY` 或当前确定的 provider key 入口
- 在 `.env.example` 中补充中文配置说明
- 在 `requirements.txt` 中补充 AI 精筛所需 SDK（如仓库暂无可用 provider）
- 在 `opportunity_ai_filter.py` 中封装：
  - 候选数校验
  - 候选机会压缩为模型输入
  - provider 调用
  - JSON 解析与严格归一化
  - 失败时抛出可识别异常
- 在 `api.py` 中新增 `POST /api/activities/ai-filter`
- 接口行为：
  - 先根据 `base_filters` 调用 `get_activities()`
  - 再调用 AI 精筛服务
  - 仅返回保留结果
  - 候选过多、AI 不可用、JSON 解析失败时返回中文错误

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/backend; python -m pytest tests/test_opportunity_ai_filter.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/config.py app/backend/.env.example app/backend/requirements.txt app/backend/api.py app/backend/analysis/opportunity_ai_filter.py app/backend/tests/test_opportunity_ai_filter.py
git commit -m "feat: add opportunity ai filter backend flow"
```

### Task 3: 扩展前端类型、API 合同与活动筛选状态

**Files:**
- Modify: `app/frontend/src/types/index.ts`
- Modify: `app/frontend/src/types/index.test.ts`
- Modify: `app/frontend/src/services/api.ts`
- Modify: `app/frontend/src/services/api.test.ts`
- Modify: `app/frontend/src/hooks/useActivities.ts`
- Modify: `app/frontend/src/utils/constants.ts`

- [ ] **Step 1: Write the failing tests**

```ts
it('serializes extended activity filters into the activities query string', async () => {
  globalThis.fetch = vi.fn().mockResolvedValue(
    jsonResponse({ total: 0, page: 1, page_size: 20, items: [] })
  ) as typeof fetch

  await api.getActivities({
    prize_range: '500-2000',
    solo_friendliness: 'solo_friendly',
    reward_clarity: 'high',
    effort_level: 'low',
    remote_mode: 'remote',
  })

  const requestUrl = new URL((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0])
  expect(requestUrl.searchParams.get('prize_range')).toBe('500-2000')
  expect(requestUrl.searchParams.get('remote_mode')).toBe('remote')
})


it('accepts AI filter response contracts', () => {
  const response: OpportunityAiFilterResponse = {
    query: '只保留适合独立开发者的机会',
    parsed_intent_summary: '筛选适合单人开发的机会',
    candidate_count: 10,
    matched_count: 3,
    discarded_count: 7,
    items: [],
  }

  expect(response.matched_count).toBe(3)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm run test -- src/services/api.test.ts src/types/index.test.ts`
Expected: FAIL because the new filter fields and AI filter response types are not defined.

- [ ] **Step 3: Write minimal implementation**

```ts
export interface ActivityFilters {
  prize_range?: string
  solo_friendliness?: string
  reward_clarity?: string
  effort_level?: string
  remote_mode?: string
}

export interface OpportunityAiFilterResponse {
  query: string
  parsed_intent_summary: string
  candidate_count: number
  matched_count: number
  discarded_count: number
  items: Array<ActivityListItem & {
    ai_match_reason: string
    ai_match_confidence: string
  }>
}
```

Implement:
- 在 `types/index.ts` 中增加固定筛选字段与 AI 精筛类型
- 在 `api.ts` 中新增：
  - 扩展后的 `getActivities()`
  - `aiFilterActivities(payload)`
- 在 `useActivities.ts` 中保留现有模式，只确保新增筛选字段能进入 `filters` 状态
- 在 `constants.ts` 中增加中文筛选选项：
  - 奖金区间
  - 独立开发者友好
  - 奖励明确性
  - 投入成本
  - 线上/远程

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm run test -- src/services/api.test.ts src/types/index.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/types/index.ts app/frontend/src/types/index.test.ts app/frontend/src/services/api.ts app/frontend/src/services/api.test.ts app/frontend/src/hooks/useActivities.ts app/frontend/src/utils/constants.ts
git commit -m "feat: add opportunity filter frontend contracts"
```

### Task 4: 重构固定筛选区为中文机会判断筛选器

**Files:**
- Modify: `app/frontend/src/components/FilterBar.tsx`
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

```ts
it('renders the new Chinese fixed filters and applies them', async () => {
  render(
    <MemoryRouter initialEntries={['/activities']}>
      <ActivitiesPage />
    </MemoryRouter>
  )

  expect(screen.getByText('奖金区间')).toBeInTheDocument()
  expect(screen.getByText('独立开发者友好')).toBeInTheDocument()
  expect(screen.getByText('线上/远程')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: '适合单人' }))

  await waitFor(() => {
    expect(setFilters).toHaveBeenCalledWith(expect.objectContaining({
      solo_friendliness: 'solo_friendly',
    }))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm run test -- src/pages/OpportunityPoolPage.test.tsx`
Expected: FAIL because the current `FilterBar` 还没有这些中文筛选项，也没有传递相应状态。

- [ ] **Step 3: Write minimal implementation**

```tsx
<FilterBar
  category={filters.category || ''}
  deadlineLevel={filters.deadline_level || ''}
  prizeRange={filters.prize_range || ''}
  soloFriendliness={filters.solo_friendliness || ''}
  rewardClarity={filters.reward_clarity || ''}
  effortLevel={filters.effort_level || ''}
  trustLevel={filters.trust_level || ''}
  remoteMode={filters.remote_mode || ''}
  onPrizeRangeChange={handlePrizeRangeChange}
  onSoloFriendlinessChange={handleSoloFriendlinessChange}
  onRemoteModeChange={handleRemoteModeChange}
/>
```

Implement:
- 扩展 `FilterBarProps`
- 保持全部前端文案为中文
- 将固定筛选区从“来源主导”切换为“机会判断主导”
- 在 `ActivitiesPage` 中增加对应 handler
- `handleClearFilters()` 同时清理新增固定筛选字段
- `hasActiveFilters` 计算同步纳入新增字段
- 固定筛选区默认可见，不再只能靠“高级调整”才看到

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm run test -- src/pages/OpportunityPoolPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/components/FilterBar.tsx app/frontend/src/pages/ActivitiesPage.tsx app/frontend/src/pages/OpportunityPoolPage.test.tsx
git commit -m "feat: redesign opportunity fixed filters in chinese"
```

### Task 5: 接入前端 AI 精筛面板与结果模式

**Files:**
- Create: `app/frontend/src/components/OpportunityAiFilterPanel.tsx`
- Create: `app/frontend/src/components/OpportunityAiFilterPanel.test.tsx`
- Modify: `app/frontend/src/pages/ActivitiesPage.tsx`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`

- [ ] **Step 1: Write the failing tests**

```ts
it('applies AI filtering and only renders matched opportunities', async () => {
  apiMocks.aiFilterActivities.mockResolvedValue({
    query: '只保留适合独立开发者的机会',
    parsed_intent_summary: '筛选适合单人开发的机会',
    candidate_count: 2,
    matched_count: 1,
    discarded_count: 1,
    items: [
      {
        ...mockActivityOne,
        ai_match_reason: '适合单人开发，奖励明确',
        ai_match_confidence: 'high',
      },
    ],
  })

  render(
    <MemoryRouter initialEntries={['/activities']}>
      <ActivitiesPage />
    </MemoryRouter>
  )

  fireEvent.change(
    screen.getByPlaceholderText('例如：只保留适合独立开发者、奖金明确、两周内截止的线上机会'),
    { target: { value: '只保留适合独立开发者的机会' } }
  )
  fireEvent.click(screen.getByRole('button', { name: '开始 AI 精筛' }))

  expect(await screen.findByText('当前为 AI 精筛结果，仅保留符合条件的机会')).toBeInTheDocument()
  expect(screen.getByText('适合单人开发，奖励明确')).toBeInTheDocument()
  expect(screen.queryByText('Grant Program')).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location app/frontend; npm run test -- src/components/OpportunityAiFilterPanel.test.tsx src/pages/OpportunityPoolPage.test.tsx`
Expected: FAIL because the AI filter panel, API call, and result-mode switching do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```tsx
const [aiQuery, setAiQuery] = useState('')
const [aiFilterLoading, setAiFilterLoading] = useState(false)
const [aiFilterSummary, setAiFilterSummary] = useState<OpportunityAiFilterResponse | null>(null)
const [aiFilteredItems, setAiFilteredItems] = useState<Activity[]>([])

const handleRunAiFilter = async () => {
  const result = await api.aiFilterActivities({ base_filters: filters, query: aiQuery })
  setAiFilterSummary(result)
  setAiFilteredItems(result.items)
}
```

Implement:
- 新增 `OpportunityAiFilterPanel`
- 在 `ActivitiesPage` 中管理：
  - `aiQuery`
  - `aiFilterLoading`
  - `aiFilterApplied`
  - `aiFilterError`
  - `aiFilterSummary`
  - `aiFilteredItems`
- AI 精筛成功后，列表改为渲染 `aiFilteredItems`
- 明确显示中文状态：
  - `当前为固定筛选结果`
  - `当前为 AI 精筛结果，仅保留符合条件的机会`
- AI 精筛失败时保留原固定筛选列表
- AI 精筛空结果时展示中文空状态与“清除 AI 条件”
- AI 精筛请求前若当前候选集大于 200，直接显示中文提示，不发请求

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location app/frontend; npm run test -- src/components/OpportunityAiFilterPanel.test.tsx src/pages/OpportunityPoolPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/components/OpportunityAiFilterPanel.tsx app/frontend/src/components/OpportunityAiFilterPanel.test.tsx app/frontend/src/pages/ActivitiesPage.tsx app/frontend/src/pages/OpportunityPoolPage.test.tsx
git commit -m "feat: add ai filtering panel for opportunity pool"
```

### Task 6: 跑回归验证并清理体验边角

**Files:**
- Modify: `app/backend/tests/test_v2_foundation.py`
- Modify: `app/backend/tests/test_opportunity_ai_filter.py`
- Modify: `app/frontend/src/pages/OpportunityPoolPage.test.tsx`
- Modify: `app/frontend/src/components/OpportunityAiFilterPanel.test.tsx`
- Modify: `app/frontend/src/services/api.test.ts`
- Modify: `app/frontend/src/types/index.test.ts`

- [ ] **Step 1: Add any missing regression tests discovered during implementation**

```ts
it('keeps the fixed-filter results visible when AI filtering fails', async () => {
  apiMocks.aiFilterActivities.mockRejectedValue(new Error('AI 精筛暂时不可用'))

  render(<ActivitiesPage />)

  fireEvent.click(screen.getByRole('button', { name: '开始 AI 精筛' }))

  expect(await screen.findByText('AI 精筛暂时不可用')).toBeInTheDocument()
  expect(screen.getByText('AI Hackathon')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run backend focused tests**

Run: `Set-Location app/backend; python -m pytest tests/test_v2_foundation.py tests/test_opportunity_ai_filter.py -q`
Expected: PASS

- [ ] **Step 3: Run frontend focused tests**

Run: `Set-Location app/frontend; npm run test -- src/services/api.test.ts src/types/index.test.ts src/components/OpportunityAiFilterPanel.test.tsx src/pages/OpportunityPoolPage.test.tsx`
Expected: PASS

- [ ] **Step 4: Run frontend build**

Run: `Set-Location app/frontend; npm run build`
Expected: PASS with a successful production build and no type errors.

- [ ] **Step 5: Commit**

```bash
git add app/backend/tests/test_v2_foundation.py app/backend/tests/test_opportunity_ai_filter.py app/frontend/src/services/api.test.ts app/frontend/src/types/index.test.ts app/frontend/src/components/OpportunityAiFilterPanel.test.tsx app/frontend/src/pages/OpportunityPoolPage.test.tsx
git commit -m "test: cover opportunity fixed filters and ai filtering flow"
```

## Review Notes

- 固定筛选必须优先于 AI 精筛，不允许因为 AI 精筛而削弱分类和基础条件。
- AI 精筛的结果模式必须是“只展示保留项”，不能退化成重新排序。
- 新增前端用户可见文案必须全部使用中文。
- 若实现中发现没有稳定 provider，可先通过可注入 provider 函数完成闭环，测试里使用 monkeypatch/mock，避免把 UI 开发阻塞在真实模型接入上。

## Execution Default

如果没有额外人工选择，本计划默认按“内联执行”推进，顺序从 Task 1 开始依次实现。
