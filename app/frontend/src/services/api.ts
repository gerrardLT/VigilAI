import type {
  Activity,
  ActivityFilters,
  ActivityListResponse,
  CategoryOption,
  RefreshResponse,
  Source,
  StatsResponse,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * API错误类
 * 包含HTTP状态码和错误消息
 */
export class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string
  ) {
    super(`API Error: ${statusCode} ${message}`)
    this.name = 'ApiError'
  }
}

/**
 * API服务类
 * 封装所有后端API调用
 */
class ApiService {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  /**
   * 通用请求方法
   * 处理HTTP错误并返回JSON响应
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    signal?: AbortSignal
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      const response = await fetch(url, {
        ...options,
        signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText)
        throw new ApiError(response.status, errorText)
      }

      return response.json()
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw error
        }
        throw new ApiError(0, error.message)
      }
      throw new ApiError(0, 'Unknown error')
    }
  }

  /**
   * 获取活动列表
   * GET /api/activities
   */
  async getActivities(
    filters: ActivityFilters = {},
    signal?: AbortSignal
  ): Promise<ActivityListResponse> {
    const params = new URLSearchParams()
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '' && value !== null) {
        params.append(key, String(value))
      }
    })
    
    const queryString = params.toString()
    const endpoint = queryString ? `/api/activities?${queryString}` : '/api/activities'
    
    return this.request<ActivityListResponse>(endpoint, {}, signal)
  }

  /**
   * 获取活动详情
   * GET /api/activities/{id}
   */
  async getActivity(id: string, signal?: AbortSignal): Promise<Activity> {
    return this.request<Activity>(`/api/activities/${id}`, {}, signal)
  }

  /**
   * 获取信息源列表
   * GET /api/sources
   */
  async getSources(signal?: AbortSignal): Promise<Source[]> {
    return this.request<Source[]>('/api/sources', {}, signal)
  }

  /**
   * 刷新指定信息源
   * POST /api/sources/{id}/refresh
   */
  async refreshSource(sourceId: string, signal?: AbortSignal): Promise<RefreshResponse> {
    return this.request<RefreshResponse>(
      `/api/sources/${sourceId}/refresh`,
      { method: 'POST' },
      signal
    )
  }

  /**
   * 刷新所有信息源
   * POST /api/sources/refresh-all
   */
  async refreshAllSources(signal?: AbortSignal): Promise<RefreshResponse> {
    return this.request<RefreshResponse>(
      '/api/sources/refresh-all',
      { method: 'POST' },
      signal
    )
  }

  /**
   * 获取统计信息
   * GET /api/stats
   */
  async getStats(signal?: AbortSignal): Promise<StatsResponse> {
    return this.request<StatsResponse>('/api/stats', {}, signal)
  }

  /**
   * 获取类别列表
   * GET /api/categories
   */
  async getCategories(signal?: AbortSignal): Promise<CategoryOption[]> {
    return this.request<CategoryOption[]>('/api/categories', {}, signal)
  }

  /**
   * 健康检查
   * GET /api/health
   */
  async healthCheck(signal?: AbortSignal): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>('/api/health', {}, signal)
  }
}

// 导出单例实例
export const api = new ApiService(API_BASE_URL)

// 导出类以便测试
export { ApiService }
