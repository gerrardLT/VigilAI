import { useCallback, useEffect, useState } from 'react'
import { rewardOpportunityApi } from '../services/rewardOpportunityApi'
import type {
  RewardOpportunityItem,
  RewardOpportunityOperationsResponse,
  RewardOpportunityOverview,
} from '../types'

export function useRewardOpportunities() {
  const [overview, setOverview] = useState<RewardOpportunityOverview | null>(null)
  const [items, setItems] = useState<RewardOpportunityItem[]>([])
  const [operations, setOperations] = useState<RewardOpportunityOperationsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadWorkspace = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [nextOverview, nextList, nextOperations] = await Promise.all([
        rewardOpportunityApi.getOverview(),
        rewardOpportunityApi.getOpportunities(),
        rewardOpportunityApi.getOperations(),
      ])
      setOverview(nextOverview)
      setItems(nextList.items)
      setOperations(nextOperations)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载奖励工作台失败')
      setOverview(null)
      setItems([])
      setOperations(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadWorkspace()
  }, [loadWorkspace])

  return { overview, items, operations, loading, error, reload: loadWorkspace }
}

export default useRewardOpportunities
