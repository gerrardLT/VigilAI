# Requirements Document: VigilAI信息源扩展

## Introduction

VigilAI系统当前仅实现了6个信息源（Devpost、DoraHacks、Gitcoin、36氪、虎嗅、Kaggle），但用户文档中列出了100+个高价值信息源。本需求文档定义了扩展系统以支持所有这些信息源的功能需求，包括空投聚合、数据竞赛、黑客松聚合、漏洞赏金、企业开发者平台、政府竞赛、设计竞赛和编程竞赛等多个类别的爬虫实现。

## Glossary

- **Scraper**: 爬虫，用于从特定信息源抓取数据的组件
- **BaseScraper**: 爬虫基类，定义了所有爬虫的通用接口和行为
- **Dynamic_Web_Scraper**: 动态网页爬虫，使用Selenium或Playwright处理JavaScript渲染的页面
- **Anti_Scraping_Strategy**: 反爬虫策略，包括代理池、User-Agent轮换等技术
- **Scheduler**: 调度器，负责按优先级和频率调度爬虫任务
- **Activity**: 活动，从信息源抓取的机会信息（黑客松、竞赛、空投等）
- **Source_Config**: 信息源配置，定义信息源的URL、类型、优先级等参数
- **Proxy_Pool**: 代理池，用于轮换IP地址以避免被封禁
- **Error_Handler**: 错误处理器，负责捕获和记录爬虫运行时错误

## Requirements

### Requirement 1: 空投聚合爬虫实现

**User Story:** 作为系统管理员，我希望系统能够从多个空投聚合平台抓取空投信息，以便用户能够及时发现加密货币空投机会。

#### Acceptance Criteria

1. WHEN Airdrops.io爬虫运行时，THE Airdrop_Scraper SHALL抓取所有活跃空投的标题、描述、截止日期和奖励信息
2. WHEN CoinMarketCap空投页面爬虫运行时，THE Airdrop_Scraper SHALL使用动态网页爬取技术获取JavaScript渲染的内容
3. WHEN Galxe平台爬虫运行时，THE Airdrop_Scraper SHALL抓取任务型空投的详细要求和奖励代币信息
4. WHEN DeFiLlama空投页面爬虫运行时，THE Airdrop_Scraper SHALL提取项目名称、预计空投时间和参与条件
5. WHEN Zealy平台爬虫运行时，THE Airdrop_Scraper SHALL抓取社区任务和积分奖励信息
6. WHEN任何空投爬虫遇到反爬虫机制时，THE Anti_Scraping_Strategy SHALL自动切换代理IP和User-Agent

### Requirement 2: 数据竞赛爬虫实现

**User Story:** 作为数据科学家，我希望系统能够从多个数据竞赛平台抓取竞赛信息，以便我能够参与各种数据科学挑战。

#### Acceptance Criteria

1. WHEN天池平台爬虫运行时，THE Data_Competition_Scraper SHALL抓取竞赛标题、奖金、截止日期和参赛要求
2. WHEN DataFountain爬虫运行时，THE Data_Competition_Scraper SHALL处理中文内容并正确解析竞赛详情
3. WHEN DataCastle爬虫运行时，THE Data_Competition_Scraper SHALL提取竞赛类型（算法、数据分析等）和难度等级
4. WHEN DrivenData爬虫运行时，THE Data_Competition_Scraper SHALL抓取社会公益类数据竞赛的影响力指标
5. WHEN任何数据竞赛平台需要登录时，THE Data_Competition_Scraper SHALL仅抓取公开可访问的竞赛信息

### Requirement 3: 黑客松聚合爬虫实现

**User Story:** 作为开发者，我希望系统能够从黑客松聚合平台抓取全球黑客松活动，以便我能够参与各种技术创新活动。

#### Acceptance Criteria

1. WHEN MLH平台爬虫运行时，THE Hackathon_Aggregator_Scraper SHALL抓取所有即将举行的黑客松活动信息
2. WHEN Hackathon.com爬虫运行时，THE Hackathon_Aggregator_Scraper SHALL提取活动的地点（线上/线下）、时间和主题
3. WHEN黑客松聚合爬虫解析活动详情时，THE Hackathon_Aggregator_Scraper SHALL识别并提取奖金、赞助商和技术栈信息
4. WHEN黑客松活动已结束时，THE Hackathon_Aggregator_Scraper SHALL过滤掉已过期的活动

### Requirement 4: 漏洞赏金爬虫实现

**User Story:** 作为安全研究员，我希望系统能够从多个漏洞赏金平台抓取赏金项目，以便我能够参与安全漏洞挖掘并获得奖励。

#### Acceptance Criteria

1. WHEN HackerOne爬虫运行时，THE Bounty_Scraper SHALL抓取公开赏金项目的范围、奖金范围和响应时间
2. WHEN Bugcrowd爬虫运行时，THE Bounty_Scraper SHALL提取项目的严重性等级和支付条件
3. WHEN Code4rena爬虫运行时，THE Bounty_Scraper SHALL抓取智能合约审计竞赛的奖池和时间线
4. WHEN IssueHunt爬虫运行时，THE Bounty_Scraper SHALL提取开源项目的Issue赏金金额和技术要求
5. WHEN Bountysource爬虫运行时，THE Bounty_Scraper SHALL抓取众筹赏金的当前金额和支持者数量
6. WHEN漏洞赏金平台需要认证时，THE Bounty_Scraper SHALL仅抓取公开可见的项目信息

### Requirement 5: 企业开发者平台爬虫实现

**User Story:** 作为企业开发者，我希望系统能够从主流企业开发者平台抓取竞赛和挑战信息，以便我能够参与企业技术生态建设。

#### Acceptance Criteria

1. WHEN华为开发者平台爬虫运行时，THE Enterprise_Scraper SHALL抓取开发者大赛、创新挑战和技术沙龙信息
2. WHEN Google开发者平台爬虫运行时，THE Enterprise_Scraper SHALL提取Google Cloud、Android等生态的竞赛信息
3. WHEN AWS开发者平台爬虫运行时，THE Enterprise_Scraper SHALL抓取AWS Hackathon和创新挑战的详细信息
4. WHEN Microsoft开发者平台爬虫运行时，THE Enterprise_Scraper SHALL提取Azure、GitHub等平台的开发者活动
5. WHEN企业平台使用API时，THE Enterprise_Scraper SHALL优先使用官方API而非网页爬取

### Requirement 6: 政府竞赛爬虫实现

**User Story:** 作为创业者，我希望系统能够从政府竞赛平台抓取官方竞赛信息，以便我能够参与政府支持的创新创业项目。

#### Acceptance Criteria

1. WHEN Challenge.gov爬虫运行时，THE Government_Scraper SHALL抓取美国联邦政府发布的所有公开挑战
2. WHEN中国创新创业大赛爬虫运行时，THE Government_Scraper SHALL处理中文内容并提取赛事阶段、奖金和报名要求
3. WHEN创客中国平台爬虫运行时，THE Government_Scraper SHALL抓取工信部主办的创新创业竞赛信息
4. WHEN政府平台更新频率较低时，THE Scheduler SHALL将这些爬虫设置为低优先级（每6小时）

### Requirement 7: 设计竞赛爬虫实现

**User Story:** 作为设计师，我希望系统能够从设计竞赛平台抓取竞赛信息，以便我能够参与各种设计挑战并展示作品。

#### Acceptance Criteria

1. WHEN设计竞赛网爬虫运行时，THE Design_Competition_Scraper SHALL抓取竞赛类型（UI/UX、平面、工业设计等）和奖金
2. WHEN设计竞赛爬虫解析详情时，THE Design_Competition_Scraper SHALL提取作品提交格式、评审标准和截止日期
3. WHEN设计竞赛包含多个阶段时，THE Design_Competition_Scraper SHALL记录每个阶段的时间节点

### Requirement 8: 编程竞赛爬虫实现

**User Story:** 作为算法工程师，我希望系统能够从编程竞赛平台抓取竞赛信息，以便我能够参与算法挑战并提升技能。

#### Acceptance Criteria

1. WHEN HackerEarth爬虫运行时，THE Coding_Competition_Scraper SHALL抓取编程挑战的难度、时长和奖励
2. WHEN TopCoder爬虫运行时，THE Coding_Competition_Scraper SHALL提取SRM（Single Round Match）和Marathon赛事信息
3. WHEN编程竞赛爬虫处理实时竞赛时，THE Coding_Competition_Scraper SHALL标记正在进行的竞赛状态

### Requirement 9: Web3平台爬虫优化

**User Story:** 作为系统维护者，我希望优化现有Web3平台爬虫的性能和可靠性，以便提高数据抓取的成功率和准确性。

#### Acceptance Criteria

1. WHEN DoraHacks爬虫运行时，THE Web3_Scraper SHALL使用改进的选择器以适应页面结构变化
2. WHEN Gitcoin爬虫运行时，THE Web3_Scraper SHALL处理GraphQL API响应并提取Grant信息
3. WHEN ETHGlobal爬虫运行时，THE Web3_Scraper SHALL抓取黑客松的赞助商、赛道和评审标准
4. WHEN Immunefi爬虫运行时，THE Web3_Scraper SHALL提取漏洞赏金的最高奖金和项目类型（DeFi、NFT等）

### Requirement 10: 爬虫架构继承

**User Story:** 作为开发者，我希望所有新爬虫都继承BaseScraper架构，以便保持代码一致性和可维护性。

#### Acceptance Criteria

1. WHEN创建新爬虫类时，THE Scraper SHALL继承BaseScraper并实现scrape方法
2. WHEN爬虫初始化时，THE Scraper SHALL接收Source_Config参数并设置基本属性
3. WHEN爬虫执行抓取时，THE Scraper SHALL返回标准化的Activity对象列表
4. WHEN爬虫需要动态网页支持时，THE Scraper SHALL使用Selenium或Playwright库
5. THE BaseScraper SHALL定义统一的错误处理和日志记录接口

### Requirement 11: 反爬虫策略实现

**User Story:** 作为系统管理员，我希望系统实现反爬虫策略，以便避免IP被封禁并提高爬取成功率。

#### Acceptance Criteria

1. WHEN爬虫发起请求时，THE Anti_Scraping_Strategy SHALL从代理池中随机选择代理IP
2. WHEN爬虫设置请求头时，THE Anti_Scraping_Strategy SHALL从预定义列表中轮换User-Agent
3. WHEN爬虫连续请求时，THE Anti_Scraping_Strategy SHALL在请求之间添加随机延迟（1-3秒）
4. WHEN代理IP失败时，THE Anti_Scraping_Strategy SHALL自动切换到下一个可用代理
5. WHEN检测到验证码或封禁时，THE Anti_Scraping_Strategy SHALL记录错误并暂停该爬虫30分钟

### Requirement 12: 错误处理和日志记录

**User Story:** 作为系统维护者，我希望所有爬虫都有完善的错误处理和日志记录，以便快速定位和解决问题。

#### Acceptance Criteria

1. WHEN爬虫遇到网络错误时，THE Error_Handler SHALL捕获异常并记录详细错误信息
2. WHEN爬虫解析失败时，THE Error_Handler SHALL记录失败的URL和HTML片段
3. WHEN爬虫成功抓取数据时，THE Scraper SHALL记录抓取的活动数量和耗时
4. WHEN爬虫运行时，THE Scraper SHALL使用Python logging模块记录INFO、WARNING和ERROR级别日志
5. IF爬虫连续失败3次，THEN THE Scheduler SHALL发送告警通知

### Requirement 13: 调度器更新

**User Story:** 作为系统管理员，我希望调度器能够支持新的爬虫类型映射，以便正确调度所有信息源的爬取任务。

#### Acceptance Criteria

1. WHEN Scheduler初始化时，THE Scheduler SHALL加载所有爬虫类型到类映射关系
2. WHEN Scheduler创建爬虫实例时，THE Scheduler SHALL根据Source_Config的类型选择正确的爬虫类
3. WHEN Scheduler调度任务时，THE Scheduler SHALL按照优先级（高/中/低）和频率执行爬虫
4. WHEN新增爬虫类型时，THE Scheduler SHALL支持动态注册新的爬虫类映射
5. THE Scheduler SHALL为每个信息源维护独立的调度状态和错误计数

### Requirement 14: 数据标准化

**User Story:** 作为数据消费者，我希望所有爬虫返回标准化的数据格式，以便统一处理和存储活动信息。

#### Acceptance Criteria

1. WHEN爬虫返回活动数据时，THE Scraper SHALL将数据转换为Activity模型对象
2. WHEN Activity对象创建时，THE Scraper SHALL确保必填字段（title、source、url、deadline）不为空
3. WHEN解析日期时间时，THE Scraper SHALL将所有日期转换为ISO 8601格式
4. WHEN提取奖金信息时，THE Scraper SHALL标准化货币单位（USD、CNY、ETH等）
5. WHEN活动类型不明确时，THE Scraper SHALL根据信息源自动推断类型（hackathon、competition、bounty、airdrop）

### Requirement 15: 测试覆盖

**User Story:** 作为质量保证工程师，我希望所有爬虫都有完整的测试覆盖，以便确保代码质量和功能正确性。

#### Acceptance Criteria

1. WHEN编写新爬虫时，THE Developer SHALL为每个爬虫类编写单元测试
2. WHEN测试爬虫时，THE Test SHALL使用mock数据模拟HTTP响应
3. WHEN测试反爬虫策略时，THE Test SHALL验证代理轮换和User-Agent随机化
4. WHEN测试错误处理时，THE Test SHALL模拟网络错误、解析错误和超时场景
5. THE Test_Suite SHALL包含属性测试以验证数据标准化的正确性

## Notes

- 所有爬虫必须遵守目标网站的robots.txt规则
- 动态网页爬取应优先使用Playwright（性能更好）而非Selenium
- 代理池配置应支持免费代理和付费代理两种模式
- 日志文件应按日期轮转，保留最近30天的日志
- 所有时间相关字段应使用UTC时区
