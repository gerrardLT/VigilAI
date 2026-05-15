# 奖励活动发现 AI Agent 设计稿

## 1. 目标

将当前偏“机会工作台 / 跟进 / 日报 / 执行流”的机会系统，收缩为一个更聚焦的产品：

**面向全网通用奖励活动的自动发现型 AI Agent。**

这个系统的核心任务是：

1. 抓取全网公开网页和社交动态内容
2. 宽松召回疑似奖励活动
3. 由 AI Agent 自主进行深度检索、追证据、结构化判断
4. 将结果沉淀为可检索、可复核、可重跑的结构化机会库

## 2. 不再做什么

第一阶段不再围绕以下产品目标继续扩展：

- 机会工作台的人工作业流
- 跟进系统
- 日报系统
- 收藏 / 加入推进
- “今天先做什么”之类的人工执行入口
- 共享 Agent 会话作为主产品入口
- 多域产品叙事
- 复杂模板中心

这些能力可以保留为 legacy，但不再是主产品方向。

## 3. 产品定义

### 3.1 产品一句话

一个自动发现优先的 AI Agent，从全网抓取通用奖励活动相关内容，先宽松召回，再深度筛选，最后形成结构化机会库。

### 3.2 第一阶段覆盖的目标机会

第一阶段聚焦“通用奖励活动”，包括但不限于：

- 拉新活动
- 邀请有奖
- 注册奖励
- 完成任务得奖励
- 打卡奖励
- 试玩奖励
- 投稿奖励
- 测试奖励
- 其他用户可参与、且带明确激励的活动

### 3.3 第一阶段来源类型

采用混合来源策略：

- 公开网页
- 社交平台
- 搜索发现入口

### 3.4 采集与判断策略

- 采集阶段：宽松模式
- 深筛阶段：AI Agent 深度检索 + 自主追证据 + 结构化判断

系统最终输出五级分类：

- `高价值`
- `可跟`
- `待补证据`
- `低价值`
- `拒绝`

## 4. 核心架构

第一阶段不再按单条直线流水线设计，而是按一个真正的 Agentic Discovery System 设计。

系统仍然有固定的数据流，但核心判断部分改为多 Agent 协作：

1. 来源发现层
2. 原始内容抓取层
3. 宽松召回层
4. Agent 调查与追证据层
5. 结构化机会库
6. 结果消费层

### 4.0.1 基础设施选型原则

网页抓取与抽取底座不从零自研，优先直接采用 **Crawl4AI**。

原因：

- 已具备异步 crawler 能力
- 已支持动态页面处理
- 已支持 deep crawl
- 已支持 LLM extraction
- 已支持 CSS / XPath / schema extraction
- 已支持对 LLM 友好的 Markdown 输出
- 已支持较长抓取过程的恢复能力

因此本系统的边界应明确为：

- **Crawl4AI 负责抓取、清洗、抽取**
- **本系统负责 Agent 决策、追证据、评估、合并、沉淀**

也就是说，不再自造通用 crawler，而是在 Crawl4AI 之上构建你的业务 Agent。

### 4.0 总体原则

这个系统不能只是：

- 抓回来
- 做一次 LLM 分类
- 然后入库

那样只是 AI 增强采集系统，不是“真正的 AI Agent 系统”。

真正的 Agent 必须具备：

- 自己判断当前证据够不够
- 自己判断下一步该搜什么
- 自己决定要不要继续追外链
- 自己决定要不要继续打开详情页 / FAQ / 规则页
- 在证据不足时进入调查回路，而不是立刻给最终结论

### 4.1 来源发现层

来源分三类：

1. 固定高价值来源
   - 官方活动页
   - 官方公告页
   - 奖励中心
   - 邀请页
   - campaign / task / bounty 页面

2. 搜索发现来源
   - 搜索引擎查询模板
   - 站内搜索页
   - 标签页
   - 列表页

3. 社交流来源
   - X
   - Telegram
   - Discord
   - Reddit
   - 公众号 / 博客 / 社区帖子

### 4.2 抓取层

抓取对象统一归一为三类文档：

1. 页面型
   - 活动页、公告页、帮助页、落地页
2. 帖子型
   - 社交贴、论坛贴、社区讨论
3. 聚合型
   - 搜索结果页、列表页、频道页

抓取策略采用两段式：

- 先广撒网抓列表和线索
- 再对命中项做详情深抓

社交内容默认先作为线索，不直接等价为机会事实。

### 4.3 宽松召回层

目标：尽量不漏掉疑似奖励活动。

输入：

- 标题
- 正文或摘要
- 标签 / 频道名 / 分类
- 时间信息
- 外链标题

输出：

- `疑似奖励活动`
- `疑似拉新活动`
- `疑似任务奖励`
- `疑似邀请有奖`
- `非目标内容`

并附带：

- 召回原因
- 触发模式
- 是否需要详情补抓

召回层采用混合方案：

- 关键词规则
- 模式识别
- 轻量 AI / 小 prompt 判断

### 4.4 Agent 调查与追证据层

这是系统核心能力层。

这里不再是一次性的“深筛 prompt”，而是一组协作 Agent。

建议拆成 5 个角色：

#### 4.4.1 Scout Agent

职责：

- 发现新的来源入口
- 扩展搜索查询模板
- 从聚合页 / 搜索页 / 社交流里发现潜在线索

它关心的是：

- 哪些地方值得继续看
- 哪些 URL 值得进入下一步

#### 4.4.2 Collector Agent

职责：

- 抓取列表页
- 抓取详情页
- 抓取外链
- 抓取社交帖子正文
- 把结果标准化为原始文档与证据片段

它关心的是：

- 先拿到尽可能完整的材料
- 不负责最终判断

实现策略：

- Collector Agent 默认基于 Crawl4AI 实现
- 使用 Crawl4AI 处理：
  - 普通详情页抓取
  - deep crawl
  - 结构化初步抽取
  - Markdown 化
  - 动态页内容获取
- 必要时再补充浏览器自动化能力处理特殊页面

#### 4.4.3 Investigator Agent

职责：

- 当证据不足时，自主继续检索和追证据
- 决定还要不要继续查
- 决定下一跳去哪里

典型行为：

- 发现“有奖励”但没细则时，继续找活动规则页
- 发现社交帖子不完整时，继续追其引用外链
- 发现活动页提到 FAQ 时，自动打开 FAQ
- 发现时间不明确时，继续找公告页 / 说明页 / 评论区补证据

这是“真正 AI Agent”最关键的一层。

#### 4.4.4 Evaluator Agent

职责：

- 基于当前证据包做正式结构化判断
- 输出五级分类
- 输出结构化字段
- 输出缺失证据和风险

Evaluator 不负责盲目补抓，它依赖 Investigator 补证据后的结果再给最终结论。

#### 4.4.5 Merger Agent

职责：

- 合并同一活动的多来源证据
- 去重
- 更新已有机会
- 判断这是新机会还是旧机会的新增证据

因为同一个奖励活动可能同时出现在：

- 官方活动页
- 社交帖子
- 聚合资讯页
- 二次转述页

这层必须存在，否则结果库会充满重复项。

### 4.5 Agent 调查回路

建议把深筛核心设计成一个有限循环：

1. 候选进入 Evaluator 初判
2. 如果证据充分，直接分类
3. 如果证据不足，转给 Investigator
4. Investigator 决定：
   - 搜新关键词
   - 打开外链
   - 追规则页
   - 追 FAQ
   - 追活动细则
5. Collector 执行抓取
6. 新证据回到 Evaluator
7. 如果仍不足，进入：
   - 再查一轮
   - 或归类为 `待补证据`

这个回路必须有边界，例如：

- 最多调查 N 轮
- 最多新增 M 个链接
- 超时后强制结束

避免系统无限追踪。

### 4.6 Evaluator 的正式输入输出

输入不是原始全文直喂，而是整理过的证据包：

- 标题
- 来源平台
- 原文摘要
- 奖励相关片段
- 动作相关片段
- 时间相关片段
- 外链摘要
- 抓取元数据
- 第一层召回原因
- 调查回路中新增的证据

输出必须严格结构化，至少包含：

- 是否属于目标机会
- 活动类型
- 奖励类型
- 奖励描述
- 用户需要执行的动作
- 参与资格
- 时间信息
- 证据充分度
- 五级分类
- 理由摘要
- 缺失证据
- 风险标记
- 是否建议继续调查
- 如果继续调查，建议下一步调查动作

### 4.7 结果消费层

第一阶段不做复杂工作台。

结果消费层只负责：

- 浏览结构化机会库
- 查看详情和证据
- 查看来源与任务状态
- 观察系统运行概况

## 5. 五级分类定义

### 5.1 高价值

满足以下大部分条件：

- 奖励明确
- 动作明确
- 用户可参与
- 原文证据充分
- 时效有效
- 限制合理
- 对普通用户有明显价值

### 5.2 可跟

是有效机会，但优先级一般：

- 奖励存在
- 动作存在
- 能参与
- 但奖励一般、门槛偏高、吸引力一般或信息略零散

### 5.3 待补证据

很像奖励活动，但缺关键证据。

典型情况：

- 提到有奖励，但未写清奖励细则
- 说有任务，但未写清参与动作
- 社交流线索不完整，需要补抓外链
- 时间 / 资格 / 限制条件不明

这是一种正式结果，不是失败状态。

### 5.4 低价值

内容属于活动，但价值较低：

- 奖励很小
- 门槛很高
- 限制很强
- 覆盖面很窄
- 不值得重点消费

### 5.5 拒绝

明确不属于目标机会，或已不具备保留价值：

- 纯资讯
- 转述
- 讨论帖
- 营销文
- 无明确奖励
- 无明确动作
- 已过期
- 非用户可参与

## 6. 数据模型

第一阶段主数据对象不再围绕 legacy `activities` 语义扩展，而是围绕“奖励活动机会识别链 + Agent 调查回路”重建。

建议核心实体：

1. `source_feeds`
2. `crawl_jobs`
3. `raw_documents`
4. `recall_candidates`
5. `reward_opportunities`
6. `opportunity_evidence`
7. `evaluation_runs`
8. `investigation_runs`
9. `investigation_actions`

### 6.1 reward_opportunities 核心字段

- `id`
- `title`
- `normalized_title`
- `source_platform`
- `source_type`
- `source_url`
- `canonical_url`
- `published_at`
- `discovered_at`
- `content_language`
- `raw_text_excerpt`
- `opportunity_type`
- `reward_type`
- `reward_value_text`
- `action_required`
- `eligibility`
- `deadline_text`
- `deadline_at`
- `region_limit`
- `platform_limit`
- `ai_stage_1_recall_reason`
- `ai_stage_2_label`
- `ai_confidence`
- `ai_summary`
- `ai_reasoning_brief`
- `ai_missing_evidence`
- `ai_risk_flags`
- `ai_structured_evidence`
- `status`
- `dedupe_key`
- `content_hash`
- `last_evaluated_at`
- `recheck_after`

### 6.2 证据表

每条机会至少允许挂多条证据，证据类型包括：

- 原文标题
- 奖励证据片段
- 动作证据片段
- 时间证据片段
- 资格证据片段
- 原始 URL
- 抓取时间

目标是让每个结果可复核、可回溯。

### 6.3 调查运行记录

为了让系统真的是 Agent，而不是黑盒分类器，需要记录调查过程。

建议新增：

- `investigation_runs`
  - 对应一次候选调查流程
- `investigation_actions`
  - 对应每次自主动作

动作类型例如：

- 搜索新查询
- 打开链接
- 抓取详情页
- 抓取 FAQ
- 抓取规则页
- 抓取外链
- 停止调查

这样系统后续才能回答：

- Agent 为什么继续追
- Agent 追了哪些页
- Agent 为什么停
- 哪些调查动作最有效

## 7. 页面与信息架构

第一阶段主产品只保留 4 类界面：

### 7.1 系统概览

展示：

- 今日抓取量
- 今日候选召回量
- 今日深筛通过量
- 五级分类分布
- 来源健康状态
- 最近失败任务
- 最近新增高价值机会

### 7.2 机会库

这是主页面。

支持：

- 五级分类筛选
- 来源筛选
- 活动类型筛选
- 奖励类型筛选
- 时间筛选
- 证据充分度筛选
- 按抓取时间 / 发布时间 / 深筛时间排序

### 7.3 机会详情

详情页重点展示：

- 基本信息
- AI 分类结果
- 奖励与动作结构化字段
- 证据片段
- 原始内容摘要
- 外链补抓结果
- 风险标记
- 缺失证据

### 7.4 来源与任务

展示：

- 来源列表
- 最近抓取时间
- 最近成功 / 失败状态
- 抓取量
- 候选召回量
- 深筛通过量
- 失败日志
- 手动重跑入口

## 8. 对当前仓库的改造策略

### 8.1 保留并继续使用

- `scrapers/`
- `scheduler.py`
- 来源管理能力
- 基础 API 框架
- 基础前端壳和通用组件

### 8.2 降级为 legacy

- `data_manager.py`
- `app/backend/data_manager_components/*`
- `app/backend/opportunity_domain/`
- `WorkspacePage`
- `TrackingPage`
- `DigestsPage`
- 旧机会工作台叙事

这些模块可继续运行，但不再作为新主产品的中心。

### 8.3 新系统应新长的主骨架

后端新增：

- 奖励活动专用 repository / service
- 抓取任务持久化
- 原始文档存储
- 候选召回存储
- Agent 调查运行存储
- Agent 调查动作存储
- AI 深筛结果存储
- 证据存储

前端新增：

- 系统概览页
- 机会库页
- 机会详情页
- 来源与任务页

## 9. 迁移策略

采用双轨迁移，不做一次性硬切。

### 阶段一：并存

- 保留旧机会系统
- 新奖励活动系统单独生长
- 新系统不再依赖 tracking / digest / workspace 主链继续扩展

### 阶段二：切主导航

- 将首页主入口切到新系统
- 旧机会系统进入 legacy 区
- 再决定是否删除旧功能

## 10. 开源参考方向

以下开源项目不是可直接照搬的完整产品，但能为技术方案提供清晰参考。

### 10.1 抓取 / 抽取底座

- Crawl4AI
  - 不是只做参考，而是推荐直接作为网页抓取与抽取底座
  - 可直接承接：异步网页抓取、Markdown 清洗、deep crawl、structured extraction、LLM extraction
  - 参考：<https://github.com/unclecode/crawl4ai>
  - 官方文档：
    - <https://docs.crawl4ai.com/>
    - <https://docs.crawl4ai.com/core/quickstart/>
    - <https://docs.crawl4ai.com/core/deep-crawling/>
    - <https://docs.crawl4ai.com/extraction/llm-strategies/>

- Firecrawl
  - 适合借鉴：搜索 + 导航 + 网页抽取 + Agent 化网页访问
  - 参考：<https://github.com/firecrawl/firecrawl>

- Maxun
  - 适合借鉴：站点级结构化抽取与轻运营后台思路
  - 参考：<https://github.com/getmaxun/maxun>

### 10.2 浏览器代理能力

- browser-use
  - 适合借鉴：让 AI Agent 真正操作网页、点击、翻页、展开动态内容
  - 参考：<https://github.com/browser-use/browser-use>

### 10.3 深度研究 / 多步检索 Agent

- GPT Researcher
  - 适合借鉴：planner、execution agents、crawler agent、source tracking
  - 参考：<https://github.com/assafelovic/gpt-researcher>

- LangChain Open Deep Research
  - 适合借鉴：open deep research agent 的工作流和 search integration
  - 参考：<https://github.com/langchain-ai/open_deep_research>

- Tactara Deep Research Agent
  - 适合借鉴：Research Agent + Elaboration Agent 的双 Agent 结构
  - 参考：<https://github.com/Tactara/deep-research-agent>

### 10.4 搜索 Agent 思路

- OpenDeepSearch
  - 适合借鉴：deep search、semantic rerank、从“搜标题”升级到“搜后阅读”
  - 参考：<https://github.com/sentient-agi/OpenDeepSearch>

- OpenSeeker
  - 适合借鉴：搜索 Agent 的多步决策思想
  - 参考：<https://github.com/PolarSeeker/OpenSeeker>

这些项目共同说明了一件事：

你要做的系统，技术上更接近“agentic search + web investigation + evidence-based evaluation”，而不是传统爬虫平台。

其中最重要的技术决策是：

**直接采用 Crawl4AI 作为 Collector Agent 底座，而不是从零实现网页抓取框架。**

## 11. 成功标准

这个系统第一阶段成功，不看页面数量，看这几个结果：

1. 每天能稳定抓到新的原始内容
2. 宽松召回不会严重漏掉目标活动
3. `高价值 + 可跟` 结果准确率足够高
4. `待补证据` 能有效承接社交流和不完整线索
5. 每条结果都能回溯到原始证据
6. 你可以直接消费结构化机会，而不是重新读大量原始帖子
7. 在证据不足时，Agent 能自主追证据，而不是只能单轮分类
8. 调查动作可记录、可解释、可评估

## 12. 风险与控制

### 风险 1：再次回到“泛机会平台”

控制：

- 不新增 tracking / digest / 工作台执行流能力
- 所有新增需求先问是否直接服务“自动发现奖励活动”

### 风险 2：抓取量很大但结果价值低

控制：

- 维持宽松召回，但把深筛做重
- 强制证据化输出
- 对来源建立产出质量指标

### 风险 3：社交流噪音拖垮系统

控制：

- 社交流默认当线索
- 未补到关键证据前，不直接进入高价值主流

### 风险 4：Agent 调查回路失控

控制：

- 每次调查限制轮数
- 限制每轮新增链接数
- 限制调查总时长
- 限制单候选 token / 成本预算

### 风险 5：继续复用 legacy `activities` 语义导致模型混乱

控制：

- 新系统主数据对象单独建模
- 不继续把“奖励活动机会”强塞进旧机会域语义

## 13. 结论

当前项目最合理的下一步，不是继续完善“复杂机会工作台”，而是明确收缩成：

**全网奖励活动自动发现 + Agent 自主追证据 + AI 深筛 + 结构化机会库**

这是与你当前真实目标最一致、工程边界最清楚、产品叙事最干净的方向。

在实现层面，这条路线进一步具体化为：

**Crawl4AI 负责网页获取与抽取，你的业务 Agent 负责召回、调查、评估、合并与沉淀。**
