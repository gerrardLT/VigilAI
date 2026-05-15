# 机会工作台深度拆解

这份文档只描述当前仓库里已经存在的实现，不描述历史规划，也不描述理想架构。

重点是把“机会工作台”这条链路从路由、页面、Hook、API、后端聚合、同步机制到主要风险完整讲清楚。

## 1. 这里说的“机会工作台”具体指什么

在当前项目里，“机会工作台”不是整个机会域，也不是所有机会页面的统称。

它特指当前的机会域主入口页面：

- `/opportunity/workspace`

对应的前端页面文件是：

- `app/frontend/src/pages/WorkspacePage.tsx`

它的职责不是承载所有机会操作，而是作为一个行动优先级入口，把用户导向：

- 机会池
- 跟进页
- 分析结果页
- 来源页
- 日报页

所以它本质上是一个“决策与导流页面”，不是简单首页。

## 2. 路由入口和页面壳是谁在管

工作台路由定义在：

- `app/frontend/src/App.tsx`

当前链路是：

1. `App.tsx` 挂载 `/opportunity` 域
2. `DomainShellLayout` 提供机会域外壳
3. 机会域导航来自 `opportunityPaths`
4. `WorkspacePage` 挂在 `/opportunity/workspace`

需要特别强调的一点：

- `/workspace` 已经不是正式入口
- `/workspace` 只是兼容重定向，最终会跳到 `/opportunity/workspace`

这正是很多旧文档已经过时的地方。

## 3. 前端依赖图：工作台到底依赖了哪些状态

`WorkspacePage` 不是单一数据源页面，它同时依赖四路状态：

- `useWorkspace()`
- `useAnalysisTemplates()`
- `useAgentAnalysisJobs()`
- `useTracking()`

也就是说，这个页面不是“后端一次返回完整页面模型”，而是：

- 后端返回一部分工作台聚合数据
- 前端再叠加模板状态
- 再叠加 Agent 分析任务状态
- 再叠加跟进队列状态

这是当前实现最关键的结构事实之一。

## 4. 后端到底给了工作台什么

`useWorkspace()` 调用的是：

- `GET /api/workspace`

API 层没有复杂逻辑，只是转发到：

- `request.app.state.data_manager.get_workspace()`

当前返回的 `WorkspaceResponse` 主要包含：

- `overview`
- `top_opportunities`
- `digest_preview`
- `trends`
- `alert_sources`
- `first_actions`
- `analysis_overview`
- `blocked_opportunities`

注意，这不是完整屏幕状态，只是一个聚合起点。页面上很多可见区域仍然是前端自己二次计算出来的。

## 5. 页面各块是怎么拼出来的

### 5.1 顶部 Banner

顶部 Banner 用到的不是单一路径数据，而是混合数据：

- `workspace.overview.recent_activities`
- `workspace.overview.tracked_count`
- `workspace.overview.favorited_count`
- 当前默认分析模板名

所以 Banner 同时依赖：

- 后端工作台聚合
- 单独拉取的模板状态

### 5.2 Agent 分析摘要区

“Agent 分析摘要”依赖：

- `workspace.analysis_overview`
- `defaultTemplate`
- `activeJob`
- 或 `jobs` 里最近一个 batch job

这块是旧机会系统和新 Agent 分析流的交汇点。

### 5.3 行动卡片区

工作台上的 action cards 不是单纯指标展示，而是带跳转意图的入口：

- 跳到按排序筛过的机会池
- 跳到按 focus 筛过的跟进页
- 跳到来源页

所以这块本质上是“快捷工作路由器”。

### 5.4 高价值待转化区

这个区块不是直接信任后端返回，而是经过前端二次筛：

1. 后端给 `top_opportunities`
2. 前端叠加 `trackingOverrides`
3. 前端再跑 `isHighValue()`
4. 再过滤掉 `is_tracking === true`

这说明页面并没有只依赖服务端结果，而是维护了一层本地乐观状态。

### 5.5 今日先做什么

这块主要信任后端给的 `first_actions`。

和“高价值待转化”不同，它不是从 tracking 列表重新推导出来的，而是后端提前排好的一组候选行动。

### 5.6 提醒区和积压区

这两个区块不是后端工作台聚合直接给的，而是完全由前端从 `useTracking()` 拿到的列表中再算：

- `reminderTodayItems`
- `reminderOverdueItems`
- `backlogItems`

也就是说，工作台页面同时存在两种真相来源：

- `/api/workspace` 提供机会视角聚合
- `/api/tracking` 提供执行队列视角聚合

## 6. 页面状态编排方式

`WorkspacePage` 既有服务端状态，也有本地状态。

本地状态包括：

- `toast`
- `closureFeedback`
- `syncing`
- `syncNonce`
- `actionLoading`
- `trackingOverrides`

这些本地状态说明：这个页面不只是渲染器，而是自己承担了一部分交互编排职责。

## 7. 跟进同步是怎么做的

当前前端用一个浏览器事件来做跨页面同步：

- `vigilai:tracking-updated`

共享定义在：

- `app/frontend/src/utils/trackingSync.ts`

但是 `WorkspacePage.tsx` 里又本地写死了一次同样的事件名，而不是直接 import 常量。

这有明显的维护风险：

- 改名时容易漏
- 页面和工具文件之间的契约重复定义
- 后续重构时不够稳

## 8. 为什么 `useWorkspace` 和 `useTracking` 都监听同一个事件

当前同步策略是：

- `useWorkspace()` 监听跟进更新事件，收到后重新请求 `/api/workspace`
- `useTracking()` 也监听同一个事件，收到后重新请求 `/api/tracking`

这个设计的优点是简单、直观、稳定。

但代价也很明确：一次“加入跟进 / 收藏”动作，通常会触发：

- 一次写接口
- 一次浏览器事件广播
- 一次 tracking refetch
- 一次 workspace refetch

从一致性角度没问题，但从成本上不算轻。

## 9. 为什么 `WorkspacePage` 没直接用 `useTracking` 的写方法

虽然仓库里已经有：

- `useTracking().createTracking()`
- `useTracking().updateTracking()`

但 `WorkspacePage` 并没有走这层封装，而是直接 import `api` 去调用 tracking 接口。

这样做的实际效果是：

- 页面自己掌握 loading 状态
- 页面自己掌握 closure feedback
- 页面自己掌握 optimistic override

这对页面体验是方便的，但会带来一个结构问题：

- `useTracking` 有一套跟进写逻辑
- `WorkspacePage` 又有一套自己的跟进写逻辑

职责重复，后续容易漂。

## 10. 后端聚合链路具体在哪里

机会工作台的后端聚合逻辑主要在：

- `app/backend/data_manager_components/workspace.py`

`get_workspace()` 当前会组合这些数据：

- `get_stats(include_news=False)` 的统计概览
- top opportunities 查询
- trends 查询
- alert sources 查询
- first actions 查询
- analysis rows 查询
- blocked opportunities 查询
- digest preview
- full tracking list

这个实现方式的优点是集中、直接、容易继续补字段。

但它仍然属于：

- 同步式
- `DataManager` 大而全
- 页面聚合逻辑和领域存储逻辑耦合较深

## 11. 当前实现的优点

### 11.1 路由边界比以前清楚

现在 `/opportunity/*`、`/agent`、`/selection/*` 三个域分开了，页面职责比旧平铺路由清楚得多。

### 11.2 工作台不是装饰首页，而是真工作面

它已经不是一个“看总数”的首页，而是一个：

- 可直接加入跟进
- 可直接收藏
- 可跳转带 focus 的跟进视图
- 可跳转带 sort 的机会池视图

的行动面。

### 11.3 后端至少给了一个稳定聚合入口

虽然页面还要自己二次计算，但 `/api/workspace` 已经把最核心的概览块集中起来了，没有把页面逼成十几个接口拼装。

### 11.4 同步机制已经有测试覆盖

`WorkspacePage.test.tsx` 已经明确验证了：

- overview 渲染
- digest 清洗
- direct track / favorite
- 高价值转跟进
- action card 路由
- reminder / backlog 路由
- 跨页面 tracking 更新后的同步反馈

这说明页面已经被当成关键工作流页面在测，而不是轻页面。

## 12. 当前最值得注意的真实问题

### 12.1 分数尺度前后端语义不一致

前端 `WorkspacePage.isHighValue()` 用的是：

- `score >= 8`

但后端机会评分 `_score_components()` 显然是 0 到 100 语义。

这意味着：

- 工作台“高价值待转化”的阈值过低
- 很多只是中等偏上的机会也会被算进高价值

这是这次代码阅读里最明确的逻辑不一致问题。

### 12.2 后端仍有明显的 Python 侧大列表处理

例如：

- `get_activities()` 先 `fetchall()` 再 Python 过滤和分页
- `get_stats()` 先全量读 `activities` 再算统计
- `get_workspace()` 会调用 `get_tracking_items()`，后者本身也会把 tracking join 结果全拿出来

当前数据量下还能接受，但数据上来后，工作台会先在：

- 响应时间
- 内存占用

这两处吃亏。

### 12.3 页面状态真相来源分裂

这个页面同时依赖：

- backend workspace aggregate
- backend tracking list
- frontend optimistic override
- frontend local derived slices

所以它没有真正统一的 screen-level state model。

当前能跑，但复杂度在积累。

### 12.4 跟进写逻辑重复

`useTracking` 和 `WorkspacePage` 都在维护写 tracking 的路径。

现在看只是有点重复，后续如果：

- 错误提示文案变化
- 事件广播机制变化
- API 契约变化

这两个地方很容易漂出不同步行为。

### 12.5 收藏动作依赖“update 即 upsert”

`favoriteActivity()` 直接调：

- `api.updateTracking(activity.id, { is_favorited: true })`

这实际上依赖后端 tracking API 允许“未跟进时也能 PATCH 成功并隐式创建记录”。

后端现在确实支持，但这个契约是隐式的，不够一眼清楚。

### 12.6 同时存在 optimistic override 和全局 refetch

页面既维护本地 `trackingOverrides`，又通过全局事件触发 refetch。

这两层都能保证最终一致性，但也意味着：

- 页面本地有一套短期真相
- hooks 层又有一套后端真相

逻辑不算脆，但确实比单路径更复杂。

## 13. 建议的下一轮代码收敛顺序

如果要继续改代码，不建议大拆大重来，建议按这几个顺序收：

1. 先统一分数尺度，修掉 `isHighValue()` 阈值语义问题
2. 把 `WorkspacePage` 里的事件名改成 import 共享常量
3. 决定 tracking 写逻辑到底收口到 `useTracking` 还是页面命令函数
4. 再把 `get_activities()`、`get_stats()`、`get_workspace()` 里最重的 Python 侧过滤往 SQL 下推
5. 最后再考虑把 workspace 聚合从 `DataManager` 里拆成专门服务

## 14. 对应的当前说明文档

- `docs/当前系统架构与技术实现说明.md`
- `docs/当前项目核心功能梳理.md`
- `README.md`
