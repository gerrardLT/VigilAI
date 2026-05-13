import { ApiError } from './api'
import type {
  RewardOpportunityItem,
  RewardOpportunityListResponse,
  RewardOpportunityOperationsResponse,
  RewardOpportunityOverview,
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
      throw new ApiError(0, '未知错误')
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

  getOpportunities(): Promise<RewardOpportunityListResponse> {
    return this.request<RewardOpportunityListResponse>('/api/reward-opportunities')
  }

  getOpportunity(opportunityId: string): Promise<RewardOpportunityItem> {
    return this.request<RewardOpportunityItem>(`/api/reward-opportunities/${opportunityId}`)
  }

  getOperations(): Promise<RewardOpportunityOperationsResponse> {
    return this.request<RewardOpportunityOperationsResponse>('/api/reward-opportunities/operations')
  }
}

export const rewardOpportunityApi = new RewardOpportunityApiService()

export default rewardOpportunityApi
