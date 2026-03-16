# Implementation Plan: VigilAI Frontend

## Overview

基于React 18 + TypeScript + Vite + TailwindCSS构建VigilAI前端应用，实现活动浏览、筛选、搜索和信息源管理功能。

## Tasks

- [x] 1. 项目初始化与配置
  - [x] 1.1 使用Vite创建React + TypeScript项目
    - 在app/frontend目录下初始化项目
    - 配置TypeScript严格模式
    - Requirements: 1.1, 1.2, 13.4
  - [x] 1.2 配置TailwindCSS
    - 安装tailwindcss、postcss、autoprefixer
    - 创建tailwind.config.js和postcss.config.js
    - Requirements: 1.3
  - [x] 1.3 配置环境变量
    - 创建.env文件配置API_URL
    - 配置vite.config.ts读取环境变量
    - Requirements: 1.5

- [x] 2. TypeScript类型定义
  - [x] 2.1 创建类型定义文件
    - 定义Activity、Source、Prize、ActivityDates等接口
    - 定义Category、Priority、SourceType、SourceStatus枚举类型
    - 定义API响应类型
    - Requirements: 1.4, 13.1, 13.2, 13.3
  - [x] 2.2 编写类型匹配属性测试
    - Property 1: TypeScript接口与后端模型字段匹配
    - Validates: Requirements 1.4, 13.2, 13.3

- [x] 3. API服务层
  - [x] 3.1 实现API服务类
    - 创建services/api.ts
    - 实现所有API方法：getActivities, getActivity, getSources, refreshSource, refreshAllSources, getStats, getCategories, healthCheck
    - 实现统一错误处理
    - Requirements: 2.1, 2.2, 2.3
  - [x] 3.2 编写API错误处理属性测试
    - Property 2: API错误处理一致性
    - Validates: Requirements 2.2, 2.3

- [x] 4. 工具函数
  - [x] 4.1 实现日期格式化工具
    - 创建utils/formatDate.ts
    - 将ISO 8601日期转换为用户友好格式
    - Requirements: 7.4
  - [x] 4.2 编写日期格式化属性测试
    - Property 7: 日期格式化一致性
    - Validates: Requirements 7.4
  - [x] 4.3 实现常量定义
    - 创建utils/constants.ts
    - 定义类别标签映射、状态颜色映射等

- [x] 5. 自定义Hooks
  - [x] 5.1 实现useDebounce Hook
    - 创建hooks/useDebounce.ts
    - 用于搜索输入防抖
    - Requirements: 5.2
  - [x] 5.2 实现useActivities Hook
    - 创建hooks/useActivities.ts
    - 封装活动列表数据获取和状态管理
    - Requirements: 3.2, 12.3
  - [x] 5.3 实现useSources Hook
    - 创建hooks/useSources.ts
    - 封装信息源数据获取和状态管理
    - Requirements: 8.1
  - [x] 5.4 实现useStats Hook
    - 创建hooks/useStats.ts
    - 封装统计数据获取和自动刷新
    - Requirements: 9.1, 9.7

- [x] 6. 基础UI组件
  - [x] 6.1 实现Loading组件
    - 创建components/Loading.tsx
    - 显示加载动画
    - Requirements: 3.6, 12.3
  - [x] 6.2 实现ErrorMessage组件
    - 创建components/ErrorMessage.tsx
    - 显示错误信息和重试按钮
    - Requirements: 11.3, 11.5
  - [x] 6.3 实现Toast组件
    - 创建components/Toast.tsx
    - 显示成功/错误通知
    - Requirements: 11.1, 11.2
  - [x] 6.4 编写加载状态属性测试
    - Property 10: 异步操作加载状态
    - Validates: Requirements 12.3

- [x] 7. 布局组件
  - [x] 7.1 实现Header组件
    - 创建components/Header.tsx
    - 包含应用标题和导航链接
    - Requirements: 10.1, 10.2, 10.4
  - [x] 7.2 实现Footer组件
    - 创建components/Footer.tsx
    - 显示版本信息
    - Requirements: 10.5
  - [x] 7.3 实现Layout组件
    - 创建components/Layout.tsx
    - 组合Header、主内容区、Footer
    - 实现响应式布局
    - Requirements: 10.3

- [x] 8. 活动相关组件
  - [x] 8.1 实现ActivityCard组件
    - 创建components/ActivityCard.tsx
    - 显示活动标题、来源、类别、奖金、截止日期
    - Requirements: 3.3
  - [x] 8.2 编写ActivityCard属性测试
    - Property 3: 活动卡片字段显示完整性
    - Validates: Requirements 3.3
  - [x] 8.3 实现FilterBar组件
    - 创建components/FilterBar.tsx
    - 包含类别筛选和信息源筛选下拉框
    - Requirements: 4.1, 4.2, 4.4
  - [x] 8.4 实现SearchBox组件
    - 创建components/SearchBox.tsx
    - 包含搜索输入框和清除按钮
    - Requirements: 5.1, 5.3, 5.4, 5.5
  - [x] 8.5 实现SortSelect组件
    - 创建components/SortSelect.tsx
    - 支持按创建时间、截止日期、奖金排序
    - Requirements: 6.1, 6.2, 6.4
  - [x] 8.6 实现Pagination组件
    - 创建components/Pagination.tsx
    - 显示分页控件
    - Requirements: 3.4

- [x] 9. 信息源相关组件
  - [x] 9.1 实现SourceCard组件
    - 创建components/SourceCard.tsx
    - 显示信息源名称、类型、状态、最后运行时间、活动数量
    - 状态指示器使用不同颜色
    - Requirements: 8.2, 8.3, 8.7
  - [x] 9.2 编写SourceCard属性测试
    - Property 8: 信息源状态显示完整性
    - Validates: Requirements 8.2, 8.3

- [x] 10. Checkpoint - 组件开发完成
  - 确保所有组件测试通过
  - 检查TypeScript无错误

- [x] 11. 页面实现
  - [x] 11.1 实现ActivitiesPage
    - 创建pages/ActivitiesPage.tsx
    - 集成FilterBar、SearchBox、SortSelect、ActivityCard、Pagination
    - 实现URL参数同步
    - Requirements: 3.1, 3.2, 3.5, 3.7, 4.3, 4.5, 5.3, 6.3
  - [x] 11.2 编写筛选器属性测试
    - Property 4: 筛选器状态同步
    - Validates: Requirements 4.3, 4.5
  - [x] 11.3 编写排序属性测试
    - Property 5: 排序结果正确性
    - Validates: Requirements 6.3
  - [x] 11.4 实现ActivityDetailPage
    - 创建pages/ActivityDetailPage.tsx
    - 显示活动完整信息
    - 提供返回按钮和原始链接
    - Requirements: 7.1, 7.2, 7.3, 7.5, 7.6
  - [x] 11.5 编写活动详情属性测试
    - Property 6: 活动详情字段显示完整性
    - Validates: Requirements 7.2
  - [x] 11.6 实现SourcesPage
    - 创建pages/SourcesPage.tsx
    - 显示所有信息源状态
    - 提供单个刷新和全部刷新按钮
    - Requirements: 8.1, 8.4, 8.5, 8.6
  - [x] 11.7 实现DashboardPage
    - 创建pages/DashboardPage.tsx
    - 显示统计信息：总活动数、总信息源数、按类别统计、按来源统计
    - 实现60秒自动刷新
    - Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
  - [x] 11.8 实现NotFoundPage
    - 创建pages/NotFoundPage.tsx
    - 显示404错误页面
    - Requirements: 7.7

- [x] 12. 路由配置
  - [x] 12.1 配置React Router
    - 安装react-router-dom
    - 配置路由：/, /activities, /activities/:id, /sources, /dashboard
    - 实现路由守卫和404处理
    - Requirements: 3.5, 10.2

- [x] 13. 应用入口
  - [x] 13.1 实现App.tsx
    - 配置Router和Layout
    - 集成Toast通知系统
    - Requirements: 10.1
  - [x] 13.2 配置main.tsx
    - 渲染App组件
    - 配置严格模式

- [x] 14. 错误处理集成
  - [x] 14.1 实现全局错误处理
    - 创建ErrorBoundary组件
    - 集成Toast通知
    - Requirements: 11.1, 11.4
  - [x] 14.2 编写错误处理属性测试
    - Property 9: API失败时显示错误提示
    - Validates: Requirements 11.1

- [x] 15. Checkpoint - 功能开发完成
  - 确保所有页面正常工作
  - 确保所有测试通过
  - 检查TypeScript无错误

- [x] 16. 构建与优化
  - [x] 16.1 配置生产构建
    - 优化vite.config.ts
    - 配置代码分割
    - Requirements: 13.5
  - [x] 16.2 验证生产构建
    - 运行npm run build
    - 确保无TypeScript错误
    - Requirements: 13.5

- [x] 17. 后端API集成测试
  - [x] 17.1 编写API端点集成测试
    - 测试GET /api/activities返回数据结构与Activity接口匹配
    - 测试GET /api/sources返回数据结构与Source接口匹配
    - 测试GET /api/stats返回数据结构与StatsResponse接口匹配
    - Requirements: 2.1, 13.2, 13.3
  - [x] 17.2 编写API响应字段验证测试
    - 验证Activity响应包含所有必需字段：id, title, source_id, source_name, url, category, created_at, updated_at
    - 验证Source响应包含所有必需字段：id, name, type, status, activity_count
    - 验证筛选参数正确传递到后端
    - Requirements: 1.4, 13.2, 13.3
  - [x] 17.3 编写API错误响应测试
    - 测试404响应处理（活动不存在）
    - 测试500响应处理（服务器错误）
    - 测试网络错误处理（后端不可用）
    - Requirements: 2.2, 2.3, 11.4

- [x] 18. Final Checkpoint
  - 确保所有测试通过（单元测试、属性测试、集成测试）
  - 确保生产构建成功、
  - 验证与后端API集成正常
  - 启动后端服务，手动验证前端功能

## Notes

- 所有属性测试使用fast-check库，每个测试运行100次迭代
- 使用Vitest作为测试框架
- TailwindCSS用于所有样式，不使用额外CSS文件
- API调用使用fetch，不引入axios以减少依赖
