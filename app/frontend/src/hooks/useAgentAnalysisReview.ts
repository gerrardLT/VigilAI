import { useCallback, useState } from 'react'
import { api } from '../services/api'
import type { AgentAnalysisReviewRequest, AgentAnalysisReviewResult } from '../types'

interface UseAgentAnalysisReviewResult {
  reviewing: boolean
  error: string | null
  approveItem: (
    itemId: string,
    payload?: AgentAnalysisReviewRequest
  ) => Promise<AgentAnalysisReviewResult | null>
  rejectItem: (
    itemId: string,
    payload?: AgentAnalysisReviewRequest
  ) => Promise<AgentAnalysisReviewResult | null>
}

export function useAgentAnalysisReview(): UseAgentAnalysisReviewResult {
  const [reviewing, setReviewing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const approveItem = useCallback(
    async (
      itemId: string,
      payload: AgentAnalysisReviewRequest = {}
    ): Promise<AgentAnalysisReviewResult | null> => {
      setReviewing(true)
      setError(null)
      try {
        return await api.approveAgentAnalysisItem(itemId, payload)
      } catch (err) {
        const message = err instanceof Error ? err.message : '通过 Agent 分析项失败'
        setError(message)
        return null
      } finally {
        setReviewing(false)
      }
    },
    []
  )

  const rejectItem = useCallback(
    async (
      itemId: string,
      payload: AgentAnalysisReviewRequest = {}
    ): Promise<AgentAnalysisReviewResult | null> => {
      setReviewing(true)
      setError(null)
      try {
        return await api.rejectAgentAnalysisItem(itemId, payload)
      } catch (err) {
        const message = err instanceof Error ? err.message : '驳回 Agent 分析项失败'
        setError(message)
        return null
      } finally {
        setReviewing(false)
      }
    },
    []
  )

  return {
    reviewing,
    error,
    approveItem,
    rejectItem,
  }
}

export default useAgentAnalysisReview
