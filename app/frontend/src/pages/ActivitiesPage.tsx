import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ActivityCard } from '../components/ActivityCard'
import { DraftBatchToolbar } from '../components/analysis/DraftBatchToolbar'
import { JobStatusBanner } from '../components/analysis/JobStatusBanner'
import { ErrorMessage } from '../components/ErrorMessage'
import { FilterBar } from '../components/FilterBar'
import { Loading } from '../components/Loading'
import { OpportunityAiFilterPanel } from '../components/OpportunityAiFilterPanel'
import { Pagination } from '../components/Pagination'
import { SearchBox } from '../components/SearchBox'
import { SortSelect } from '../components/SortSelect'
import { useAgentAnalysisJobs } from '../hooks/useAgentAnalysisJobs'
import { useActivities } from '../hooks/useActivities'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { api } from '../services/api'
import type {
  Activity,
  ActivityFilters,
  AnalysisTemplate,
  AnalysisTemplatePreviewResults,
  AgentAnalysisJobDetail,
  AgentAnalysisJobItemDetail,
  AgentAnalysisJobSummary,
  OpportunityAiFilterItem,
  OpportunityAiFilterResponse,
} from '../types'
import { DEFAULT_SORT_BY, DEFAULT_SORT_ORDER } from '../utils/constants'
import { mapTrackingStageToStatus } from '../utils/trackingStage'
import {
  getAnalysisFieldLabel,
  getAnalysisOperatorLabel,
  localizeAnalysisTemplate,
} from '../utils/analysisI18n'

type DisplayActivity = Activity & {
  ai_match_reason?: string
  ai_match_confidence?: string
  uncertainties?: string[]
}

function buildTrackingFilters(
  trackingState: string
): Pick<ActivityFilters, 'tracking_state' | 'is_tracking' | 'is_favorited'> {
  if (trackingState === 'tracked') {
    return { tracking_state: trackingState, is_tracking: true, is_favorited: undefined }
  }
  if (trackingState === 'favorited') {
    return { tracking_state: trackingState, is_tracking: true, is_favorited: true }
  }
  if (trackingState === 'untracked') {
    return { tracking_state: trackingState, is_tracking: false, is_favorited: undefined }
  }
  return { tracking_state: '', is_tracking: undefined, is_favorited: undefined }
}

type BatchTrackingAction = 'to_decide' | 'watching' | 'favorite'

async function runBatchTrackingAction(activities: Activity[], action: BatchTrackingAction) {
  if (action === 'favorite') {
    await Promise.all(
      activities.map(activity =>
        activity.is_tracking
          ? api.updateTracking(activity.id, { is_favorited: true })
          : api.createTracking(activity.id, { status: 'saved', is_favorited: true })
      )
    )
    return
  }

  const status = mapTrackingStageToStatus(action)
  await Promise.all(
    activities.map(activity =>
      activity.is_tracking
        ? api.updateTracking(activity.id, { status })
        : api.createTracking(activity.id, { status })
    )
  )
}

function cloneDraftTemplate(template: AnalysisTemplate): AnalysisTemplate {
  return {
    ...template,
    tags: [...template.tags],
    sort_fields: [...template.sort_fields],
    layers: template.layers.map(layer => ({
      ...layer,
      conditions: layer.conditions.map(condition => ({ ...condition })),
    })),
  }
}

function serializeDraftTemplate(template: AnalysisTemplate | null) {
  if (!template) {
    return null
  }

  return JSON.stringify({
    description: template.description ?? null,
    tags: template.tags,
    sort_fields: template.sort_fields,
    layers: template.layers,
  })
}

function parseDraftConditionValue(value: string) {
  const normalized = value.trim()
  if (!normalized) return null
  if (normalized === 'true') return true
  if (normalized === 'false') return false
  if (normalized === 'null') return null
  if (/^-?\d+(\.\d+)?$/.test(normalized)) return Number(normalized)
  return normalized
}

function stringifyDraftConditionValue(value: unknown) {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}

function mapAgentSnapshotStatusToActivityStatus(status?: string | null): Activity['analysis_status'] {
  if (status === 'pass') {
    return 'passed'
  }
  if (status === 'reject') {
    return 'rejected'
  }
  if (status === 'watch') {
    return 'watch'
  }
  return null
}

function pickLatestBatchJob(jobs: AgentAnalysisJobSummary[]): AgentAnalysisJobSummary | null {
  return jobs.find(job => job.scope_type === 'batch') ?? null
}

function getBatchItemsByActivity(
  job: AgentAnalysisJobDetail | null
): Record<string, AgentAnalysisJobItemDetail> {
  return Object.fromEntries((job?.items ?? []).map(item => [item.activity_id, item]))
}

function isAiFilteredActivity(
  activity: DisplayActivity
): activity is DisplayActivity & { ai_match_reason: string } {
  return typeof activity.ai_match_reason === 'string'
}

const AI_FILTER_CLIENT_LIMIT = 200

export function ActivitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { templates, defaultTemplate, createTemplate, activateTemplate } = useAnalysisTemplates()
  const {
    jobs: agentJobs,
    activeJob: activeAgentJob,
    error: agentJobsError,
    refetch: refetchAgentJobs,
    loadJob: loadAgentJob,
    createJob: createAgentJob,
  } = useAgentAnalysisJobs()
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [isApplyingBatch, setIsApplyingBatch] = useState(false)
  const [isReviewingBatch, setIsReviewingBatch] = useState(false)
  const [draftOnlyFilter, setDraftOnlyFilter] = useState(false)
  const [showAdvancedControls, setShowAdvancedControls] = useState(false)
  const [draftTemplate, setDraftTemplate] = useState<AnalysisTemplate | null>(null)
  const [draftPreview, setDraftPreview] = useState<AnalysisTemplatePreviewResults | null>(null)
  const [draftLoading, setDraftLoading] = useState(false)
  const [draftError, setDraftError] = useState<string | null>(null)
  const [isSavingDraftTemplate, setIsSavingDraftTemplate] = useState(false)
  const [isSwitchingTemplate, setIsSwitchingTemplate] = useState(false)
  const [aiQuery, setAiQuery] = useState('')
  const [aiFilterLoading, setAiFilterLoading] = useState(false)
  const [aiFilterApplied, setAiFilterApplied] = useState(false)
  const [aiFilterError, setAiFilterError] = useState<string | null>(null)
  const [aiFilterSummary, setAiFilterSummary] = useState<OpportunityAiFilterResponse | null>(null)
  const [aiFilteredItems, setAiFilteredItems] = useState<OpportunityAiFilterItem[]>([])

  const initialFilters: ActivityFilters = {
    category: searchParams.get('category') || '',
    source_id: searchParams.get('source_id') || '',
    search: searchParams.get('search') || '',
    analysis_status: searchParams.get('analysis_status') || '',
    deadline_level: searchParams.get('deadline_level') || '',
    trust_level: searchParams.get('trust_level') || '',
    prize_range: searchParams.get('prize_range') || '',
    solo_friendliness: searchParams.get('solo_friendliness') || '',
    reward_clarity: searchParams.get('reward_clarity') || '',
    effort_level: searchParams.get('effort_level') || '',
    remote_mode: searchParams.get('remote_mode') || '',
    tracking_state: searchParams.get('tracking_state') || '',
    sort_by: searchParams.get('sort_by') || DEFAULT_SORT_BY,
    sort_order: (searchParams.get('sort_order') as 'asc' | 'desc') || DEFAULT_SORT_ORDER,
    page: parseInt(searchParams.get('page') || '1', 10),
  }

  const {
    activities,
    total,
    page,
    totalPages,
    loading,
    error,
    filters,
    setFilters,
    setPage,
    refetch,
  } = useActivities({
    ...initialFilters,
    ...buildTrackingFilters(initialFilters.tracking_state || ''),
  })

  const localizedTemplates = useMemo(
    () => templates.map(template => localizeAnalysisTemplate(template)),
    [templates]
  )
  const localizedDefaultTemplate = useMemo(
    () => (defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null),
    [defaultTemplate]
  )
  const latestBatchJobSummary = useMemo(() => pickLatestBatchJob(agentJobs), [agentJobs])
  const latestBatchJob = activeAgentJob?.scope_type === 'batch' ? activeAgentJob : null
  const latestBatchBannerJob = latestBatchJob ?? latestBatchJobSummary
  const batchItemsByActivityId = useMemo(
    () => getBatchItemsByActivity(latestBatchJob),
    [latestBatchJob]
  )
  const activityIdsSignature = useMemo(
    () => activities.map(activity => activity.id).join('|'),
    [activities]
  )
  const aiCandidateSignature = useMemo(
    () =>
      JSON.stringify({
        activity_ids: activityIdsSignature,
        category: filters.category || '',
        source_id: filters.source_id || '',
        search: filters.search || '',
        analysis_status: filters.analysis_status || '',
        deadline_level: filters.deadline_level || '',
        trust_level: filters.trust_level || '',
        prize_range: filters.prize_range || '',
        solo_friendliness: filters.solo_friendliness || '',
        reward_clarity: filters.reward_clarity || '',
        effort_level: filters.effort_level || '',
        remote_mode: filters.remote_mode || '',
        tracking_state: filters.tracking_state || '',
        sort_by: filters.sort_by || DEFAULT_SORT_BY,
        sort_order: filters.sort_order || DEFAULT_SORT_ORDER,
        page: filters.page || 1,
      }),
    [
      activityIdsSignature,
      filters.analysis_status,
      filters.category,
      filters.deadline_level,
      filters.effort_level,
      filters.page,
      filters.prize_range,
      filters.remote_mode,
      filters.reward_clarity,
      filters.search,
      filters.solo_friendliness,
      filters.sort_by,
      filters.sort_order,
      filters.source_id,
      filters.tracking_state,
      filters.trust_level,
    ]
  )
  const previousAiCandidateSignatureRef = useRef(aiCandidateSignature)

  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.category) params.set('category', filters.category)
    if (filters.source_id) params.set('source_id', filters.source_id)
    if (filters.search) params.set('search', filters.search)
    if (filters.analysis_status) params.set('analysis_status', filters.analysis_status)
    if (filters.deadline_level) params.set('deadline_level', filters.deadline_level)
    if (filters.trust_level) params.set('trust_level', filters.trust_level)
    if (filters.prize_range) params.set('prize_range', filters.prize_range)
    if (filters.solo_friendliness) params.set('solo_friendliness', filters.solo_friendliness)
    if (filters.reward_clarity) params.set('reward_clarity', filters.reward_clarity)
    if (filters.effort_level) params.set('effort_level', filters.effort_level)
    if (filters.remote_mode) params.set('remote_mode', filters.remote_mode)
    if (filters.tracking_state) params.set('tracking_state', filters.tracking_state)
    if (filters.sort_by && filters.sort_by !== DEFAULT_SORT_BY) {
      params.set('sort_by', filters.sort_by)
    }
    if (filters.sort_order && filters.sort_order !== DEFAULT_SORT_ORDER) {
      params.set('sort_order', filters.sort_order)
    }
    if (filters.page && filters.page > 1) {
      params.set('page', String(filters.page))
    }
    if (params.toString() !== searchParams.toString()) {
      setSearchParams(params, { replace: true })
    }
  }, [filters, searchParams, setSearchParams])

  useEffect(() => {
    setSelectedIds(current => {
      const next = current.filter(id => activities.some(activity => activity.id === id))
      const unchanged =
        next.length === current.length && next.every((id, index) => id === current[index])
      return unchanged ? current : next
    })
  }, [activities])

  useEffect(() => {
    if (previousAiCandidateSignatureRef.current === aiCandidateSignature) {
      return
    }
    previousAiCandidateSignatureRef.current = aiCandidateSignature
    if (!aiFilterApplied && !aiFilterError && !aiFilterSummary && aiFilteredItems.length === 0) {
      return
    }
    setAiFilterApplied(false)
    setAiFilterError(null)
    setAiFilterSummary(null)
    setAiFilteredItems([])
  }, [aiCandidateSignature, aiFilterApplied, aiFilterError, aiFilterSummary, aiFilteredItems.length])

  useEffect(() => {
    if (!localizedDefaultTemplate) {
      setDraftTemplate(null)
      setDraftPreview(null)
      setDraftError(null)
      return
    }

    setDraftTemplate(current => {
      if (current?.id === localizedDefaultTemplate.id) {
        return current
      }
      return cloneDraftTemplate(localizedDefaultTemplate)
    })
    setDraftPreview(null)
    setDraftError(null)
  }, [localizedDefaultTemplate])

  useEffect(() => {
    if (!latestBatchJobSummary) {
      return
    }

    if (activeAgentJob?.id === latestBatchJobSummary.id) {
      return
    }

    void loadAgentJob(latestBatchJobSummary.id)
  }, [activeAgentJob?.id, latestBatchJobSummary, loadAgentJob])

  const selectedActivities = useMemo(
    () => activities.filter(activity => selectedIds.includes(activity.id)),
    [activities, selectedIds]
  )
  const selectedAgentItemIds = useMemo(
    () =>
      (latestBatchJob?.items ?? [])
        .filter(item => selectedIds.includes(item.activity_id))
        .map(item => item.id),
    [latestBatchJob, selectedIds]
  )

  const draftDirty = useMemo(() => {
    if (!localizedDefaultTemplate || !draftTemplate) {
      return false
    }
    return serializeDraftTemplate(draftTemplate) !== serializeDraftTemplate(localizedDefaultTemplate)
  }, [draftTemplate, localizedDefaultTemplate])

  useEffect(() => {
    if (!localizedDefaultTemplate || !draftTemplate || !draftDirty) {
      setDraftLoading(false)
      setDraftPreview(null)
      setDraftError(null)
      return
    }

    if (activities.length === 0) {
      setDraftPreview({
        template_id: `${localizedDefaultTemplate.id}-draft`,
        total: 0,
        passed: 0,
        watch: 0,
        rejected: 0,
        items: [],
      })
      return
    }

    let cancelled = false
    setDraftLoading(true)
    setDraftError(null)

    void api
      .previewDraftAnalysisTemplateResults({
        id: `${localizedDefaultTemplate.id}-draft`,
        name: draftTemplate.name,
        description: draftTemplate.description,
        tags: draftTemplate.tags,
        sort_fields: draftTemplate.sort_fields,
        layers: draftTemplate.layers,
        activity_ids: activities.map(activity => activity.id),
      })
      .then(preview => {
        if (cancelled) return
        setDraftPreview(preview)
      })
      .catch((draftPreviewError: unknown) => {
        if (cancelled) return
        const message =
          draftPreviewError instanceof Error ? draftPreviewError.message : '临时规则预览失败'
        setDraftError(message)
      })
      .finally(() => {
        if (!cancelled) {
          setDraftLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [activities, draftDirty, draftTemplate, localizedDefaultTemplate])

  const handleCategoryChange = useCallback((category: string) => {
    setFilters({ category })
  }, [setFilters])

  const handleSourceChange = useCallback((source_id: string) => {
    setFilters({ source_id })
  }, [setFilters])

  const handleSearchChange = useCallback((search: string) => {
    setFilters({ search })
  }, [setFilters])

  const handleAnalysisStatusChange = useCallback((analysis_status: string) => {
    setFilters({ analysis_status })
  }, [setFilters])

  const handleSortByChange = useCallback((sort_by: string) => {
    setFilters({ sort_by })
  }, [setFilters])

  const handleSortOrderChange = useCallback((sort_order: 'asc' | 'desc') => {
    setFilters({ sort_order })
  }, [setFilters])

  const handleDeadlineLevelChange = useCallback((deadline_level: string) => {
    setFilters({ deadline_level })
  }, [setFilters])

  const handleTrustLevelChange = useCallback((trust_level: string) => {
    setFilters({ trust_level })
  }, [setFilters])

  const handlePrizeRangeChange = useCallback((prize_range: string) => {
    setFilters({ prize_range })
  }, [setFilters])

  const handleSoloFriendlinessChange = useCallback((solo_friendliness: string) => {
    setFilters({ solo_friendliness })
  }, [setFilters])

  const handleRewardClarityChange = useCallback((reward_clarity: string) => {
    setFilters({ reward_clarity })
  }, [setFilters])

  const handleEffortLevelChange = useCallback((effort_level: string) => {
    setFilters({ effort_level })
  }, [setFilters])

  const handleRemoteModeChange = useCallback((remote_mode: string) => {
    setFilters({ remote_mode })
  }, [setFilters])

  const handleTrackingStateChange = useCallback((tracking_state: string) => {
    setFilters(buildTrackingFilters(tracking_state))
  }, [setFilters])

  const handleClearFilters = useCallback(() => {
    setFilters({
      category: '',
      source_id: '',
      search: '',
      analysis_status: '',
      deadline_level: '',
      trust_level: '',
      prize_range: '',
      solo_friendliness: '',
      reward_clarity: '',
      effort_level: '',
      remote_mode: '',
      tracking_state: '',
      is_tracking: undefined,
      is_favorited: undefined,
      sort_by: DEFAULT_SORT_BY,
      sort_order: DEFAULT_SORT_ORDER,
    })
  }, [setFilters])

  const toggleSelection = useCallback((activityId: string) => {
    setSelectedIds(current =>
      current.includes(activityId)
        ? current.filter(id => id !== activityId)
        : [...current, activityId]
    )
  }, [])

  const applyBatchAction = useCallback(
    async (action: BatchTrackingAction) => {
      if (selectedActivities.length === 0) {
        return
      }

      setIsApplyingBatch(true)
      try {
        await runBatchTrackingAction(selectedActivities, action)
        await refetch()
      } catch (batchError) {
        console.error(batchError)
      } finally {
        setIsApplyingBatch(false)
      }
    },
    [refetch, selectedActivities]
  )

  const hasActiveFilters = Boolean(
    filters.category ||
      filters.source_id ||
      filters.search ||
      filters.analysis_status ||
      filters.deadline_level ||
      filters.trust_level ||
      filters.prize_range ||
      filters.solo_friendliness ||
      filters.reward_clarity ||
      filters.effort_level ||
      filters.remote_mode ||
      filters.tracking_state
  )

  const analysisStatusOptions = [
    { value: '', label: '全部', testId: 'analysis-status-filter-cleared' },
    { value: 'passed', label: '通过', testId: 'analysis-status-filter-passed' },
    { value: 'watch', label: '待观察', testId: 'analysis-status-filter-watch' },
    { value: 'rejected', label: '淘汰', testId: 'analysis-status-filter-rejected' },
  ]

  const draftResultsById = useMemo(
    () => Object.fromEntries((draftPreview?.items ?? []).map(item => [item.activity_id, item])),
    [draftPreview]
  )

  const enrichActivity = useCallback(
    (activity: DisplayActivity): DisplayActivity => {
      const draftResult = draftResultsById[activity.id]
      const batchDraft = batchItemsByActivityId[activity.id]?.draft

      if (!draftResult && !batchDraft) {
        return activity
      }

      return {
        ...activity,
        analysis_status: draftResult
          ? (draftResult.status as Activity['analysis_status'])
          : mapAgentSnapshotStatusToActivityStatus(batchDraft?.status) ?? activity.analysis_status,
        analysis_failed_layer: draftResult?.failed_layer ?? activity.analysis_failed_layer,
        analysis_summary_reasons:
          draftResult?.summary_reasons ?? batchDraft?.reasons ?? activity.analysis_summary_reasons,
        analysis_latest_draft: batchDraft ?? activity.analysis_latest_draft,
      }
    },
    [batchItemsByActivityId, draftResultsById]
  )

  const hasAgentDraft = useCallback(
    (activity: Pick<Activity, 'id'>) => Boolean(batchItemsByActivityId[activity.id]?.draft),
    [batchItemsByActivityId]
  )

  const filterDraftOnly = useCallback(
    (items: DisplayActivity[]) => (draftOnlyFilter ? items.filter(hasAgentDraft) : items),
    [draftOnlyFilter, hasAgentDraft]
  )

  const enrichedActivities = useMemo(
    () => activities.map(activity => enrichActivity(activity)),
    [activities, enrichActivity]
  )
  const enrichedAiFilteredItems = useMemo(
    () => aiFilteredItems.map(item => enrichActivity(item)),
    [aiFilteredItems, enrichActivity]
  )
  const visibleActivities = useMemo(
    () => filterDraftOnly(enrichedActivities),
    [enrichedActivities, filterDraftOnly]
  )
  const displayedActivities = useMemo(
    () => (aiFilterApplied ? filterDraftOnly(enrichedAiFilteredItems) : visibleActivities),
    [aiFilterApplied, enrichedAiFilteredItems, filterDraftOnly, visibleActivities]
  )

  const updateDraftLayerEnabled = useCallback((layerIndex: number, enabled: boolean) => {
    setDraftTemplate(current =>
      current
        ? {
            ...current,
            layers: current.layers.map((layer, index) =>
              index === layerIndex ? { ...layer, enabled } : layer
            ),
          }
        : current
    )
  }, [])

  const updateDraftConditionEnabled = useCallback(
    (layerIndex: number, conditionIndex: number, enabled: boolean) => {
      setDraftTemplate(current =>
        current
          ? {
              ...current,
              layers: current.layers.map((layer, currentLayerIndex) =>
                currentLayerIndex === layerIndex
                  ? {
                      ...layer,
                      conditions: layer.conditions.map((condition, currentConditionIndex) =>
                        currentConditionIndex === conditionIndex ? { ...condition, enabled } : condition
                      ),
                    }
                  : layer
              ),
            }
          : current
      )
    },
    []
  )

  const updateDraftConditionValue = useCallback(
    (layerIndex: number, conditionIndex: number, value: string) => {
      setDraftTemplate(current =>
        current
          ? {
              ...current,
              layers: current.layers.map((layer, currentLayerIndex) =>
                currentLayerIndex === layerIndex
                  ? {
                      ...layer,
                      conditions: layer.conditions.map((condition, currentConditionIndex) =>
                        currentConditionIndex === conditionIndex
                          ? { ...condition, value: parseDraftConditionValue(value) }
                          : condition
                      ),
                    }
                  : layer
              ),
            }
          : current
      )
    },
    []
  )

  const resetDraftTemplate = useCallback(() => {
    if (!localizedDefaultTemplate) {
      return
    }
    setDraftTemplate(cloneDraftTemplate(localizedDefaultTemplate))
    setDraftPreview(null)
    setDraftError(null)
  }, [localizedDefaultTemplate])

  const saveDraftAsTemplate = useCallback(async () => {
    if (!draftTemplate) {
      return
    }

    const proposedName = window.prompt('新模板名称', `${draftTemplate.name} 调整版`)
    const nextName = proposedName?.trim()
    if (!nextName) {
      return
    }

    setIsSavingDraftTemplate(true)
    setDraftError(null)
    try {
      const createdTemplate = await createTemplate(nextName, draftTemplate)
      if (createdTemplate?.id) {
        await activateTemplate(createdTemplate.id)
      }
    } catch (draftSaveError) {
      const message =
        draftSaveError instanceof Error ? draftSaveError.message : '保存临时模板失败'
      setDraftError(message)
    } finally {
      setIsSavingDraftTemplate(false)
    }
  }, [activateTemplate, createTemplate, draftTemplate])

  const handleTemplateSwitch = useCallback(
    async (templateId: string) => {
      if (!templateId || templateId === localizedDefaultTemplate?.id) {
        return
      }

      setIsSwitchingTemplate(true)
      setDraftError(null)
      try {
        await activateTemplate(templateId)
      } catch (templateSwitchError) {
        const message =
          templateSwitchError instanceof Error ? templateSwitchError.message : '切换模板失败'
        setDraftError(message)
      } finally {
        setIsSwitchingTemplate(false)
      }
    },
    [activateTemplate, localizedDefaultTemplate?.id]
  )

  const handleBatchApprove = useCallback(async () => {
    if (selectedAgentItemIds.length === 0) {
      return
    }

    setIsReviewingBatch(true)
    try {
      await api.approveAgentAnalysisBatch(selectedAgentItemIds, {
        review_note: '机会池批量通过',
      })
      await Promise.all([refetch(), refetchAgentJobs()])
      if (latestBatchJobSummary) {
        await loadAgentJob(latestBatchJobSummary.id)
      }
    } catch (batchError) {
      console.error(batchError)
    } finally {
      setIsReviewingBatch(false)
    }
  }, [latestBatchJobSummary, loadAgentJob, refetch, refetchAgentJobs, selectedAgentItemIds])

  const handleBatchReject = useCallback(async () => {
    if (selectedAgentItemIds.length === 0) {
      return
    }

    setIsReviewingBatch(true)
    try {
      await api.rejectAgentAnalysisBatch(selectedAgentItemIds, {
        review_note: '机会池批量拒绝',
      })
      await Promise.all([refetch(), refetchAgentJobs()])
      if (latestBatchJobSummary) {
        await loadAgentJob(latestBatchJobSummary.id)
      }
    } catch (batchError) {
      console.error(batchError)
    } finally {
      setIsReviewingBatch(false)
    }
  }, [latestBatchJobSummary, loadAgentJob, refetch, refetchAgentJobs, selectedAgentItemIds])

  const handleBatchDeepResearch = useCallback(async () => {
    if (selectedIds.length === 0) {
      return
    }

    setIsReviewingBatch(true)
    try {
      await createAgentJob({
        scope_type: 'batch',
        trigger_type: 'manual',
        activity_ids: selectedIds,
        template_id: localizedDefaultTemplate?.id,
      })
      await refetchAgentJobs()
    } catch (batchError) {
      console.error(batchError)
    } finally {
      setIsReviewingBatch(false)
    }
  }, [createAgentJob, localizedDefaultTemplate?.id, refetchAgentJobs, selectedIds])

  const handleRunAiFilter = useCallback(async () => {
    if (!aiQuery.trim()) {
      setAiFilterError('请输入 AI 精筛条件。')
      return
    }

    if (total > AI_FILTER_CLIENT_LIMIT) {
      setAiFilterError('当前候选机会过多，请先缩小固定筛选范围后再进行 AI 精筛。')
      setAiFilterApplied(false)
      setAiFilterSummary(null)
      setAiFilteredItems([])
      return
    }

    setAiFilterLoading(true)
    setAiFilterError(null)
    try {
      const result = await api.aiFilterActivities({
        base_filters: filters,
        query: aiQuery.trim(),
      })
      setAiFilterSummary(result)
      setAiFilteredItems(result.items)
      setAiFilterApplied(true)
    } catch (aiError) {
      const message = aiError instanceof Error ? aiError.message : 'AI 精筛暂时不可用，请稍后重试。'
      setAiFilterError(message)
      setAiFilterApplied(false)
      setAiFilterSummary(null)
      setAiFilteredItems([])
    } finally {
      setAiFilterLoading(false)
    }
  }, [aiQuery, filters, total])

  const handleClearAiFilter = useCallback(() => {
    setAiQuery('')
    setAiFilterApplied(false)
    setAiFilterError(null)
    setAiFilterSummary(null)
    setAiFilteredItems([])
  }, [])

  const emptyStateTitle = aiFilterApplied
    ? 'AI 精筛后没有找到符合条件的机会'
    : '当前筛选条件下还没有机会'
  const emptyStateDescription = aiFilterApplied
    ? '可以调整描述后重新精筛，或先清除 AI 条件回到固定筛选结果。'
    : '可以调整固定筛选条件，继续缩小或放宽范围。'
  const emptyStateActionLabel = aiFilterApplied ? '清除 AI 条件' : '清除筛选'
  const handleEmptyStateClear = aiFilterApplied ? handleClearAiFilter : handleClearFilters
  const canClearEmptyState = aiFilterApplied || hasActiveFilters || draftOnlyFilter

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.24em] text-sky-700">机会池工作台</div>
          <h1 className="text-3xl font-bold text-gray-900">先筛出值得投入的机会，再批量推进</h1>
          <p className="mt-2 text-sm text-gray-600">这里不是信息广场，而是你的机会决策台。先筛、再判、再批量推进。</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
          <span>{total} 个机会</span>
          <span>{selectedIds.length} 个已选</span>
          <button
            type="button"
            onClick={() => setShowAdvancedControls(current => !current)}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900"
          >
            {showAdvancedControls ? '收起高级调整' : '高级调整'}
          </button>
        </div>
      </div>

      <div
        className={`grid gap-6 ${
          showAdvancedControls ? 'grid-cols-1 xl:grid-cols-[320px_1fr]' : 'grid-cols-1'
        }`}
      >
        {draftTemplate && showAdvancedControls ? (
          <aside
            data-testid="opportunity-pool-rules-panel"
            className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">高级调整</div>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">边调规则，边看结果</h2>
              <p className="mt-2 text-sm text-slate-600">
                这里只影响当前机会池预览，不会直接覆盖默认模板。
              </p>
            </div>

            <div className="space-y-3">
              {draftTemplate.layers.map((layer, layerIndex) => (
                <div key={layer.key} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <label className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{layer.label}</div>
                      <div className="text-xs text-slate-500">{getAnalysisFieldLabel(layer.key)}</div>
                    </div>
                    <input
                      type="checkbox"
                      aria-label={`启用规则层：${layer.label}`}
                      checked={layer.enabled}
                      data-testid={`opportunity-pool-layer-enabled-${draftTemplate.id}-${layerIndex}`}
                      onChange={event => updateDraftLayerEnabled(layerIndex, event.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                    />
                  </label>

                  <div className="mt-3 space-y-3">
                    {layer.conditions.map((condition, conditionIndex) => (
                      <div
                        key={`${layer.key}-${condition.key}-${conditionIndex}`}
                        className="rounded-xl bg-white p-3"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="text-sm font-medium text-slate-900">{condition.label}</div>
                            <div className="text-xs text-slate-500">
                              {getAnalysisFieldLabel(condition.key)} ·{' '}
                              {getAnalysisOperatorLabel(condition.operator)}
                            </div>
                          </div>
                          <input
                            type="checkbox"
                            aria-label={`启用条件：${condition.label}`}
                            checked={condition.enabled}
                            data-testid={`opportunity-pool-condition-enabled-${draftTemplate.id}-${layerIndex}-${conditionIndex}`}
                            onChange={event =>
                              updateDraftConditionEnabled(layerIndex, conditionIndex, event.target.checked)
                            }
                            className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                          />
                        </div>

                        <input
                          type="text"
                          value={stringifyDraftConditionValue(condition.value)}
                          data-testid={`opportunity-pool-condition-value-${draftTemplate.id}-${layerIndex}-${conditionIndex}`}
                          onChange={event =>
                            updateDraftConditionValue(layerIndex, conditionIndex, event.target.value)
                          }
                          className="mt-3 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-sky-300"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </aside>
        ) : null}

        <div className="space-y-6">
          <div className="space-y-4 rounded-xl bg-white p-4 shadow">
            {latestBatchBannerJob ? (
              <JobStatusBanner job={latestBatchBannerJob} title="最近一轮批量复核" />
            ) : null}

            {latestBatchBannerJob ? (
              <DraftBatchToolbar
                selectedCount={selectedAgentItemIds.length}
                busy={isReviewingBatch}
                onApprove={() => void handleBatchApprove()}
                onReject={() => void handleBatchReject()}
                onDeepResearch={() => void handleBatchDeepResearch()}
              />
            ) : null}

            {agentJobsError ? <ErrorMessage message={agentJobsError} /> : null}

            {localizedDefaultTemplate ? (
              <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 lg:flex-row lg:items-center lg:justify-between">
                <div
                  data-testid="opportunity-pool-active-template"
                  className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-800"
                >
                  当前 AI 模板: {localizedDefaultTemplate.name}
                </div>
                <label className="flex flex-col gap-1 text-sm text-slate-600">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    模板切换
                  </span>
                  <select
                    value={localizedDefaultTemplate.id}
                    data-testid="opportunity-pool-template-switcher"
                    disabled={isSwitchingTemplate}
                    onChange={event => void handleTemplateSwitch(event.target.value)}
                    className="min-w-[220px] rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-sky-300 disabled:cursor-not-allowed disabled:bg-slate-100"
                  >
                    {localizedTemplates.map(template => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : null}

            {localizedDefaultTemplate ? (
              <div
                data-testid="opportunity-pool-draft-banner"
                className={`flex flex-col gap-3 rounded-2xl border px-4 py-3 text-sm md:flex-row md:items-center md:justify-between ${
                  draftDirty
                    ? 'border-amber-200 bg-amber-50 text-amber-900'
                    : 'border-slate-200 bg-slate-50 text-slate-700'
                }`}
              >
                <div>
                  <div className="font-medium">
                    {draftDirty ? '临时调整已生效' : `当前模板 ${localizedDefaultTemplate.name}`}
                  </div>
                  <div className="mt-1 text-xs">
                    {draftDirty
                      ? '规则调整只影响当前机会池预览，确认有效后再另存为新模板。'
                      : '打开高级调整后，可以临时微调硬门槛和筛选条件，不会直接覆盖模板。'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {isSwitchingTemplate ? (
                    <span className="text-xs text-slate-500">正在切换模板...</span>
                  ) : null}
                  {draftLoading ? (
                    <span className="text-xs text-slate-500">正在刷新预览...</span>
                  ) : null}
                  {draftDirty ? (
                    <button
                      type="button"
                      data-testid="save-draft-as-template-button"
                      disabled={isSavingDraftTemplate}
                      onClick={() => void saveDraftAsTemplate()}
                      className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:border-emerald-400 hover:text-emerald-800 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
                    >
                      {isSavingDraftTemplate ? '正在另存...' : '另存为新模板'}
                    </button>
                  ) : null}
                  {draftDirty ? (
                    <button
                      type="button"
                      data-testid="opportunity-pool-reset-draft"
                      onClick={resetDraftTemplate}
                      className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
                    >
                      恢复默认
                    </button>
                  ) : null}
                </div>
              </div>
            ) : null}

            {draftPreview ? (
              <div
                data-testid="opportunity-pool-draft-preview"
                className="grid grid-cols-2 gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-4"
              >
                <div className="rounded-xl bg-white p-3">
                  <div className="text-xs text-slate-500">当前页总数</div>
                  <div className="mt-1 text-xl font-semibold text-slate-900">{draftPreview.total}</div>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <div className="text-xs text-emerald-600">通过</div>
                  <div className="mt-1 text-xl font-semibold text-emerald-700">{draftPreview.passed}</div>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <div className="text-xs text-amber-600">待观察</div>
                  <div className="mt-1 text-xl font-semibold text-amber-700">{draftPreview.watch}</div>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <div className="text-xs text-rose-600">淘汰</div>
                  <div className="mt-1 text-xl font-semibold text-rose-700">{draftPreview.rejected}</div>
                </div>
              </div>
            ) : null}

            {draftError ? <ErrorMessage message={draftError} /> : null}

            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
                <SearchBox value={filters.search || ''} onChange={handleSearchChange} />
                <SortSelect
                  sortBy={filters.sort_by || DEFAULT_SORT_BY}
                  sortOrder={filters.sort_order || DEFAULT_SORT_ORDER}
                  onSortByChange={handleSortByChange}
                  onSortOrderChange={handleSortOrderChange}
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  data-testid="agent-analysis-filter-draft-only"
                  onClick={() => setDraftOnlyFilter(current => !current)}
                  className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                    draftOnlyFilter
                      ? 'border-sky-300 bg-sky-50 text-sky-800'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900'
                  }`}
                >
                  {draftOnlyFilter ? '只看草稿判断：已开启' : '只看草稿判断'}
                </button>

                {selectedIds.length > 0 ? (
                  <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-sky-100 bg-sky-50 px-3 py-2">
                    <span className="text-sm text-sky-800">已选中 {selectedIds.length} 条，直接推进到下一步</span>
                    <button
                      type="button"
                      data-testid="batch-track-button"
                      disabled={isApplyingBatch}
                      onClick={() => void applyBatchAction('to_decide')}
                      className="rounded-full bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                    >
                      批量加入待判断

                    </button>
                    <button
                      type="button"
                      data-testid="batch-favorite-button"
                      disabled={isApplyingBatch}
                      onClick={() => void applyBatchAction('favorite')}
                      className="rounded-full border border-sky-200 bg-white px-4 py-2 text-sm font-medium text-sky-700 transition hover:border-sky-300 hover:bg-sky-100 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
                    >
                      批量收藏

                    </button>
                    <button
                      type="button"
                      disabled={isApplyingBatch}
                      onClick={() => void applyBatchAction('watching')}
                      className="rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
                    >
                      批量标记重点

                    </button>
                  </div>
                ) : null}
              </div>
            </div>

            <FilterBar
              category={filters.category || ''}
              sourceId={filters.source_id || ''}
              deadlineLevel={filters.deadline_level || ''}
              prizeRange={filters.prize_range || ''}
              soloFriendliness={filters.solo_friendliness || ''}
              rewardClarity={filters.reward_clarity || ''}
              effortLevel={filters.effort_level || ''}
              trustLevel={filters.trust_level || ''}
              remoteMode={filters.remote_mode || ''}
              trackingState={filters.tracking_state || ''}
              onCategoryChange={handleCategoryChange}
              onSourceChange={handleSourceChange}
              onDeadlineLevelChange={handleDeadlineLevelChange}
              onPrizeRangeChange={handlePrizeRangeChange}
              onSoloFriendlinessChange={handleSoloFriendlinessChange}
              onRewardClarityChange={handleRewardClarityChange}
              onEffortLevelChange={handleEffortLevelChange}
              onTrustLevelChange={handleTrustLevelChange}
              onRemoteModeChange={handleRemoteModeChange}
              onTrackingStateChange={handleTrackingStateChange}
              onClear={handleClearFilters}
            />

            <OpportunityAiFilterPanel
              value={aiQuery}
              loading={aiFilterLoading}
              error={aiFilterError}
              summary={aiFilterSummary}
              onChange={setAiQuery}
              onSubmit={() => void handleRunAiFilter()}
              onClear={handleClearAiFilter}
            />

            <div className="flex flex-wrap items-center gap-2" data-testid="analysis-status-filters">
              {analysisStatusOptions.map(option => {
                const active = (filters.analysis_status || '') === option.value
                return (
                  <button
                    key={option.testId}
                    type="button"
                    aria-pressed={active}
                    data-testid={option.testId}
                    onClick={() => handleAnalysisStatusChange(option.value)}
                    className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
                      active
                        ? 'bg-slate-900 text-white'
                        : 'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900'
                    }`}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
            {aiFilterApplied ? '当前为 AI 精筛结果，仅保留符合条件的机会。' : '当前为固定筛选结果。'}
          </div>

          {loading ? (
            <Loading text="加载机会池中..." />
          ) : error ? (
            <ErrorMessage message={error} onRetry={refetch} />
          ) : displayedActivities.length === 0 ? (
            <div className="rounded-xl bg-white py-14 text-center shadow">
              <div className="mb-4 text-4xl text-slate-300">◌</div>
              <p className="text-gray-700">{emptyStateTitle}</p>
              <p className="mt-2 text-sm text-gray-500">{emptyStateDescription}</p>
              {canClearEmptyState ? (
                <button
                  onClick={handleEmptyStateClear}
                  className="mt-4 text-sm text-primary-600 underline hover:text-primary-700"
                >
                  {emptyStateActionLabel}
                </button>
              ) : null}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {displayedActivities.map(activity => (
                  <div key={activity.id} className="relative">
                    <label className="absolute right-3 top-3 z-10 flex items-center gap-2 rounded-full bg-white/95 px-3 py-1 text-xs font-medium text-gray-700 shadow">
                      <input
                        type="checkbox"
                        aria-label={`选择机会：${activity.title}`}
                        checked={selectedIds.includes(activity.id)}
                        onChange={() => toggleSelection(activity.id)}
                        data-testid={`select-activity-${activity.id.split('-').pop() || activity.id}`}
                        className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      选择
                    </label>
                    {isAiFilteredActivity(activity) ? (
                      <div className="mb-2 rounded-2xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-800">
                        {activity.ai_match_reason}
                      </div>
                    ) : null}
                    <ActivityCard activity={activity} />
                  </div>
                ))}
              </div>

              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default ActivitiesPage
