import type { RefreshResponse, Source } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string
  ) {
    super(`Request failed (${statusCode}): ${message}`)
    this.name = 'ApiError'
  }
}

class ApiService {
  constructor(private readonly baseUrl: string) {}

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
}

export const api = new ApiService(API_BASE_URL)

export default api
