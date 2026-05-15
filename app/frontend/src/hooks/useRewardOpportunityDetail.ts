import { useCallback, useEffect, useState } from 'react'
import { rewardOpportunityApi } from '../services/rewardOpportunityApi'
import type { RewardOpportunityItem } from '../types'

export function useRewardOpportunityDetail(id: string) {
  const [item, setItem] = useState<RewardOpportunityItem | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadDetail = useCallback(async () => {
    if (!id) {
      setItem(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await rewardOpportunityApi.getOpportunity(id)
      setItem(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载奖励活动详情失败')
      setItem(null)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void loadDetail()
  }, [loadDetail])

  return { item, loading, error, reload: loadDetail }
}

export default useRewardOpportunityDetail
