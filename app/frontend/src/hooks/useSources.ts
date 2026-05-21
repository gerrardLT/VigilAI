import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
 * 使用 React Query 实现数据缓存和自动重新验证
 */
export function useSources(): UseSourcesResult {
  const queryClient = useQueryClient()

  const {
    data: sources = [],
    isLoading: loading,
    error: queryError,
    refetch: queryRefetch,
  } = useQuery<Source[], Error>({
    queryKey: ['sources'],
    queryFn: ({ signal }) => api.getSources(signal),
  })

  const refreshSourceMutation = useMutation({
    mutationFn: (sourceId: string) => api.refreshSource(sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const refreshAllMutation = useMutation({
    mutationFn: () => api.refreshAllSources(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const refreshSource = async (sourceId: string): Promise<boolean> => {
    try {
      await refreshSourceMutation.mutateAsync(sourceId)
      return true
    } catch {
      return false
    }
  }

  const refreshAllSources = async (): Promise<boolean> => {
    try {
      await refreshAllMutation.mutateAsync()
      return true
    } catch {
      return false
    }
  }

  const refetch = async (): Promise<void> => {
    await queryRefetch()
  }

  // Determine which source is currently refreshing
  const refreshing = refreshSourceMutation.isPending
    ? (refreshSourceMutation.variables ?? null)
    : refreshAllMutation.isPending
      ? 'all'
      : null

  // Combine errors from query and mutations
  const error = queryError?.message
    ?? refreshSourceMutation.error?.message
    ?? refreshAllMutation.error?.message
    ?? null

  return {
    sources,
    loading,
    error,
    refreshing,
    refreshSource,
    refreshAllSources,
    refetch,
  }
}

export default useSources
