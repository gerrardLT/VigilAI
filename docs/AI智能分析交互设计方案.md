# VigilAI AI 智能分析交互设计方案

## 1. 设计目标

VigilAI 当前的核心能力仍然是 `机会数据爬取 + 聚合展示`。  
AI 智能分析不是为了把产品做成一个泛内容摘要器，而是要把平台升级成一个 `可配置的搞钱筛选工作台`。

本方案的终极目标是：

- 让用户更快筛出 `投资小、回报快、投入产出比高` 的机会
- 让筛选逻辑可配置、可保存、可复用
- 让 AI 负责补足文本理解与解释，而不是替代用户策略
- 让工作台、机会池、详情页都绑定同一套赚钱策略上下文

## 2. 核心定位

AI 智能分析的产品定位不是独立的一页，而是一层横跨全站的能力层：

`爬取 -> 清洗 -> 规则筛选 -> AI 补充判断 -> 结果分发 -> 模板复用`

它在产品中的角色不是“黑盒推荐器”，而是：

- 帮用户把赚钱策略固化成模板
- 按模板逐层筛选机会
- 对规则难以直接表达的文本信号做语义补充
- 输出可解释的结果与排序

## 3. 设计原则

### 3.1 搞钱优先

AI 的首要目标不是内容理解，而是帮助用户快速判断：

- 这条机会是否值得做
- 是否适合 `低投入`
- 是否具备 `快回报`
- 是否满足 `高 ROI`

### 3.2 规则优先，AI 补充

- 规则决定筛选边界
- AI 负责补充判断字段和解释
- AI 不能直接越过用户模板下最终结论

### 3.3 分层筛选，而不是单一打分

不做一个大而全的综合分，而是采用多层漏斗：

1. 硬门槛层
2. 投入产出层
3. 可信度层
4. 优先级层

### 3.4 默认简洁，展开透明

- 默认先给结论
- 原因链路默认折叠
- 用户需要时再展开完整层级说明

### 3.5 模板可复用

- 用户可以保存多套赚钱策略模板
- 平时用模板，筛选时允许临时微调
- 临时调整与原模板严格分开

## 4. 核心用户目标

面向的不是“想了解更多信息”的用户，而是“想用最少时间找到最值得做机会”的用户。

关键目标：

- 快速砍掉不值得看的机会
- 只保留符合当前赚钱策略的结果
- 能够解释为什么保留、为什么淘汰
- 能把有效策略沉淀为模板，长期复用

## 5. 核心信息架构

AI 智能分析由 5 个核心对象组成：

### 5.1 分析模板

用户保存的一套筛选策略，包含：

- 模板名称
- 模板说明
- 适用目标
- 4 层筛选配置
- 默认品类偏好
- 排序策略
- 最近使用时间
- 是否默认模板

### 5.2 筛选层

模板内的层级漏斗结构：

1. 硬门槛层
2. 投入产出层
3. 可信度层
4. 优先级层

### 5.3 分析维度

每层中具体可配置的条件，例如：

- 奖励明确度
- 是否适合个人参与
- 预计投入等级
- 回报周期
- 规则完整度
- 可信度风险

### 5.4 分析结果

每条机会在当前模板下的状态：

- 通过
- 待观察
- 淘汰

并附带：

- 最终推荐等级
- 主要命中原因
- 可展开的层级原因链

### 5.5 模板运行上下文

用于支持临时微调，不直接改动原模板：

- 当前模板
- 本次临时调整项
- 当前筛选结果
- 是否有未保存改动

## 6. 四个核心页面

### 6.1 工作台

工作台负责先给答案，而不是让用户先配置参数。

建议结构：

- 当前生效模板条
- 今日高 ROI 机会区
- 被拦截机会概览
- 模板表现反馈

工作台的作用是：

`在当前默认策略下，先把今天最值得赚的钱推到前面`

### 6.2 机会池

机会池是 AI 筛选主战场。

建议结构：

- 左侧规则面板
- 中间结果列表
- 顶部模板与临时调整提示条
- 支持切换结果状态：
  - 全部
  - 通过
  - 待观察
  - 淘汰

机会池的作用是：

`实时调规则，实时看结果变化，并把有效策略保存下来`

### 6.3 详情页

详情页负责帮助用户判断一条机会是否值得投入。

建议结构：

- 顶部基础元信息
- 当前模板下的 AI 判断区
- 摘要与短描述区
- 可展开的原因链路
- 现有跟进与收藏动作

详情页的作用是：

`解释这条机会为什么值得做，或者为什么不值得浪费时间`

### 6.4 模板中心

模板中心是用户赚钱策略的管理仓库。

建议支持：

- 新建模板
- 复制模板
- 重命名模板
- 设为默认
- 删除模板
- 保存前预览效果

## 7. 规则模板与四层漏斗

### 7.1 第 1 层：硬门槛层

目标：快速淘汰明显不符合策略的机会。

建议条件：

- 是否有明确收益信息
- 是否允许个人参与
- 是否要求组队
- 是否要求线下参与
- 是否要求复杂材料
- 是否已临近截止
- 是否属于当前关注的机会类型

### 7.2 第 2 层：投入产出层

目标：筛出 `投资小、回报快、ROI 高` 的机会。

建议条件：

- 预计投入等级
- 预计准备时间
- 预计回报周期
- 奖励金额区间
- 奖励兑现明确度
- ROI 等级
- 是否适合快速尝试

### 7.3 第 3 层：可信度层

目标：拦下看起来赚钱但规则模糊、可信度不足的机会。

建议条件：

- 来源可信度
- 规则完整度
- 奖励说明清晰度
- 风险等级
- 是否存在营销噪音过高的问题

### 7.4 第 4 层：优先级层

目标：对前面通过的机会做排序，而不是直接淘汰。

建议维度：

- ROI
- 回报速度
- 收益明确度
- 可信度
- 截止紧迫性
- 与模板匹配度

## 8. AI 在系统中的角色

AI 不直接输出黑盒推荐，而是先生成标准化分析字段，供规则消费。

### 8.1 AI 需要补充的分析字段

- `estimated_effort_level`
- `estimated_time_cost`
- `expected_payout_speed`
- `reward_clarity_level`
- `execution_complexity`
- `solo_friendliness`
- `trust_risk_level`
- `money_path_type`
- `roi_level`
- `analysis_confidence`

### 8.2 AI 在每层的职责

- 硬门槛层：补识别是否需要组队、是否线下、是否门槛过高
- 投入产出层：判断投入成本、回报速度、ROI 级别
- 可信度层：判断规则是否模糊、奖励兑现是否不清晰
- 优先级层：解释排序原因，而不是重新定义排序逻辑

### 8.3 AI 输出形式

每条机会默认输出：

- 一句结论
- 2-3 条关键原因
- 可展开的详细原因链
- 判断置信度

## 9. 关键交互状态流

### 9.1 工作台主链路

`打开工作台 -> 查看当前模板下重点机会 -> 进入详情 -> 验证判断 -> 必要时去机会池调规则`

### 9.2 机会池主链路

`选择模板 -> 调整参数 -> 结果实时刷新 -> 另存为新模板`

### 9.3 详情页回流链路

`查看单条机会 -> 展开原因 -> 发现规则偏差 -> 去机会池继续调整`

### 9.4 模板沉淀链路

`复制模板 -> 修改关键阈值 -> 预览效果 -> 保存为长期策略`

## 10. MVP 第一版范围

第一版不做“大而全”，只做最关键的赚钱筛选链路。

### 10.1 MVP 必做

1. 模板系统
2. 四层筛选漏斗
3. AI 分析字段生成
4. 机会池主筛选交互
5. 详情页判断区
6. 工作台重点机会区

### 10.2 MVP 核心模板

建议预置：

- 快钱模式
- 低投入高回报模式
- 稳妥可信模式

### 10.3 第一版核心条件

- 是否有明确收益
- 是否个人可做
- 是否需要组队
- 是否线下参与
- 预计投入等级
- 回报周期
- 奖励明确度
- ROI 等级
- 来源可信度
- 规则完整度

## 11. 第一版暂不做

以下功能建议明确后置：

- AI 助手聊天面板
- 自然语言生成规则
- 强个性化画像
- 自动行动建议系统
- 用户反馈训练闭环
- 多用户共享模板
- 复杂可视化分析报表
- 全文级深度分析工作流

## 12. 页面级组件清单

### 12.1 通用组件

- `TemplateSwitcher`
- `TemplateSummaryBar`
- `FilterLayerPanel`
- `RuleConditionRow`
- `UnsavedChangesBar`
- `AnalysisResultBadge`
- `ReasonSummary`
- `ReasonChainCollapse`
- `TemplatePreviewCard`

### 12.2 工作台组件

- `ActiveTemplateHero`
- `HighRoiOpportunityList`
- `RejectedReasonSummary`
- `TemplatePerformanceCard`

### 12.3 机会池组件

- `TemplateControlSidebar`
- `LayeredFilterPanel`
- `OpportunityResultTabs`
- `OpportunityAnalysisCard`
- `TemporaryAdjustmentsBar`

### 12.4 详情页组件

- `AiDecisionPanel`
- `QuickReasonList`
- `RulePassFailTimeline`
- `TemplateContextHint`

### 12.5 模板中心组件

- `TemplateLibraryGrid`
- `TemplateEditor`
- `TemplatePreviewRunner`
- `TemplateDuplicateDialog`

## 13. 数据与接口建议

### 13.1 后端新增核心对象

- `analysis_templates`
- `analysis_template_layers`
- `analysis_template_conditions`
- `activity_analysis_results`
- `activity_analysis_explanations`

### 13.2 建议新增接口

- `GET /api/analysis/templates`
- `POST /api/analysis/templates`
- `PATCH /api/analysis/templates/{id}`
- `POST /api/analysis/templates/{id}/duplicate`
- `POST /api/analysis/templates/{id}/preview`
- `POST /api/analysis/run`
- `GET /api/analysis/results`
- `GET /api/analysis/results/{activity_id}`

### 13.3 前端状态建议

前端需要明确区分：

- 默认模板
- 当前正在使用的模板
- 临时调整
- 未保存状态
- 结果刷新状态

## 14. 成功标准

这套 AI 智能分析方案上线后，至少应满足：

1. 用户能基于模板快速筛出高 ROI 机会
2. 用户能看懂为什么某条机会被保留或淘汰
3. 用户能把一次有效的筛选策略保存为模板
4. 工作台不再只是列表汇总，而是当前赚钱策略的看板
5. 详情页不再只是展示页，而是支持判断的页面

## 15. 一句话总结

VigilAI 的 AI 智能分析，不应该做成一个泛化的内容助手，而应该做成：

`一个可配置、可解释、可复用的搞钱筛选引擎。`
## Status: Historical Context

This document describes the original rule-first AI analysis MVP and is kept as historical context.

Current implementation work should follow:
`docs/superpowers/specs/2026-03-27-vigilai-agent-analysis-design.md`

That agent-analysis spec supersedes this document for new backend orchestration, review/writeback, and replay-evaluation work.
