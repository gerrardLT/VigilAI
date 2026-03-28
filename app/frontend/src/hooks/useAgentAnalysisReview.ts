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
        const message = err instanceof Error ? err.message : 'Failed to approve agent analysis item'
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
        const message = err instanceof Error ? err.message : 'Failed to reject agent analysis item'
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
