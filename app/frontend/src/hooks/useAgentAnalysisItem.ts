import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type {
  AgentAnalysisJobCreateRequest,
  AgentAnalysisJobDetail,
  AgentAnalysisJobItemDetail,
} from '../types'

type AgentAnalysisRerunOptions = Omit<
  AgentAnalysisJobCreateRequest,
  'scope_type' | 'trigger_type' | 'activity_ids'
>

interface UseAgentAnalysisItemResult {
  item: AgentAnalysisJobItemDetail | null
  lastJob: AgentAnalysisJobDetail | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  rerunItem: (options?: AgentAnalysisRerunOptions) => Promise<AgentAnalysisJobDetail | null>
}

export function useAgentAnalysisItem(itemId?: string | null): UseAgentAnalysisItemResult {
  const skipNextRefreshRef = useRef(false)
  const [resolvedItemId, setResolvedItemId] = useState<string | null>(itemId ?? null)
  const [item, setItem] = useState<AgentAnalysisJobItemDetail | null>(null)
  const [lastJob, setLastJob] = useState<AgentAnalysisJobDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setResolvedItemId(itemId ?? null)
  }, [itemId])

  const refresh = useCallback(async () => {
    if (!resolvedItemId) {
      setItem(null)
      return
    }

    if (skipNextRefreshRef.current) {
      skipNextRefreshRef.current = false
      return
    }

    setLoading(true)
    setError(null)
    try {
      const detail = await api.getAgentAnalysisItem(resolvedItemId)
      setItem(detail)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load agent analysis item'
      setError(message)
      setItem(null)
    } finally {
      setLoading(false)
    }
  }, [resolvedItemId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const rerunItem = useCallback(
    async (options: AgentAnalysisRerunOptions = {}): Promise<AgentAnalysisJobDetail | null> => {
      if (!item) {
        setError('No agent analysis item is loaded')
        return null
      }

      setError(null)
      try {
        const created = await api.createAgentAnalysisJob({
          scope_type: 'single',
          trigger_type: 'manual',
          activity_ids: [item.activity_id],
          ...options,
        })
        setLastJob(created)
        const latestItem = created.items[0] ?? null
        if (latestItem) {
          setItem(latestItem)
          skipNextRefreshRef.current = true
          setResolvedItemId(latestItem.id)
        }
        return created
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to rerun agent analysis item'
        setError(message)
        return null
      }
    },
    [item]
  )

  return {
    item,
    lastJob,
    loading,
    error,
    refetch: refresh,
    rerunItem,
  }
}

export default useAgentAnalysisItem
