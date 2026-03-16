# Requirements Document

## Introduction

VigilAI前端是开发者搞钱机会监控系统的Web界面，提供活动浏览、筛选、搜索、信息源管理等功能。前端通过调用后端REST API获取数据，为用户提供直观、高效的信息展示和交互体验。

## Glossary

- Activity: 活动实体，代表一个黑客松、竞赛、空投等机会
- Source: 信息源，代表一个数据来源平台（如Devpost、DoraHacks等）
- Category: 活动类别，包括hackathon、competition、airdrop、bounty、grant、event
- API: 后端REST接口服务，运行在http://localhost:8000
- Dashboard: 仪表盘，展示统计信息和概览
- Pagination: 分页，用于处理大量数据的分批展示

## Backend API Reference

前端需要调用以下后端API端点：

- GET /api/activities - 获取活动列表（支持分页、筛选、排序、搜索）
- GET /api/activities/{id} - 获取活动详情
- GET /api/sources - 获取所有信息源状态
- POST /api/sources/{id}/refresh - 手动刷新指定信息源
- POST /api/sources/refresh-all - 刷新所有信息源
- GET /api/stats - 获取统计信息
- GET /api/categories - 获取所有活动类别
- GET /api/health - 健康检查

## Requirements

### Requirement 1: 项目初始化与配置

User Story: As a 开发者, I want 前端项目有清晰的结构和配置, so that 代码易于维护和扩展。

#### Acceptance Criteria

1. THE Frontend SHALL use React 18 with TypeScript as the core framework
2. THE Frontend SHALL use Vite as the build tool for fast development experience
3. THE Frontend SHALL use TailwindCSS for styling
4. THE Frontend SHALL define TypeScript interfaces matching backend data models (Activity, Source, Category, etc.)
5. THE Frontend SHALL configure API base URL as environment variable with default http://localhost:8000

### Requirement 2: API服务层

User Story: As a 前端开发者, I want 有统一的API调用封装, so that 可以方便地与后端交互。

#### Acceptance Criteria

1. THE API_Service SHALL provide methods for all backend endpoints
2. THE API_Service SHALL handle HTTP errors and return appropriate error messages
3. WHEN an API call fails THEN THE API_Service SHALL throw an error with status code and message
4. THE API_Service SHALL use fetch or axios for HTTP requests
5. THE API_Service SHALL support request cancellation for component unmount scenarios

### Requirement 3: 活动列表页面

User Story: As a 用户, I want 浏览所有活动列表, so that 我能发现感兴趣的机会。

#### Acceptance Criteria

1. THE Activity_List_Page SHALL display activities in a card or table layout
2. WHEN the page loads THEN THE System SHALL fetch activities from GET /api/activities
3. THE Activity_Card SHALL display title, source_name, category, prize (if available), and deadline (if available)
4. THE Activity_List_Page SHALL support pagination with page size of 20 items
5. WHEN user clicks an activity card THEN THE System SHALL navigate to the activity detail page
6. THE Activity_List_Page SHALL show loading state while fetching data
7. IF no activities are found THEN THE System SHALL display an empty state message

### Requirement 4: 活动筛选功能

User Story: As a 用户, I want 按类别和信息源筛选活动, so that 我能快速找到特定类型的机会。

#### Acceptance Criteria

1. THE Filter_Component SHALL provide category filter dropdown with options: hackathon, competition, airdrop, bounty, grant, event
2. THE Filter_Component SHALL provide source filter dropdown populated from GET /api/sources
3. WHEN user selects a filter THEN THE System SHALL update the activity list with filtered results
4. THE Filter_Component SHALL support clearing all filters
5. WHEN filters are applied THEN THE URL SHALL reflect the current filter state for bookmarking

### Requirement 5: 活动搜索功能

User Story: As a 用户, I want 搜索活动标题和描述, so that 我能快速找到特定的活动。

#### Acceptance Criteria

1. THE Search_Component SHALL provide a text input for keyword search
2. WHEN user types in the search box THEN THE System SHALL debounce input for 300ms before making API call
3. WHEN user submits search THEN THE System SHALL call GET /api/activities with search parameter
4. THE Search_Component SHALL display the current search term
5. THE Search_Component SHALL provide a clear button to reset search

### Requirement 6: 活动排序功能

User Story: As a 用户, I want 按不同字段排序活动, so that 我能按优先级查看机会。

#### Acceptance Criteria

1. THE Sort_Component SHALL support sorting by: created_at (最新), deadline (截止日期), prize (奖金)
2. THE Sort_Component SHALL support ascending and descending order
3. WHEN user changes sort option THEN THE System SHALL update the activity list with sorted results
4. THE Default sort SHALL be created_at in descending order (最新优先)

### Requirement 7: 活动详情页面

User Story: As a 用户, I want 查看活动的完整信息, so that 我能决定是否参与。

#### Acceptance Criteria

1. THE Activity_Detail_Page SHALL fetch activity data from GET /api/activities/{id}
2. THE Activity_Detail_Page SHALL display all activity fields: title, description, source, category, tags, prize, dates, location, organizer
3. THE Activity_Detail_Page SHALL provide a link to the original activity URL
4. THE Activity_Detail_Page SHALL display formatted dates in user-friendly format
5. IF activity has prize information THEN THE System SHALL display amount and currency
6. THE Activity_Detail_Page SHALL provide a back button to return to the list
7. IF activity is not found THEN THE System SHALL display a 404 error page

### Requirement 8: 信息源管理页面

User Story: As a 用户, I want 查看和管理信息源状态, so that 我能了解数据采集情况。

#### Acceptance Criteria

1. THE Sources_Page SHALL fetch source data from GET /api/sources
2. THE Sources_Page SHALL display each source with: name, type, status, last_run, activity_count
3. THE Source_Card SHALL show status indicator (idle, running, success, error) with appropriate colors
4. WHEN user clicks refresh button on a source THEN THE System SHALL call POST /api/sources/{id}/refresh
5. THE Sources_Page SHALL provide a "Refresh All" button that calls POST /api/sources/refresh-all
6. WHEN a refresh is triggered THEN THE System SHALL show loading state and update status after completion
7. IF a source has error_message THEN THE System SHALL display the error information

### Requirement 9: 仪表盘/统计页面

User Story: As a 用户, I want 查看活动统计概览, so that 我能了解当前机会的整体情况。

#### Acceptance Criteria

1. THE Dashboard_Page SHALL fetch statistics from GET /api/stats
2. THE Dashboard_Page SHALL display total_activities count
3. THE Dashboard_Page SHALL display total_sources count
4. THE Dashboard_Page SHALL display activities_by_category as a chart or list
5. THE Dashboard_Page SHALL display activities_by_source as a chart or list
6. THE Dashboard_Page SHALL display last_update timestamp
7. THE Dashboard_Page SHALL auto-refresh statistics every 60 seconds

### Requirement 10: 导航与布局

User Story: As a 用户, I want 清晰的导航结构, so that 我能方便地访问各个功能。

#### Acceptance Criteria

1. THE Layout SHALL include a header with application title "VigilAI"
2. THE Navigation SHALL include links to: 活动列表, 信息源管理, 仪表盘
3. THE Layout SHALL be responsive and work on desktop and mobile devices
4. THE Navigation SHALL highlight the current active page
5. THE Layout SHALL include a footer with version information

### Requirement 11: 错误处理与用户反馈

User Story: As a 用户, I want 清晰的错误提示和操作反馈, so that 我知道系统的状态。

#### Acceptance Criteria

1. WHEN an API call fails THEN THE System SHALL display an error toast or message
2. WHEN a refresh operation succeeds THEN THE System SHALL display a success notification
3. THE Error_Component SHALL display user-friendly error messages
4. IF the backend is unavailable THEN THE System SHALL display a connection error message
5. THE System SHALL provide retry options for failed operations

### Requirement 12: 状态管理

User Story: As a 前端开发者, I want 合理的状态管理方案, so that 组件间数据共享高效。

#### Acceptance Criteria

1. THE Frontend SHALL use React hooks (useState, useEffect) for local component state
2. THE Frontend MAY use React Context or Zustand for global state if needed
3. THE Frontend SHALL implement loading states for all async operations
4. THE Frontend SHALL cache API responses appropriately to reduce unnecessary requests

### Requirement 13: 类型安全

User Story: As a 前端开发者, I want 完整的TypeScript类型定义, so that 代码更健壮且易于维护。

#### Acceptance Criteria

1. THE Frontend SHALL define interfaces for all API response types
2. THE Activity interface SHALL match backend Activity model fields
3. THE Source interface SHALL match backend Source model fields
4. THE Frontend SHALL use strict TypeScript configuration
5. THE Frontend SHALL have no TypeScript errors in production build
