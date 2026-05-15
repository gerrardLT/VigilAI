import { ApiError } from './api'
import type {
  RewardOpportunityItem,
  RewardOpportunityListResponse,
  RewardOpportunityOperationsResponse,
  RewardOpportunityOverview,
  RewardScoutSettingsResponse,
  RewardSourceDetailResponse,
  RewardSourceDiscoveryResponse,
  RewardSourcePauseResponse,
  RewardSourceSyncResult,
  RewardOpportunitySyncResponse,
  RewardSourceFeedItem,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class RewardOpportunityApiService {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    }).catch((error: unknown) => {
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

  getOverview(): Promise<RewardOpportunityOverview> {
    return this.request<RewardOpportunityOverview>('/api/reward-opportunities/overview')
  }

  listOpportunities(params?: {
    classification?: string
    source_platform?: string
    opportunity_type?: string
    reward_type?: string
    evidence_status?: string
    sort_by?: string
  }): Promise<RewardOpportunityListResponse> {
    const search = new URLSearchParams()
    Object.entries(params ?? {}).forEach(([key, value]) => {
      if (value) search.set(key, value)
    })
    const suffix = search.size > 0 ? `?${search.toString()}` : ''
    return this.request<RewardOpportunityListResponse>(`/api/reward-opportunities${suffix}`)
  }

  getOpportunities(): Promise<RewardOpportunityListResponse> {
    return this.listOpportunities()
  }

  getOpportunity(opportunityId: string): Promise<RewardOpportunityItem> {
    return this.request<RewardOpportunityItem>(`/api/reward-opportunities/${opportunityId}`)
  }

  getOperations(): Promise<RewardOpportunityOperationsResponse> {
    return this.request<RewardOpportunityOperationsResponse>('/api/reward-opportunities/operations')
  }

  getSourceDiscovery(): Promise<RewardSourceDiscoveryResponse> {
    return this.request<RewardSourceDiscoveryResponse>('/api/reward-opportunities/discovery')
  }

  getScoutSettings(): Promise<RewardScoutSettingsResponse> {
    return this.request<RewardScoutSettingsResponse>('/api/reward-opportunities/discovery/settings')
  }

  getSourceDetail(sourceFeedId: string): Promise<RewardSourceDetailResponse> {
    return this.request<RewardSourceDetailResponse>(`/api/reward-opportunities/sources/${sourceFeedId}`)
  }

  updateScoutSettings(payload: { query_templates: string[] }): Promise<RewardScoutSettingsResponse> {
    return this.request<RewardScoutSettingsResponse>('/api/reward-opportunities/discovery/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  importDiscoveredSource(payload: {
    name: string
    entry_url: string
    source_type: string
    source_platform?: string | null
    discovery_queries?: string[]
  }): Promise<RewardSourceFeedItem> {
    return this.request<RewardSourceFeedItem>('/api/reward-opportunities/discovery/import', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  ignoreDiscoveredSource(payload: { dedupe_key: string; entry_url: string; reason?: string | null }): Promise<{ success?: boolean }> {
    return this.request<{ success?: boolean }>('/api/reward-opportunities/discovery/ignore', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  unignoreDiscoveredSource(payload: { dedupe_key: string; entry_url: string; reason?: string | null }): Promise<{ success?: boolean }> {
    return this.request<{ success?: boolean }>('/api/reward-opportunities/discovery/unignore', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  syncSources(): Promise<RewardOpportunitySyncResponse> {
    return this.request<RewardOpportunitySyncResponse>('/api/reward-opportunities/sync', {
      method: 'POST',
    })
  }

  syncSingleSource(sourceFeedId: string): Promise<RewardSourceSyncResult> {
    return this.request<RewardSourceSyncResult>(`/api/reward-opportunities/sync/${sourceFeedId}`, {
      method: 'POST',
    })
  }

  pauseSource(sourceFeedId: string): Promise<RewardSourcePauseResponse> {
    return this.request<RewardSourcePauseResponse>(`/api/reward-opportunities/sources/${sourceFeedId}/pause`, {
      method: 'POST',
    })
  }

  resumeSource(sourceFeedId: string): Promise<RewardSourcePauseResponse> {
    return this.request<RewardSourcePauseResponse>(`/api/reward-opportunities/sources/${sourceFeedId}/resume`, {
      method: 'POST',
    })
  }

  updateSource(
    sourceFeedId: string,
    payload: {
      name?: string
      source_type?: string
      source_platform?: string | null
      entry_url?: string | null
      merge_group_key?: string | null
      preferred_entry_url?: string | null
    }
  ): Promise<RewardSourceDetailResponse> {
    return this.request<RewardSourceDetailResponse>(`/api/reward-opportunities/sources/${sourceFeedId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  updateSourceSchedule(
    sourceFeedId: string,
    payload: { auto_sync_enabled: boolean; sync_interval_minutes: number }
  ): Promise<{ id: string; auto_sync_enabled: boolean; sync_interval_minutes: number; updated_at: string }> {
    return this.request(`/api/reward-opportunities/sources/${sourceFeedId}/schedule`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  executeRecommendedAction(sourceFeedId: string, action: string): Promise<RewardSourceDetailResponse | RewardSourceSyncResult> {
    return this.request(`/api/reward-opportunities/sources/${sourceFeedId}/recommended-action`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
  }
}

export const rewardOpportunityApi = new RewardOpportunityApiService()

export default rewardOpportunityApi
