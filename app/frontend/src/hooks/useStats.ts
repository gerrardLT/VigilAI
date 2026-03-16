import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../services/api'
import type { StatsResponse } from '../types'
import { STATS_REFRESH_INTERVAL } from '../utils/constants'

interface UseStatsResult {
  stats: StatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  lastRefresh: Date | null
}

/**
 * 统计数据Hook
 * 封装统计数据获取和自动刷新
 */
export function useStats(autoRefresh: boolean = true): UseStatsResult {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const intervalRef = useRef<number | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await api.getStats()
      setStats(data)
      setLastRefresh(new Date())
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取统计信息失败'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  // 自动刷新
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = window.setInterval(() => {
        fetchStats()
      }, STATS_REFRESH_INTERVAL)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoRefresh, fetchStats])

  return {
    stats,
    loading,
    error,
    refetch: fetchStats,
    lastRefresh,
  }
}

export default useStats
