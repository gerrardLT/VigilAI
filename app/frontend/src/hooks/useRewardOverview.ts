import { useCallback, useEffect, useState } from 'react'
import { rewardOpportunityApi } from '../services/rewardOpportunityApi'
import type { RewardOpportunityOverview } from '../types'

export function useRewardOverview() {
  const [overview, setOverview] = useState<RewardOpportunityOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await rewardOpportunityApi.getOverview()
      setOverview(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载奖励活动总览失败')
      setOverview(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadOverview()
  }, [loadOverview])

  return { overview, loading, error, reload: loadOverview }
}

export default useRewardOverview
