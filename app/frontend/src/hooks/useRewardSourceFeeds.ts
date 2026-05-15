import { useCallback, useEffect, useMemo, useState } from 'react'
import { rewardOpportunityApi } from '../services/rewardOpportunityApi'
import type {
  RewardDiscoveryIgnoreItem,
  RewardOpportunityOperationsResponse,
  RewardOpportunitySyncResponse,
  RewardSourceDiscoveryItem,
  RewardSourceFeedItem,
  RewardSourceSyncResult,
} from '../types'

function sortSources(items: RewardSourceFeedItem[]): RewardSourceFeedItem[] {
  const rank = (item: RewardSourceFeedItem): number => {
    if (item.pause_mode === 'suggested') return 0
    if (item.cold_start_status === 'cold_start_failed') return 1
    if ((item.consecutive_failures ?? 0) >= 2) return 2
    if (item.health_level === 'cold') return 3
    if (item.health_level === 'risky') return 4
    if (item.is_paused) return 6
    if (item.health_level === 'watch') return 5
    return 5
  }

  return [...items].sort((a, b) => {
    const rankDiff = rank(a) - rank(b)
    if (rankDiff !== 0) return rankDiff
    const scoreDiff = (a.health_score ?? 0) - (b.health_score ?? 0)
    if (scoreDiff !== 0) return scoreDiff
    return a.created_at.localeCompare(b.created_at)
  })
}

export function useRewardSourceFeeds() {
  const [operations, setOperations] = useState<RewardOpportunityOperationsResponse | null>(null)
  const [discoveredSources, setDiscoveredSources] = useState<RewardSourceDiscoveryItem[]>([])
  const [ignoredItems, setIgnoredItems] = useState<RewardDiscoveryIgnoreItem[]>([])
  const [queryTemplateDraft, setQueryTemplateDraft] = useState('')
  const [failureFilter, setFailureFilter] = useState('all')
  const [actionFilter, setActionFilter] = useState('all')
  const [discovering, setDiscovering] = useState(false)
  const [importingUrl, setImportingUrl] = useState<string | null>(null)
  const [rerunningSourceId, setRerunningSourceId] = useState<string | null>(null)
  const [togglingSourceId, setTogglingSourceId] = useState<string | null>(null)
  const [actionSourceId, setActionSourceId] = useState<string | null>(null)
  const [savingTemplates, setSavingTemplates] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [lastSyncResult, setLastSyncResult] = useState<RewardOpportunitySyncResponse | null>(null)
  const [lastSingleSyncResult, setLastSingleSyncResult] = useState<RewardSourceSyncResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadOperations = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await rewardOpportunityApi.getOperations()
      setOperations({ ...response, sources: sortSources(response.sources) })
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载奖励活动运行面板失败')
      setOperations(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadOperations()
  }, [loadOperations])

  const loadDiscovery = useCallback(async () => {
    setDiscovering(true)
    try {
      const response = await rewardOpportunityApi.getSourceDiscovery()
      setDiscoveredSources(response.items)
      setIgnoredItems(response.ignored_items ?? [])
      setQueryTemplateDraft((response.query_templates ?? []).join('\n'))
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载来源发现候选失败')
      setDiscoveredSources([])
      setIgnoredItems([])
    } finally {
      setDiscovering(false)
    }
  }, [])

  useEffect(() => {
    void loadDiscovery()
  }, [loadDiscovery])

  const sources = useMemo(() => {
    const current = operations?.sources ?? []
    return current.filter(source => {
      const failureMatch = failureFilter === 'all' || source.current_failure_category === failureFilter
      const actionMatch = actionFilter === 'all' || source.recommended_action === actionFilter
      return failureMatch && actionMatch
    })
  }, [operations?.sources, failureFilter, actionFilter])

  const recentJobs = operations?.recent_jobs ?? []
  const failedJobs = useMemo(() => {
    const current = operations?.failed_jobs ?? []
    return current.filter(job => {
      const failureMatch = failureFilter === 'all' || job.failure_category === failureFilter
      const actionMatch = actionFilter === 'all' || job.recommended_action === actionFilter
      return failureMatch && actionMatch
    })
  }, [operations?.failed_jobs, failureFilter, actionFilter])

  const syncSources = useCallback(async () => {
    setSyncing(true)
    setError(null)
    try {
      const response = await rewardOpportunityApi.syncSources()
      setLastSyncResult(response)
      await loadOperations()
      return response
    } catch (err) {
      setError(err instanceof Error ? err.message : '同步来源失败')
      throw err
    } finally {
      setSyncing(false)
    }
  }, [loadOperations])

  const rerunSource = useCallback(
    async (sourceFeedId: string) => {
      setRerunningSourceId(sourceFeedId)
      setError(null)
      try {
        const response = await rewardOpportunityApi.syncSingleSource(sourceFeedId)
        setLastSingleSyncResult(response)
        await loadOperations()
        return response
      } catch (err) {
        setError(err instanceof Error ? err.message : '单源重跑失败')
        throw err
      } finally {
        setRerunningSourceId(null)
      }
    },
    [loadOperations]
  )

  const toggleSourcePaused = useCallback(
    async (sourceFeedId: string, paused: boolean) => {
      setTogglingSourceId(sourceFeedId)
      setError(null)
      try {
        if (paused) {
          await rewardOpportunityApi.pauseSource(sourceFeedId)
        } else {
          await rewardOpportunityApi.resumeSource(sourceFeedId)
        }
        await loadOperations()
      } catch (err) {
        setError(err instanceof Error ? err.message : paused ? '停用来源失败' : '恢复来源失败')
        throw err
      } finally {
        setTogglingSourceId(null)
      }
    },
    [loadOperations]
  )

  const executeRecommendedAction = useCallback(
    async (sourceFeedId: string, action: string) => {
      setActionSourceId(sourceFeedId)
      setError(null)
      try {
        const response = await rewardOpportunityApi.executeRecommendedAction(sourceFeedId, action)
        if ('job_id' in response) {
          setLastSingleSyncResult(response)
        }
        await loadOperations()
        return response
      } catch (err) {
        setError(err instanceof Error ? err.message : '执行建议动作失败')
        throw err
      } finally {
        setActionSourceId(null)
      }
    },
    [loadOperations]
  )

  const importDiscoveredSource = useCallback(
    async (item: RewardSourceDiscoveryItem) => {
      setImportingUrl(item.entry_url)
      setError(null)
      try {
        const created = await rewardOpportunityApi.importDiscoveredSource({
          name: item.name,
          entry_url: item.entry_url,
          source_type: item.source_type,
          source_platform: item.source_platform,
          discovery_queries: item.discovery_queries,
        })
        setLastSingleSyncResult(created.import_preview ?? null)
        await loadOperations()
        await loadDiscovery()
        return created
      } catch (err) {
        setError(err instanceof Error ? err.message : '导入来源失败')
        throw err
      } finally {
        setImportingUrl(null)
      }
    },
    [loadDiscovery, loadOperations]
  )

  const ignoreDiscoveredSource = useCallback(
    async (item: RewardSourceDiscoveryItem) => {
      setImportingUrl(item.entry_url)
      setError(null)
      try {
        await rewardOpportunityApi.ignoreDiscoveredSource({
          dedupe_key: item.dedupe_key || item.entry_url,
          entry_url: item.entry_url,
        })
        await loadDiscovery()
      } catch (err) {
        setError(err instanceof Error ? err.message : '忽略来源候选失败')
        throw err
      } finally {
        setImportingUrl(null)
      }
    },
    [loadDiscovery]
  )

  const unignoreDiscoveredSource = useCallback(
    async (item: RewardDiscoveryIgnoreItem) => {
      setImportingUrl(item.entry_url)
      setError(null)
      try {
        await rewardOpportunityApi.unignoreDiscoveredSource({
          dedupe_key: item.dedupe_key,
          entry_url: item.entry_url,
        })
        await loadDiscovery()
      } catch (err) {
        setError(err instanceof Error ? err.message : '恢复来源候选失败')
        throw err
      } finally {
        setImportingUrl(null)
      }
    },
    [loadDiscovery]
  )

  const saveQueryTemplates = useCallback(async () => {
    setSavingTemplates(true)
    setError(null)
    try {
      const normalized = queryTemplateDraft
        .split('\n')
        .map(item => item.trim())
        .filter(Boolean)
      const response = await rewardOpportunityApi.updateScoutSettings({ query_templates: normalized })
      setQueryTemplateDraft(response.query_templates.join('\n'))
      await loadDiscovery()
      return response
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存 Scout 模板失败')
      throw err
    } finally {
      setSavingTemplates(false)
    }
  }, [loadDiscovery, queryTemplateDraft])

  return {
    sources,
    recentJobs,
    failedJobs,
    discoveredSources,
    ignoredItems,
    failureCategoryCounts: operations?.failure_category_counts ?? {},
    recommendedActionCounts: operations?.recommended_action_counts ?? {},
    queryTemplateDraft,
    setQueryTemplateDraft,
    failureFilter,
    setFailureFilter,
    actionFilter,
    setActionFilter,
    discovering,
    importingUrl,
    rerunningSourceId,
    togglingSourceId,
    actionSourceId,
    savingTemplates,
    syncing,
    lastSyncResult,
    lastSingleSyncResult,
    loading,
    error,
    reload: loadOperations,
    reloadDiscovery: loadDiscovery,
    syncSources,
    rerunSource,
    toggleSourcePaused,
    executeRecommendedAction,
    importDiscoveredSource,
    ignoreDiscoveredSource,
    unignoreDiscoveredSource,
    saveQueryTemplates,
  }
}

export default useRewardSourceFeeds
