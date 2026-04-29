import { ApiError } from './api'
import type {
  ProductSelectionOpportunityDetail,
  ProductSelectionOpportunityFilters,
  ProductSelectionOpportunityListResponse,
  ProductSelectionResearchJobCreateRequest,
  ProductSelectionResearchJobResponse,
  ProductSelectionTrackingItem,
  ProductSelectionTrackingFilters,
  ProductSelectionTrackingState,
  ProductSelectionTrackingStatus,
  ProductSelectionTrackingUpsertRequest,
  ProductSelectionWorkspaceResponse,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ProductSelectionApiService {
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

  createResearchJob(
    payload: ProductSelectionResearchJobCreateRequest
  ): Promise<ProductSelectionResearchJobResponse> {
    return this.request<ProductSelectionResearchJobResponse>('/api/product-selection/research-jobs', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  getResearchJob(jobId: string): Promise<ProductSelectionResearchJobResponse> {
    return this.request<ProductSelectionResearchJobResponse>(
      `/api/product-selection/research-jobs/${jobId}`
    )
  }

  getOpportunities(
    filters: ProductSelectionOpportunityFilters = {}
  ): Promise<ProductSelectionOpportunityListResponse> {
    return this.request<ProductSelectionOpportunityListResponse>(
      `/api/product-selection/opportunities${this.buildQueryString(filters)}`
    )
  }

  getOpportunity(opportunityId: string): Promise<ProductSelectionOpportunityDetail> {
    return this.request<ProductSelectionOpportunityDetail>(
      `/api/product-selection/opportunities/${opportunityId}`
    )
  }

  getTracking(
    filters: ProductSelectionTrackingFilters | ProductSelectionTrackingStatus = {}
  ): Promise<ProductSelectionTrackingItem[]> {
    const normalizedFilters =
      typeof filters === 'string' || filters === undefined ? { status: filters } : filters
    return this.request<ProductSelectionTrackingItem[]>(
      `/api/product-selection/tracking${this.buildQueryString(normalizedFilters)}`
    )
  }

  createTracking(
    opportunityId: string,
    payload: ProductSelectionTrackingUpsertRequest
  ): Promise<ProductSelectionTrackingState> {
    return this.request<ProductSelectionTrackingState>(
      `/api/product-selection/tracking/${opportunityId}`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    )
  }

  updateTracking(
    opportunityId: string,
    payload: ProductSelectionTrackingUpsertRequest
  ): Promise<ProductSelectionTrackingState> {
    return this.request<ProductSelectionTrackingState>(
      `/api/product-selection/tracking/${opportunityId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }
    )
  }

  deleteTracking(opportunityId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/product-selection/tracking/${opportunityId}`, {
      method: 'DELETE',
    })
  }

  getWorkspace(): Promise<ProductSelectionWorkspaceResponse> {
    return this.request<ProductSelectionWorkspaceResponse>('/api/product-selection/workspace')
  }
}

export const productSelectionApi = new ProductSelectionApiService()

export default productSelectionApi
