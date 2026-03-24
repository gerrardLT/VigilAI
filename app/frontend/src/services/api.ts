import type {
  ActivityListItem,
  ActivityDetail,
  ActivityFilters,
  ActivityListResponse,
  CategoryOption,
  DigestCandidateRequest,
  DigestDetail,
  DigestGenerateRequest,
  DigestSendRequest,
  RefreshResponse,
  Source,
  StatsResponse,
  SuccessResponse,
  TrackingItem,
  TrackingState,
  TrackingStatus,
  TrackingUpsertRequest,
  WorkspaceResponse,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string
  ) {
    super(`API Error: ${statusCode} ${message}`)
    this.name = 'ApiError'
  }
}

class ApiService {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    signal?: AbortSignal
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    }).catch((error: unknown) => {
      if (error instanceof Error && error.name === 'AbortError') {
        throw error
      }
      if (error instanceof Error) {
        throw new ApiError(0, error.message)
      }
      throw new ApiError(0, 'Unknown error')
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText)
      throw new ApiError(response.status, errorText)
    }

    return response.json() as Promise<T>
  }

  private buildQueryString(params: object) {
    const searchParams = new URLSearchParams()

    Object.entries(params as Record<string, unknown>).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value))
      }
    })

    const queryString = searchParams.toString()
    return queryString ? `?${queryString}` : ''
  }

  private withJsonBody(method: string, body?: object): RequestInit {
    if (!body || Object.keys(body).length === 0) {
      return { method }
    }
    return {
      method,
      body: JSON.stringify(body),
    }
  }

  async getActivities(
    filters: ActivityFilters = {},
    signal?: AbortSignal
  ): Promise<ActivityListResponse> {
    return this.request<ActivityListResponse>(
      `/api/activities${this.buildQueryString(filters)}`,
      {},
      signal
    )
  }

  async getActivity(id: string, signal?: AbortSignal): Promise<ActivityDetail> {
    return this.request<ActivityDetail>(`/api/activities/${id}`, {}, signal)
  }

  async getSources(signal?: AbortSignal): Promise<Source[]> {
    return this.request<Source[]>('/api/sources', {}, signal)
  }

  async refreshSource(sourceId: string, signal?: AbortSignal): Promise<RefreshResponse> {
    return this.request<RefreshResponse>(
      `/api/sources/${sourceId}/refresh`,
      { method: 'POST' },
      signal
    )
  }

  async refreshAllSources(signal?: AbortSignal): Promise<RefreshResponse> {
    return this.request<RefreshResponse>(
      '/api/sources/refresh-all',
      { method: 'POST' },
      signal
    )
  }

  async getStats(signal?: AbortSignal): Promise<StatsResponse> {
    return this.request<StatsResponse>('/api/stats', {}, signal)
  }

  async getWorkspace(signal?: AbortSignal): Promise<WorkspaceResponse> {
    return this.request<WorkspaceResponse>('/api/workspace', {}, signal)
  }

  async getTracking(status?: TrackingStatus, signal?: AbortSignal): Promise<TrackingItem[]> {
    return this.request<TrackingItem[]>(
      `/api/tracking${this.buildQueryString({ status })}`,
      {},
      signal
    )
  }

  async createTracking(
    activityId: string,
    payload: TrackingUpsertRequest,
    signal?: AbortSignal
  ): Promise<TrackingState> {
    return this.request<TrackingState>(
      `/api/tracking/${activityId}`,
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async updateTracking(
    activityId: string,
    payload: TrackingUpsertRequest,
    signal?: AbortSignal
  ): Promise<TrackingState> {
    return this.request<TrackingState>(
      `/api/tracking/${activityId}`,
      this.withJsonBody('PATCH', payload),
      signal
    )
  }

  async deleteTracking(activityId: string, signal?: AbortSignal): Promise<SuccessResponse> {
    return this.request<SuccessResponse>(
      `/api/tracking/${activityId}`,
      { method: 'DELETE' },
      signal
    )
  }

  async getDigests(signal?: AbortSignal): Promise<DigestDetail[]> {
    return this.request<DigestDetail[]>('/api/digests', {}, signal)
  }

  async getDigestCandidates(
    digestDate?: string,
    signal?: AbortSignal
  ): Promise<ActivityListItem[]> {
    return this.request<ActivityListItem[]>(
      `/api/digests/candidates${this.buildQueryString({ digest_date: digestDate })}`,
      {},
      signal
    )
  }

  async getDigest(id: string, signal?: AbortSignal): Promise<DigestDetail> {
    return this.request<DigestDetail>(`/api/digests/${id}`, {}, signal)
  }

  async generateDigest(
    payload: DigestGenerateRequest = {},
    signal?: AbortSignal
  ): Promise<DigestDetail> {
    return this.request<DigestDetail>(
      '/api/digests/generate',
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async sendDigest(
    digestId: string,
    payload: DigestSendRequest = {},
    signal?: AbortSignal
  ): Promise<DigestDetail> {
    return this.request<DigestDetail>(
      `/api/digests/${digestId}/send`,
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async addDigestCandidate(
    activityId: string,
    payload: DigestCandidateRequest = {},
    signal?: AbortSignal
  ): Promise<SuccessResponse> {
    return this.request<SuccessResponse>(
      `/api/digests/candidates/${activityId}`,
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async removeDigestCandidate(
    activityId: string,
    payload: DigestCandidateRequest = {},
    signal?: AbortSignal
  ): Promise<SuccessResponse> {
    return this.request<SuccessResponse>(
      `/api/digests/candidates/${activityId}${this.buildQueryString({
        digest_date: payload.digest_date,
      })}`,
      { method: 'DELETE' },
      signal
    )
  }

  async getCategories(signal?: AbortSignal): Promise<CategoryOption[]> {
    return this.request<CategoryOption[]>('/api/categories', {}, signal)
  }

  async healthCheck(signal?: AbortSignal): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>('/api/health', {}, signal)
  }
}

export const api = new ApiService(API_BASE_URL)

export { ApiService }
