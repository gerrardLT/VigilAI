import { useCallback, useEffect, useState } from 'react'
import { rewardOpportunityApi } from '../services/rewardOpportunityApi'
import type { RewardOpportunityItem } from '../types'

export function useRewardOpportunities() {
  const [items, setItems] = useState<RewardOpportunityItem[]>([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    classification: '',
    source_platform: '',
    opportunity_type: '',
    reward_type: '',
    evidence_status: '',
    sort_by: 'created_at',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadOpportunities = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await rewardOpportunityApi.listOpportunities(filters)
      setItems(response.items)
      setTotal(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载奖励活动机会库失败')
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void loadOpportunities()
  }, [loadOpportunities])

  return { items, total, filters, setFilters, loading, error, reload: loadOpportunities }
}

export default useRewardOpportunities
