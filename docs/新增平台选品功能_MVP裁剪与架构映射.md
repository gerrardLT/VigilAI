# 新增平台选品功能 MVP 裁剪与现有架构映射

## 1. 结论

这份 [新增平台选品功能 PRD](./新增平台选品功能.md) 更接近一条新产品线，不是给现有 VigilAI 增加一个小功能。

当前项目主域仍然是“开发者机会情报工作台”，核心对象是 `Activity`，页面、分类、来源类型、工作台指标和日报语义都围绕这个主域构建。直接把现有 `activities` 体系原地改造成“淘宝/闲鱼选品”会同时破坏两条业务线，后续维护成本会很高。

建议做法只有一条：

- 在当前仓库内新增一个独立的 `product-selection` 有界上下文
- 复用现有前端壳层、FastAPI 组织方式、SQLite 持久化模式、跟进状态模式、AI 调用基础设施
- 不复用现有 `Activity / Category / Source / Digest` 业务语义

同时，MVP 不应该从“完整跨平台选品系统”起步，而应该先验证一个更小的闭环：

`输入关键词/链接 -> 生成机会池 -> 看详情 -> 保存/对比 -> 形成下一步动作`

---

## 2. 裁剪后的可开发 MVP

### 2.1 MVP 只验证一件事

验证用户是否愿意用“淘宝/闲鱼公开信号 + AI 解释”更快找到并保存值得继续研究的商品机会。

不是先验证监控、报告、团队协作，也不是先验证深度平台授权接入。

### 2.2 MVP 目标用户

- 淘宝中小卖家
- 闲鱼职业/半职业卖家
- 小型选品工作室

本阶段先不覆盖：

- 品牌孵化团队的复杂协作场景
- 团队权限与管理后台
- 1688 供应链映射

### 2.3 MVP 核心流程

1. 用户输入关键词、类目，或淘宝/闲鱼商品链接
2. 系统创建一次“选品研究任务”，拉取并归一化候选结果
3. 系统输出机会池，用户按平台、价格带、风险、置信度筛选
4. 用户打开详情，查看需求、竞争、价格带、风险、AI 推荐理由
5. 用户收藏、写备注、加入对比，形成下一步动作
6. 工作台展示最近查询、已保存机会、待跟进行动

### 2.4 MVP P0 功能范围

| 模块 | P0 保留内容 | 裁剪说明 |
| --- | --- | --- |
| 输入入口 | 关键词、类目、淘宝/闲鱼商品链接 | 不做截图上传，不做店铺链接批量分析 |
| 研究任务 | 创建任务、轮询状态、缓存最近结果 | 先做查询驱动，不做全站定时监控 |
| 机会池 | 列表、卡片、分页、筛选、排序、收藏、加入对比 | 批量导出先不做 |
| 筛选排序 | 平台、类目、价格带、风险、置信度；按机会分、需求、低竞争排序 | 保持最小必要维度 |
| 机会详情 | 标题、图片、平台、价格带、需求代理指标、竞争代理指标、风险标签、AI 推荐理由 | 保留“为什么值得做”主链路 |
| 价格建议 | 输出建议价格区间与理由 | 只做区间，不做复杂利润模拟 |
| 跨平台验证 | 在有足够信号时展示“另一平台是否存在验证信号” | 不做完整双向迁移分析页 |
| 收藏跟进 | 收藏、状态、备注、下一步动作 | 复用现有 tracking 思路 |
| 对比 | 2-5 个机会对比需求/竞争/价格/风险/置信度 | 客户端或轻量服务端实现即可 |
| 最小工作台 | 最近查询、已保存高置信机会、待跟进事项 | 不做日报和团队摘要 |

### 2.5 明确移出 MVP 的内容

以下内容进入 V1 之后再做，不进入首个可开发版本：

- 关键词监控、类目监控、竞品监控、机会失效提醒
- 报告中心、PDF 导出、会议版摘要
- 团队工作区、角色权限、审计日志后台
- 用户可编辑的策略模板中心
- 1688 货源匹配
- 批量链接导入、截图识别、插件入口
- 深度淘宝 `<->` 闲鱼迁移评分
- 小程序、客服系统、聚石塔等深接入

### 2.6 MVP 明确不做

- ERP、订单、打单、仓配
- 广告投放管理
- 平台私有数据复现
- 24x7 自动抓全网商品库

---

## 3. MVP 的产品定义与对象模型

### 3.1 与当前 VigilAI 的核心差异

当前 VigilAI 是“源驱动”的：

`固定来源 -> 周期抓取 -> 活动池 -> 判断 -> 跟进`

选品 MVP 应该是“查询驱动”的：

`用户输入 -> 即席研究任务 -> 机会池 -> 详情判断 -> 保存/对比`

这意味着可以复用 UI 和 API 组织方式，但不能把数据入口仍然建在当前 `sources -> scrapers -> activities` 主链上。

### 3.2 MVP 的最小核心对象

#### ProductResearchQuery

- `id`
- `query_type`：`keyword | category | listing_url`
- `query_text`
- `platform_scope`：`taobao | xianyu | both`
- `status`
- `created_at`
- `updated_at`

#### ProductOpportunity

- `id`
- `query_id`
- `platform`
- `platform_item_id`
- `title`
- `image_url`
- `category_path`
- `price_low`
- `price_mid`
- `price_high`
- `demand_score`
- `competition_score`
- `price_fit_score`
- `risk_score`
- `cross_platform_signal_score`
- `opportunity_score`
- `confidence_score`
- `risk_tags`
- `reason_blocks`
- `recommended_action`
- `source_urls`
- `snapshot_at`
- `created_at`
- `updated_at`

#### ProductOpportunitySignal

- `id`
- `opportunity_id`
- `platform`
- `signal_type`
- `value_json`
- `sample_size`
- `freshness`
- `reliability`

#### ProductTrackingState

- `opportunity_id`
- `is_favorited`
- `status`
- `notes`
- `next_action`
- `remind_at`
- `created_at`
- `updated_at`

### 3.3 MVP 评分模型建议

首版只保留最容易落地的 5 个维度：

`Opportunity Score = 0.35 * Demand + 0.25 * LowCompetition + 0.20 * PriceFit + 0.10 * CrossPlatformSignal - 0.10 * Risk`

说明：

- `Demand`：搜索热度、互动量、上架活跃度等公开代理信号
- `LowCompetition`：同款密度、卖家拥挤度、价格带拥挤度
- `PriceFit`：建议价格区间是否存在合理空间
- `CrossPlatformSignal`：另一平台是否出现辅助验证信号
- `Risk`：侵权、违规、售后、物流等风险

如果没有可用的跨平台验证信号，首版可以对其余权重做归一化，不强求所有机会都具备双平台样本。

### 3.4 AI 输出的最小结构约束

每条 AI 推荐理由必须回答 5 个问题：

1. 为什么系统判断这里有需求
2. 为什么系统认为还存在可切入空间
3. 建议价格带是什么
4. 主要风险是什么
5. 如果今天开始做，第一步动作是什么

AI 输出必须绑定结构化字段，不能只存长文本结论。

---

## 4. 与当前代码架构的映射方案

### 4.1 哪些部分可以直接复用

| 可复用部分 | 现有落点 | 复用方式 |
| --- | --- | --- |
| 路由与应用壳层 | `app/frontend/src/App.tsx`、`app/frontend/src/components/Layout.tsx`、`app/frontend/src/components/Header.tsx` | 继续复用整体布局、导航模式和容器宽度 |
| 页面组织方式 | `app/frontend/src/pages/*.tsx` | 继续沿用“页面 + types + services + tests”结构 |
| API 服务封装 | `app/frontend/src/services/api.ts` | 新增一份 `productSelectionApi.ts`，保持同样调用风格 |
| 类型定义习惯 | `app/frontend/src/types/index.ts` | 新增 `productSelection.ts`，不要塞回现有 `Activity` 类型文件 |
| FastAPI 组织方式 | `app/backend/api.py` | 保持同一应用实例，新增独立路由前缀 |
| SQLite 数据访问模式 | `app/backend/data_manager.py` | 复用“Repository/DataManager 风格”，但建议选品域单独封装 |
| 跟进状态模式 | `tracking_items` 和相关接口 | 语义可复用，数据表不要共用 |
| AI Provider 抽象 | `app/backend/analysis/providers/*` | 继续复用 provider/router，不复用当前开发者机会 prompt 和 schema |
| 测试组织方式 | `app/frontend/src/pages/*.test.tsx`、`app/backend/tests/*.py` | 直接按同样方式为新垂域补测试 |

### 4.2 哪些部分不建议原地改

| 当前对象/模块 | 不建议直接复用的原因 |
| --- | --- |
| `Activity` | 语义是“活动/机会情报”，不是“商品选品结果” |
| `Category` 枚举 | 当前分类是 `hackathon / grant / airdrop / dev_event`，与电商完全不同 |
| `SourceType` 与 `sources` 表 | 当前是抓取来源治理，不是淘宝/闲鱼研究任务 |
| `workspace` 聚合指标 | 当前指标是活动量、来源量、日报预览，不是选品研究态 |
| `digests` | 当前是开发者机会日报，不是选品报告中心 |
| 现有 `analysis_templates` 业务语义 | 当前模板围绕开发者机会筛选规则，不是商品机会评分规则 |

结论：可以复用工程模式，但不能共用业务主表和业务枚举。

### 4.3 建议的前端路由与页面映射

建议新增独立路由组，避免与当前主域混用：

- `/selection/workspace`
- `/selection/opportunities`
- `/selection/opportunities/:id`
- `/selection/compare`
- `/selection/tracking`

映射关系如下：

| 选品 MVP 模块 | 当前可参考页面 | 建议新页面 | 说明 |
| --- | --- | --- | --- |
| 选品工作台 | `WorkspacePage.tsx` | `SelectionWorkspacePage.tsx` | 复用概览卡片、趋势区、待办区布局 |
| 机会池 | `ActivitiesPage.tsx` | `SelectionOpportunitiesPage.tsx` | 复用筛选栏、排序、列表、批量选择交互 |
| 机会详情 | `ActivityDetailPage.tsx` | `SelectionOpportunityDetailPage.tsx` | 复用详情区块、收藏/备注/下一步动作面板 |
| 收藏跟进 | `TrackingPage.tsx` | `SelectionTrackingPage.tsx` | 复用状态切换和备注维护模式 |
| 对比页 | 无直接现成页面 | `SelectionComparePage.tsx` | 新增页面，数据结构可沿用表格对比思路 |
| 规则模板 | `AnalysisTemplatesPage.tsx` | V1 再做 | MVP 先内置一套系统规则，不开放给用户编辑 |
| 报告中心 | `DigestsPage.tsx` | V1 再做 | MVP 不进入主导航 |
| 数据源健康 | `SourcesPage.tsx` | 内部管理页可后置 | 不作为首个用户主流程 |

前端建议新建文件：

- `app/frontend/src/types/productSelection.ts`
- `app/frontend/src/services/productSelectionApi.ts`
- `app/frontend/src/pages/selection/SelectionWorkspacePage.tsx`
- `app/frontend/src/pages/selection/SelectionOpportunitiesPage.tsx`
- `app/frontend/src/pages/selection/SelectionOpportunityDetailPage.tsx`
- `app/frontend/src/pages/selection/SelectionComparePage.tsx`
- `app/frontend/src/pages/selection/SelectionTrackingPage.tsx`
- 对应的页面测试文件

前端建议修改文件：

- `app/frontend/src/App.tsx`
- `app/frontend/src/components/Header.tsx`

### 4.4 建议的后端 API 映射

建议统一使用独立前缀：

- `/api/product-selection/*`

首版 API 可以控制在下面这组：

| 选品能力 | 建议接口 | 可复用的现有模式 |
| --- | --- | --- |
| 创建研究任务 | `POST /api/product-selection/research-jobs` | 参考 `agent-analysis/jobs` 的任务创建与轮询思路 |
| 查询任务状态 | `GET /api/product-selection/research-jobs/{job_id}` | 复用异步任务状态设计 |
| 查询机会池 | `GET /api/product-selection/opportunities` | 参考 `GET /api/activities` 的筛选、排序、分页模式 |
| 查询机会详情 | `GET /api/product-selection/opportunities/{id}` | 参考 `GET /api/activities/{id}` 的 detail 组织方式 |
| 收藏/跟进 | `POST/PATCH/DELETE /api/product-selection/tracking/{id}` | 参考现有 tracking 接口 |
| 获取工作台 | `GET /api/product-selection/workspace` | 参考 `GET /api/workspace` 的聚合返回结构 |
| 对比 | `GET /api/product-selection/compare?ids=...` 或 `POST /compare` | 新增轻量聚合接口 |

MVP 不建议首版就暴露：

- 模板中心接口
- 监控规则接口
- 报告导出接口
- 反馈闭环接口

### 4.5 建议的后端目录结构

当前后端是以平铺文件为主。为了避免把电商域逻辑继续堆进 `data_manager.py`，建议对新垂域单独建包：

- `app/backend/product_selection/__init__.py`
- `app/backend/product_selection/models.py`
- `app/backend/product_selection/schemas.py`
- `app/backend/product_selection/repository.py`
- `app/backend/product_selection/service.py`
- `app/backend/product_selection/scoring.py`
- `app/backend/product_selection/ai_explainer.py`
- `app/backend/product_selection/adapters/taobao.py`
- `app/backend/product_selection/adapters/xianyu.py`

需要修改的现有文件：

- `app/backend/api.py`
- `app/backend/main.py`
- `app/backend/config.py`

如果仍然把所有选品表、评分逻辑和平台适配器继续写进当前 `data_manager.py`，短期会快一点，但 2-3 次迭代后一定会和现有 `activities` 域纠缠在一起。

### 4.6 建议的数据表

建议首版只建 4 张核心表：

| 表名 | 用途 | 备注 |
| --- | --- | --- |
| `selection_queries` | 记录用户输入与任务状态 | 查询驱动入口 |
| `selection_opportunities` | 存放机会池结果与评分摘要 | 每条结果保留一份快照 |
| `selection_opportunity_signals` | 存放分平台信号与证据 | 支撑详情解释和评分回放 |
| `selection_tracking_items` | 收藏、状态、备注、下一步动作 | 与当前 tracking 语义相似，但不要共表 |

首版可以暂时不建：

- `selection_reports`
- `selection_watch_rules`
- `selection_template_profiles`
- `selection_team_members`

### 4.7 对 AI 与规则引擎的复用边界

可以复用：

- `app/backend/analysis/providers/router.py`
- provider 配置与模型路由
- 结构化输出校验的做法

不建议直接复用：

- 当前开发者机会的 prompt
- 当前分析模板字段
- 当前 `Activity` 评分规则

选品域应该有自己的：

- 评分器 `scoring.py`
- 解释器 `ai_explainer.py`
- 平台信号到结构化字段的归一层

---

## 5. 建议的实施顺序

### 5.1 第一阶段：搭骨架，不接复杂能力

目标：

- 跑通独立路由组
- 建好 4 张核心表
- 返回一组可渲染的 mock 或静态结果

完成标志：

- 前端能进入 `/selection/*`
- 后端有独立 API 前缀
- 不影响现有开发者机会链路

### 5.2 第二阶段：跑通查询 -> 机会池 -> 详情

目标：

- 接入淘宝/闲鱼最小平台适配器
- 支持关键词/链接输入
- 返回可筛选的机会池
- 打开详情页看到结构化信号和 AI 理由

完成标志：

- 单次查询可以得到可用结果
- 详情页能回答“为什么值得做”

### 5.3 第三阶段：补齐收藏、对比、工作台

目标：

- 支持收藏和下一步动作
- 支持 2-5 个机会对比
- 工作台展示最近查询与高置信已保存机会

完成标志：

- 用户能从“看到结果”进入“形成动作”

### 5.4 第四阶段：再决定要不要进入 V1

只有当下面 3 件事成立，才建议继续做监控、报告和团队能力：

- 用户持续保存机会，而不是只搜一次
- 详情页解释被频繁查看
- 收藏后的机会确实会进入后续动作

如果这 3 件事没成立，说明当前问题不在“功能不够多”，而在“机会质量或解释可信度不够”。

---

## 6. 最终建议

对这份 PRD，最合理的处理方式不是“照单全做”，而是做两层拆分：

第一层，保留原始 PRD 作为完整产品愿景。  
第二层，按本文裁成一个真正可开发、可验证、可接到当前仓库里的 MVP。

落地时要坚持两个原则：

- 工程上复用壳层和基础设施
- 业务上隔离主域和数据模型

只要坚持这两个原则，这个新方向可以在当前仓库里落地；如果直接改现有 `Activity` 主域，后面很快就会进入“一边救旧功能、一边补新需求”的混乱状态。
