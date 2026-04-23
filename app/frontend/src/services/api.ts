import type {
  ActivityListItem,
  ActivityDetail,
  AgentAnalysisJobCreateRequest,
  AgentAnalysisJobDetail,
  AgentAnalysisJobItemDetail,
  AgentAnalysisJobListResponse,
  AgentAnalysisReviewRequest,
  AgentAnalysisReviewResult,
  AnalysisResultsFilters,
  AnalysisResultsResponse,
  AnalysisTemplate,
  AnalysisTemplateCreateRequest,
  AnalysisTemplateDraftPreviewRequest,
  AnalysisTemplatePreview,
  AnalysisTemplatePreviewResults,
  AnalysisTemplateUpdateRequest,
  ActivityFilters,
  ActivityListResponse,
  CategoryOption,
  DigestCandidateRequest,
  DigestDetail,
  DigestGenerateRequest,
  DigestSendRequest,
  OpportunityAiFilterRequest,
  OpportunityAiFilterResponse,
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
    super(`接口请求失败（${statusCode}）：${message}`)
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
      throw new ApiError(0, '未知错误')
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

  async getAnalysisTemplates(signal?: AbortSignal): Promise<AnalysisTemplate[]> {
    return this.request<AnalysisTemplate[]>('/api/analysis/templates', {}, signal)
  }

  async getDefaultAnalysisTemplate(signal?: AbortSignal): Promise<AnalysisTemplate> {
    return this.request<AnalysisTemplate>('/api/analysis/templates/default', {}, signal)
  }

  async createAnalysisTemplate(
    payload: AnalysisTemplateCreateRequest,
    signal?: AbortSignal
  ): Promise<AnalysisTemplate> {
    return this.request<AnalysisTemplate>(
      '/api/analysis/templates',
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async duplicateAnalysisTemplate(
    templateId: string,
    name: string,
    signal?: AbortSignal
  ): Promise<AnalysisTemplate> {
    return this.request<AnalysisTemplate>(
      `/api/analysis/templates/${templateId}/duplicate`,
      this.withJsonBody('POST', { name }),
      signal
    )
  }

  async activateAnalysisTemplate(
    templateId: string,
    signal?: AbortSignal
  ): Promise<AnalysisTemplate> {
    return this.request<AnalysisTemplate>(
      `/api/analysis/templates/${templateId}/activate`,
      { method: 'POST' },
      signal
    )
  }

  async updateAnalysisTemplate(
    templateId: string,
    payload: AnalysisTemplateUpdateRequest,
    signal?: AbortSignal
  ): Promise<AnalysisTemplate> {
    return this.request<AnalysisTemplate>(
      `/api/analysis/templates/${templateId}`,
      this.withJsonBody('PATCH', payload),
      signal
    )
  }

  async deleteAnalysisTemplate(
    templateId: string,
    signal?: AbortSignal
  ): Promise<SuccessResponse> {
    return this.request<SuccessResponse>(
      `/api/analysis/templates/${templateId}`,
      { method: 'DELETE' },
      signal
    )
  }

  async previewAnalysisTemplate(
    templateId: string,
    signal?: AbortSignal
  ): Promise<AnalysisTemplatePreview> {
    return this.request<AnalysisTemplatePreview>(
      `/api/analysis/templates/${templateId}/preview`,
      {},
      signal
    )
  }

  async previewDraftAnalysisTemplate(
    payload: AnalysisTemplateDraftPreviewRequest,
    signal?: AbortSignal
  ): Promise<AnalysisTemplatePreview> {
    return this.request<AnalysisTemplatePreview>(
      '/api/analysis/templates/preview',
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async previewDraftAnalysisTemplateResults(
    payload: AnalysisTemplateDraftPreviewRequest,
    signal?: AbortSignal
  ): Promise<AnalysisTemplatePreviewResults> {
    return this.request<AnalysisTemplatePreviewResults>(
      '/api/analysis/templates/preview/results',
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async runAnalysis(signal?: AbortSignal): Promise<{ success: boolean; processed: number }> {
    return this.request<{ success: boolean; processed: number }>(
      '/api/analysis/run',
      { method: 'POST' },
      signal
    )
  }

  async getAnalysisResults(
    filters: AnalysisResultsFilters = {},
    signal?: AbortSignal
  ): Promise<AnalysisResultsResponse> {
    return this.request<AnalysisResultsResponse>(
      `/api/analysis/results${this.buildQueryString(filters)}`,
      {},
      signal
    )
  }

  async getAnalysisResult(activityId: string, signal?: AbortSignal): Promise<ActivityDetail> {
    return this.request<ActivityDetail>(`/api/analysis/results/${activityId}`, {}, signal)
  }

  async createAgentAnalysisJob(
    payload: AgentAnalysisJobCreateRequest,
    signal?: AbortSignal
  ): Promise<AgentAnalysisJobDetail> {
    return this.request<AgentAnalysisJobDetail>(
      '/api/agent-analysis/jobs',
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async aiFilterActivities(
    payload: OpportunityAiFilterRequest,
    signal?: AbortSignal
  ): Promise<OpportunityAiFilterResponse> {
    return this.request<OpportunityAiFilterResponse>(
      '/api/activities/ai-filter',
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async getAgentAnalysisJobs(signal?: AbortSignal): Promise<AgentAnalysisJobListResponse> {
    return this.request<AgentAnalysisJobListResponse>('/api/agent-analysis/jobs', {}, signal)
  }

  async getAgentAnalysisJob(jobId: string, signal?: AbortSignal): Promise<AgentAnalysisJobDetail> {
    return this.request<AgentAnalysisJobDetail>(
      `/api/agent-analysis/jobs/${jobId}`,
      {},
      signal
    )
  }

  async getAgentAnalysisItem(
    itemId: string,
    signal?: AbortSignal
  ): Promise<AgentAnalysisJobItemDetail> {
    return this.request<AgentAnalysisJobItemDetail>(
      `/api/agent-analysis/items/${itemId}`,
      {},
      signal
    )
  }

  async approveAgentAnalysisItem(
    itemId: string,
    payload: AgentAnalysisReviewRequest = {},
    signal?: AbortSignal
  ): Promise<AgentAnalysisReviewResult> {
    return this.request<AgentAnalysisReviewResult>(
      `/api/agent-analysis/items/${itemId}/approve`,
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async rejectAgentAnalysisItem(
    itemId: string,
    payload: AgentAnalysisReviewRequest = {},
    signal?: AbortSignal
  ): Promise<AgentAnalysisReviewResult> {
    return this.request<AgentAnalysisReviewResult>(
      `/api/agent-analysis/items/${itemId}/reject`,
      this.withJsonBody('POST', payload),
      signal
    )
  }

  async approveAgentAnalysisBatch(
    itemIds: string[],
    payload: AgentAnalysisReviewRequest = {},
    signal?: AbortSignal
  ): Promise<AgentAnalysisReviewResult[]> {
    return Promise.all(
      itemIds.map(itemId => this.approveAgentAnalysisItem(itemId, payload, signal))
    )
  }

  async rejectAgentAnalysisBatch(
    itemIds: string[],
    payload: AgentAnalysisReviewRequest = {},
    signal?: AbortSignal
  ): Promise<AgentAnalysisReviewResult[]> {
    return Promise.all(
      itemIds.map(itemId => this.rejectAgentAnalysisItem(itemId, payload, signal))
    )
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
