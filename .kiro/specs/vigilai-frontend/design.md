# Design Document: VigilAI Frontend

## Overview

VigilAI前端是一个基于React 18 + TypeScript + Vite + TailwindCSS的单页应用（SPA），通过调用后端REST API为用户提供活动浏览、筛选、搜索和信息源管理功能。

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    React App                          │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │              Router (React Router)           │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │           │              │              │            │   │
│  │  ┌────────▼───┐  ┌──────▼──────┐  ┌───▼────────┐   │   │
│  │  │ Activities │  │   Sources   │  │ Dashboard  │   │   │
│  │  │   Page     │  │    Page     │  │   Page     │   │   │
│  │  └────────────┘  └─────────────┘  └────────────┘   │   │
│  │           │              │              │            │   │
│  │  ┌────────▼──────────────▼──────────────▼────────┐  │   │
│  │  │              API Service Layer                 │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend API (FastAPI)                      │
│                   http://localhost:8000                      │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 项目结构

```
app/frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── .env
├── src/
│   ├── main.tsx                 # 应用入口
│   ├── App.tsx                  # 根组件
│   ├── types/
│   │   └── index.ts             # TypeScript类型定义
│   ├── services/
│   │   └── api.ts               # API服务层
│   ├── components/
│   │   ├── Layout.tsx           # 布局组件
│   │   ├── Header.tsx           # 头部导航
│   │   ├── Footer.tsx           # 页脚
│   │   ├── ActivityCard.tsx     # 活动卡片
│   │   ├── SourceCard.tsx       # 信息源卡片
│   │   ├── FilterBar.tsx        # 筛选栏
│   │   ├── SearchBox.tsx        # 搜索框
│   │   ├── SortSelect.tsx       # 排序选择
│   │   ├── Pagination.tsx       # 分页组件
│   │   ├── Loading.tsx          # 加载状态
│   │   ├── ErrorMessage.tsx     # 错误提示
│   │   └── Toast.tsx            # 通知提示
│   ├── pages/
│   │   ├── ActivitiesPage.tsx   # 活动列表页
│   │   ├── ActivityDetailPage.tsx # 活动详情页
│   │   ├── SourcesPage.tsx      # 信息源管理页
│   │   ├── DashboardPage.tsx    # 仪表盘页
│   │   └── NotFoundPage.tsx     # 404页面
│   ├── hooks/
│   │   ├── useActivities.ts     # 活动数据Hook
│   │   ├── useSources.ts        # 信息源数据Hook
│   │   ├── useStats.ts          # 统计数据Hook
│   │   └── useDebounce.ts       # 防抖Hook
│   └── utils/
│       ├── formatDate.ts        # 日期格式化
│       └── constants.ts         # 常量定义
└── public/
    └── favicon.ico
```

### TypeScript类型定义

```typescript
// types/index.ts

// 活动类别枚举
export type Category = 'hackathon' | 'competition' | 'airdrop' | 'bounty' | 'grant' | 'event';

// 优先级枚举
export type Priority = 'high' | 'medium' | 'low';

// 信息源类型枚举
export type SourceType = 'rss' | 'web' | 'api';

// 信息源状态枚举
export type SourceStatus = 'idle' | 'running' | 'success' | 'error';

// 奖金信息
export interface Prize {
  amount: number | null;
  currency: string;
  description: string | null;
}

// 活动时间信息
export interface ActivityDates {
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
}

// 活动实体
export interface Activity {
  id: string;
  title: string;
  description: string | null;
  source_id: string;
  source_name: string;
  url: string;
  category: Category;
  tags: string[];
  prize: Prize | null;
  dates: ActivityDates | null;
  location: string | null;
  organizer: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

// 信息源实体
export interface Source {
  id: string;
  name: string;
  type: SourceType;
  status: SourceStatus;
  last_run: string | null;
  last_success: string | null;
  activity_count: number;
  error_message: string | null;
}

// 活动列表响应
export interface ActivityListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Activity[];
}

// 统计信息响应
export interface StatsResponse {
  total_activities: number;
  total_sources: number;
  activities_by_category: Record<string, number>;
  activities_by_source: Record<string, number>;
  last_update: string | null;
}

// 刷新响应
export interface RefreshResponse {
  success: boolean;
  message: string;
}

// 类别选项
export interface CategoryOption {
  value: string;
  label: string;
}

// 筛选参数
export interface ActivityFilters {
  category?: string;
  source_id?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}
```

### API服务层

```typescript
// services/api.ts

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // 获取活动列表
  async getActivities(filters: ActivityFilters): Promise<ActivityListResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.append(key, String(value));
      }
    });
    return this.request(`/api/activities?${params.toString()}`);
  }

  // 获取活动详情
  async getActivity(id: string): Promise<Activity> {
    return this.request(`/api/activities/${id}`);
  }

  // 获取信息源列表
  async getSources(): Promise<Source[]> {
    return this.request('/api/sources');
  }

  // 刷新指定信息源
  async refreshSource(sourceId: string): Promise<RefreshResponse> {
    return this.request(`/api/sources/${sourceId}/refresh`, { method: 'POST' });
  }

  // 刷新所有信息源
  async refreshAllSources(): Promise<RefreshResponse> {
    return this.request('/api/sources/refresh-all', { method: 'POST' });
  }

  // 获取统计信息
  async getStats(): Promise<StatsResponse> {
    return this.request('/api/stats');
  }

  // 获取类别列表
  async getCategories(): Promise<CategoryOption[]> {
    return this.request('/api/categories');
  }

  // 健康检查
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request('/api/health');
  }
}

export const api = new ApiService(API_BASE_URL);
```

## Data Models

数据模型与后端完全一致，详见上方TypeScript类型定义。

### 状态管理

使用React Hooks进行状态管理：

```typescript
// hooks/useActivities.ts
export function useActivities(initialFilters: ActivityFilters) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState(initialFilters);

  const fetchActivities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getActivities(filters);
      setActivities(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  return { activities, total, loading, error, filters, setFilters, refetch: fetchActivities };
}
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: TypeScript接口与后端模型字段匹配

For any Activity object returned from the backend API, the frontend Activity interface SHALL contain all the same fields with compatible types.

Validates: Requirements 1.4, 13.2, 13.3

### Property 2: API错误处理一致性

For any HTTP error response (status >= 400), the API service SHALL throw an Error containing the status code and error message.

Validates: Requirements 2.2, 2.3

### Property 3: 活动卡片字段显示完整性

For any Activity with non-null fields, the ActivityCard component SHALL render the title, source_name, and category; and SHALL conditionally render prize and deadline when available.

Validates: Requirements 3.3

### Property 4: 筛选器状态同步

For any filter selection (category or source), the URL query parameters SHALL reflect the current filter state, and the activity list SHALL update to show only matching results.

Validates: Requirements 4.3, 4.5

### Property 5: 排序结果正确性

For any sort option selection, the activity list SHALL be ordered according to the selected field and direction.

Validates: Requirements 6.3

### Property 6: 活动详情字段显示完整性

For any Activity fetched by ID, the ActivityDetailPage SHALL display all non-null fields including title, description, source, category, tags, prize, dates, location, and organizer.

Validates: Requirements 7.2

### Property 7: 日期格式化一致性

For any ISO 8601 date string from the backend, the formatDate utility SHALL convert it to a user-friendly format (e.g., "2024-01-15 14:30").

Validates: Requirements 7.4

### Property 8: 信息源状态显示完整性

For any Source object, the SourceCard SHALL display name, type, status with appropriate color indicator, last_run timestamp, and activity_count.

Validates: Requirements 8.2, 8.3

### Property 9: API失败时显示错误提示

For any failed API call, the system SHALL display an error message to the user via toast or error component.

Validates: Requirements 11.1

### Property 10: 异步操作加载状态

For any async operation (API call), the component SHALL display a loading indicator while the operation is in progress.

Validates: Requirements 12.3

## Error Handling

### API错误处理

```typescript
// 统一错误处理
try {
  const data = await api.getActivities(filters);
  // 处理成功响应
} catch (error) {
  if (error instanceof Error) {
    // 显示错误提示
    showToast({ type: 'error', message: error.message });
  }
}
```

### 错误边界

```typescript
// ErrorBoundary组件用于捕获渲染错误
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return <ErrorMessage message="页面加载出错，请刷新重试" />;
    }
    return this.props.children;
  }
}
```

### 网络错误处理

- 后端不可用时显示连接错误提示
- 提供重试按钮
- 自动重试机制（可选）

## Testing Strategy

### 单元测试

使用Vitest + React Testing Library进行单元测试：

- 测试组件渲染
- 测试用户交互
- 测试API服务层
- 测试工具函数

### 属性测试

使用fast-check进行属性测试：

- 测试类型接口匹配
- 测试日期格式化
- 测试筛选逻辑
- 测试排序逻辑

### 测试配置

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
```

### 测试示例

```typescript
// 属性测试示例
import fc from 'fast-check';
import { formatDate } from '../utils/formatDate';

describe('formatDate', () => {
  // Property 7: 日期格式化一致性
  it('should format any valid ISO date string', () => {
    fc.assert(
      fc.property(fc.date(), (date) => {
        const isoString = date.toISOString();
        const formatted = formatDate(isoString);
        // 验证格式化结果包含年月日
        expect(formatted).toMatch(/\d{4}-\d{2}-\d{2}/);
      }),
      { numRuns: 100 }
    );
  });
});
```
