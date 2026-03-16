import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import type { Source } from '../types'

interface UseSourcesResult {
  sources: Source[]
  loading: boolean
  error: string | null
  refreshing: string | null // 正在刷新的source id
  refreshSource: (sourceId: string) => Promise<boolean>
  refreshAllSources: () => Promise<boolean>
  refetch: () => Promise<void>
}

/**
 * 信息源数据Hook
 * 封装信息源数据获取和刷新操作
 */
export function useSources(): UseSourcesResult {
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState<string | null>(null)

  const fetchSources = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await api.getSources()
      setSources(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取信息源列表失败'
      setError(message)
      setSources([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSources()
  }, [fetchSources])

  const refreshSource = useCallback(async (sourceId: string): Promise<boolean> => {
    setRefreshing(sourceId)
    setError(null)

    try {
      await api.refreshSource(sourceId)
      // 刷新后重新获取信息源状态
      await fetchSources()
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : '刷新信息源失败'
      setError(message)
      return false
    } finally {
      setRefreshing(null)
    }
  }, [fetchSources])

  const refreshAllSources = useCallback(async (): Promise<boolean> => {
    setRefreshing('all')
    setError(null)

    try {
      await api.refreshAllSources()
      // 刷新后重新获取信息源状态
      await fetchSources()
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : '刷新所有信息源失败'
      setError(message)
      return false
    } finally {
      setRefreshing(null)
    }
  }, [fetchSources])

  return {
    sources,
    loading,
    error,
    refreshing,
    refreshSource,
    refreshAllSources,
    refetch: fetchSources,
  }
}

export default useSources
