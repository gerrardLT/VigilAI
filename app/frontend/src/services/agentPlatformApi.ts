import { ApiError } from './api'
import type {
  AgentArtifact,
  AgentSession,
  AgentSessionCreateRequest,
  AgentTurn,
  AgentTurnCreateRequest,
  AgentTurnReply,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class AgentPlatformApiService {
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

  createSession(payload: AgentSessionCreateRequest): Promise<AgentSession> {
    return this.request<AgentSession>('/api/agent/sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  getSession(sessionId: string): Promise<AgentSession> {
    return this.request<AgentSession>(`/api/agent/sessions/${sessionId}`)
  }

  postTurn(sessionId: string, payload: AgentTurnCreateRequest): Promise<AgentTurnReply> {
    return this.request<AgentTurnReply>(`/api/agent/sessions/${sessionId}/turns`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  listTurns(sessionId: string): Promise<AgentTurn[]> {
    return this.request<AgentTurn[]>(`/api/agent/sessions/${sessionId}/turns`)
  }

  listArtifacts(sessionId: string): Promise<AgentArtifact[]> {
    return this.request<AgentArtifact[]>(`/api/agent/sessions/${sessionId}/artifacts`)
  }
}

export const agentPlatformApi = new AgentPlatformApiService()

export default agentPlatformApi
