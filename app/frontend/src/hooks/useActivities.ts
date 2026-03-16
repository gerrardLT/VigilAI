import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import type { Activity, ActivityFilters } from '../types'
import { DEFAULT_PAGE_SIZE, DEFAULT_SORT_BY, DEFAULT_SORT_ORDER } from '../utils/constants'

interface UseActivitiesResult {
  activities: Activity[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  loading: boolean
  error: string | null
  filters: ActivityFilters
  setFilters: (filters: ActivityFilters) => void
  setPage: (page: number) => void
  refetch: () => Promise<void>
}

/**
 * 活动列表数据Hook
 * 封装活动数据获取和状态管理
 */
export function useActivities(initialFilters: ActivityFilters = {}): UseActivitiesResult {
  const [activities, setActivities] = useState<Activity[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<ActivityFilters>({
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
    sort_by: DEFAULT_SORT_BY,
    sort_order: DEFAULT_SORT_ORDER,
    ...initialFilters,
  })

  const fetchActivities = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await api.getActivities(filters)
      setActivities(response.items)
      setTotal(response.total)
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取活动列表失败'
      setError(message)
      setActivities([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  const setFilters = useCallback((newFilters: ActivityFilters) => {
    setFiltersState(prev => ({
      ...prev,
      ...newFilters,
      page: newFilters.page ?? 1, // 更改筛选条件时重置页码
    }))
  }, [])

  const setPage = useCallback((page: number) => {
    setFiltersState(prev => ({
      ...prev,
      page,
    }))
  }, [])

  const pageSize = filters.page_size || DEFAULT_PAGE_SIZE
  const totalPages = Math.ceil(total / pageSize)

  return {
    activities,
    total,
    page: filters.page || 1,
    pageSize,
    totalPages,
    loading,
    error,
    filters,
    setFilters,
    setPage,
    refetch: fetchActivities,
  }
}

export default useActivities
