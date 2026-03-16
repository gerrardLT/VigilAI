# Requirements Document

## Introduction

VigilAI是一个面向开发者的搞钱机会自动化监控系统，实时追踪全球范围内的黑客松、编程竞赛、Web3空投、漏洞赏金、开源悬赏、创业资助等变现机会。系统通过多源数据采集、智能去重、自动分类等功能，帮助用户比别人更早发现高价值机会。

## Glossary

- Scraper: 数据采集器，负责从各信息源抓取活动数据
- Activity: 活动实体，代表一个黑客松、竞赛、空投等机会
- Source: 信息源，代表一个数据来源平台（如Devpost、DoraHacks等）
- DataManager: 数据管理器，负责数据存储、去重、查询
- Scheduler: 调度器，负责定时触发数据采集任务
- API: 后端REST接口服务
- RSS: Really Simple Syndication，一种信息订阅格式

## Requirements

### Requirement 1: 数据模型定义

User Story: As a 开发者, I want 系统有清晰的数据模型定义, so that 数据结构统一且易于扩展。

#### Acceptance Criteria

1. THE Activity_Model SHALL include fields: id, title, description, source_id, source_name, url, category, tags, prize, dates, location, organizer, status, created_at, updated_at
2. THE Source_Model SHALL include fields: id, name, type, url, priority, update_interval, enabled, last_run, last_success, status, error_message, activity_count
3. WHEN creating an Activity THEN THE System SHALL generate a unique id based on source_id and original url
4. THE Category field SHALL support values: hackathon, competition, airdrop, bounty, grant, event
5. THE Priority field SHALL support values: high, medium, low

### Requirement 2: 配置管理

User Story: As a 系统管理员, I want 集中管理所有信息源配置, so that 可以方便地添加、修改、启用或禁用信息源。

#### Acceptance Criteria

1. THE Config_Module SHALL define all source configurations in a centralized location
2. WHEN a source is disabled THEN THE Scheduler SHALL skip its data collection tasks
3. THE Config_Module SHALL support different update intervals for each priority level: high (3600s), medium (7200s), low (21600s)
4. THE Config_Module SHALL include API host and port settings with defaults: host=0.0.0.0, port=8000

### Requirement 3: RSS数据采集

User Story: As a 用户, I want 系统自动采集RSS订阅源的活动信息, so that 我能获取Devpost、36氪、虎嗅等平台的最新活动。

#### Acceptance Criteria

1. WHEN the RSS_Scraper receives a valid RSS feed URL THEN THE System SHALL parse all entries and extract activity information
2. THE RSS_Scraper SHALL extract title, description, link, published_date from each RSS entry
3. IF the RSS feed is unavailable or malformed THEN THE RSS_Scraper SHALL log the error and return an empty list without crashing
4. THE RSS_Scraper SHALL support both RSS 2.0 and Atom feed formats
5. WHEN parsing RSS entries THEN THE RSS_Scraper SHALL convert all dates to ISO 8601 format

### Requirement 4: 网页数据采集

User Story: As a 用户, I want 系统能爬取动态网页上的活动信息, so that 我能获取DoraHacks、Gitcoin等平台的最新活动。

#### Acceptance Criteria

1. THE Web_Scraper SHALL provide a base class with common scraping utilities
2. WHEN scraping a webpage THEN THE Web_Scraper SHALL use appropriate User-Agent headers to avoid blocking
3. THE Web_Scraper SHALL implement request rate limiting with configurable delays between requests
4. IF a webpage request fails THEN THE Web_Scraper SHALL retry up to 3 times with exponential backoff
5. THE Web_Scraper SHALL support both static HTML parsing and dynamic JavaScript rendering

### Requirement 5: Web3平台数据采集

User Story: As a Web3开发者, I want 系统监控Web3相关平台, so that 我能及时发现空投、黑客松和Grant机会。

#### Acceptance Criteria

1. THE Web3_Scraper SHALL support scraping DoraHacks hackathon listings
2. THE Web3_Scraper SHALL support scraping Gitcoin grants information
3. THE Web3_Scraper SHALL extract prize information including amount and currency (USD, ETH, etc.)
4. WHEN scraping Web3 platforms THEN THE System SHALL categorize activities as hackathon, airdrop, bounty, or grant

### Requirement 6: Kaggle竞赛数据采集

User Story: As a 数据科学家, I want 系统监控Kaggle竞赛, so that 我能及时参与高奖金的数据科学比赛。

#### Acceptance Criteria

1. THE Kaggle_Scraper SHALL use the official Kaggle API to fetch competition listings
2. THE Kaggle_Scraper SHALL extract competition title, description, deadline, prize, and category
3. IF Kaggle API credentials are not configured THEN THE Kaggle_Scraper SHALL log a warning and skip Kaggle data collection
4. THE Kaggle_Scraper SHALL filter competitions by status to only include active and upcoming ones

### Requirement 7: 科技媒体数据采集

User Story: As a 创业者, I want 系统监控科技媒体的活动信息, so that 我能了解行业峰会和创业活动。

#### Acceptance Criteria

1. THE Tech_Media_Scraper SHALL support 36kr RSS feed parsing
2. THE Tech_Media_Scraper SHALL support Huxiu RSS feed parsing
3. WHEN parsing tech media content THEN THE System SHALL filter articles containing activity-related keywords
4. THE Tech_Media_Scraper SHALL extract event dates from article content when available

### Requirement 8: 数据存储与管理

User Story: As a 系统, I want 持久化存储所有采集的活动数据, so that 用户可以随时查询历史和最新活动。

#### Acceptance Criteria

1. THE DataManager SHALL store data in a SQLite database file (vigilai.db) in the data directory
2. THE DataManager SHALL create activities and sources tables on initialization
3. WHEN saving data THEN THE DataManager SHALL use database transactions to ensure data integrity
4. THE DataManager SHALL connect to existing database on startup and preserve existing data
5. WHEN storing an Activity THEN THE DataManager SHALL insert or update the record in the activities table
6. WHEN loading an Activity THEN THE DataManager SHALL query from the activities table and convert to Activity model

### Requirement 9: 数据去重

User Story: As a 用户, I want 系统自动去除重复的活动信息, so that 我不会看到同一个活动多次。

#### Acceptance Criteria

1. WHEN adding a new activity THEN THE DataManager SHALL check for duplicates based on url
2. IF a duplicate is found THEN THE DataManager SHALL update the existing record instead of creating a new one
3. THE DataManager SHALL maintain a unique constraint on the combination of source_id and original url
4. WHEN updating a duplicate THEN THE DataManager SHALL preserve the original created_at timestamp

### Requirement 10: 定时调度

User Story: As a 系统, I want 按照配置的时间间隔自动执行数据采集任务, so that 活动信息保持最新。

#### Acceptance Criteria

1. THE Scheduler SHALL use APScheduler to manage periodic tasks
2. WHEN the system starts THEN THE Scheduler SHALL register all enabled sources as scheduled jobs
3. THE Scheduler SHALL execute high priority sources every 1 hour
4. THE Scheduler SHALL execute medium priority sources every 2 hours
5. THE Scheduler SHALL execute low priority sources every 6 hours
6. WHEN a scheduled job fails THEN THE Scheduler SHALL log the error and continue with other jobs
7. THE Scheduler SHALL update source status after each job execution

### Requirement 11: REST API服务

User Story: As a 前端应用, I want 通过REST API获取活动数据, so that 可以展示给用户。

#### Acceptance Criteria

1. THE API SHALL provide GET /api/activities endpoint to list activities with pagination
2. THE API SHALL provide GET /api/activities/{id} endpoint to get activity details
3. THE API SHALL provide GET /api/sources endpoint to list all source statuses
4. THE API SHALL provide POST /api/sources/{id}/refresh endpoint to manually trigger a source refresh
5. THE API SHALL provide POST /api/sources/refresh-all endpoint to refresh all sources
6. THE API SHALL provide GET /api/stats endpoint to return activity statistics
7. WHEN listing activities THEN THE API SHALL support filtering by category, source_id, and status
8. WHEN listing activities THEN THE API SHALL support sorting by created_at, deadline, and prize amount
9. THE API SHALL enable CORS to allow frontend access from different origins

### Requirement 12: 系统启动与初始化

User Story: As a 运维人员, I want 系统能够正确启动并初始化所有组件, so that 服务可以稳定运行。

#### Acceptance Criteria

1. WHEN the system starts THEN THE Main_Module SHALL initialize DataManager, Scheduler, and API components in order
2. WHEN the system starts THEN THE Scheduler SHALL trigger an initial data collection for all enabled sources
3. THE Main_Module SHALL start the API server using uvicorn with configured host and port
4. IF any component fails to initialize THEN THE System SHALL log the error and exit gracefully
5. WHEN the system receives a shutdown signal THEN THE Scheduler SHALL stop all running jobs gracefully

### Requirement 13: 错误处理与日志

User Story: As a 运维人员, I want 系统有完善的错误处理和日志记录, so that 可以快速定位和解决问题。

#### Acceptance Criteria

1. THE System SHALL use Python logging module with configurable log levels
2. WHEN an error occurs during scraping THEN THE System SHALL log the error with source_id, url, and error message
3. THE System SHALL log the start and completion of each scheduled job
4. IF a critical error occurs THEN THE System SHALL continue running other components without crashing
5. THE System SHALL log API request information including method, path, and response status
