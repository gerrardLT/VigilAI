import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AgentVerdictCard } from '../components/analysis/AgentVerdictCard'
import { EvidencePanel } from '../components/analysis/EvidencePanel'
import { ExecutionTracePanel } from '../components/analysis/ExecutionTracePanel'
import { ReviewActionBar } from '../components/analysis/ReviewActionBar'
import { StructuredFactorCard } from '../components/analysis/StructuredFactorCard'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useAgentAnalysisReview } from '../hooks/useAgentAnalysisReview'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { api } from '../services/api'
import type { ActivityDetail, AgentAnalysisJobDetail, AgentAnalysisJobItemDetail, TrackingState } from '../types'
import { CATEGORY_COLOR_MAP, CATEGORY_ICON_MAP } from '../utils/constants'
import { daysUntil, formatDateOnly, formatDateTime, isExpired } from '../utils/formatDate'
import { CATEGORY_LABELS } from '../types'
import {
  getAnalysisFieldLabel,
  getAnalysisStatusLabel,
  getTrackingStatusLabel,
  getTrustLevelLabel,
  localizeAnalysisTemplate,
  localizeAnalysisText,
} from '../utils/analysisI18n'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'

const TRUST_STYLES = {
  high: 'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-rose-100 text-rose-700',
} as const

const DEADLINE_STYLES = {
  urgent: 'bg-rose-100 text-rose-700',
  soon: 'bg-amber-100 text-amber-700',
  upcoming: 'bg-sky-100 text-sky-700',
  later: 'bg-slate-100 text-slate-700',
  none: 'bg-gray-100 text-gray-600',
  expired: 'bg-gray-200 text-gray-700',
} as const

const DEADLINE_LABELS = {
  urgent: '紧急截止',
  soon: '即将截止',
  upcoming: '近期开放',
  later: '后续关注',
  none: '无截止信息',
  expired: '已截止',
} as const

const ANALYSIS_STATUS_STYLES = {
  passed: 'bg-emerald-100 text-emerald-700',
  watch: 'bg-amber-100 text-amber-700',
  rejected: 'bg-rose-100 text-rose-700',
} as const

const LAYER_DECISION_STYLES = {
  passed: 'bg-emerald-100 text-emerald-700',
  borderline: 'bg-amber-100 text-amber-700',
  failed: 'bg-rose-100 text-rose-700',
} as const

const LAYER_DECISION_LABELS = {
  passed: '通过',
  borderline: '待观察',
  failed: '淘汰',
} as const

const FIELD_LABELS: Record<string, string> = {
  title: '标题',
  description: '描述',
  full_content: '正文',
  category: '类别',
  location: '地点',
  organizer: '主办方',
  image_url: '封面',
  status: '状态',
  tags: '标签',
  deadline: '截止时间',
  prize: '奖励',
}

type DetailAction = 'track' | 'favorite' | 'plan' | 'digest'

interface TrackingPlanForm {
  status: TrackingState['status']
  next_action: string
  notes: string
  remind_at: string
}

function toDateTimeLocalValue(value?: string | null) {
  if (!value) {
    return ''
  }

  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) {
    return value
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(0, 16)
  }

  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

function buildTrackingPlanForm(tracking: TrackingState | null, isTracking: boolean): TrackingPlanForm {
  return {
    status: tracking?.status ?? (isTracking ? 'saved' : 'tracking'),
    next_action: localizeAnalysisText(tracking?.next_action),
    notes: localizeAnalysisText(tracking?.notes),
    remind_at: toDateTimeLocalValue(tracking?.remind_at),
  }
}

function normalizeTextField(value: string) {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function selectAgentAnalysisItem(
  job: AgentAnalysisJobDetail,
  activityId: string
): AgentAnalysisJobItemDetail | null {
  return job.items.find(item => item.activity_id === activityId) ?? job.items[0] ?? null
}

export function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { defaultTemplate } = useAnalysisTemplates()
  const { approveItem, rejectItem, reviewing, error: reviewError } = useAgentAnalysisReview()
  const localizedDefaultTemplate = defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null
  const [activity, setActivity] = useState<ActivityDetail | null>(null)
  const [tracking, setTracking] = useState<TrackingState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<DetailAction | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [planForm, setPlanForm] = useState<TrackingPlanForm>(() => buildTrackingPlanForm(null, false))
  const [agentJob, setAgentJob] = useState<AgentAnalysisJobDetail | null>(null)
  const [agentItem, setAgentItem] = useState<AgentAnalysisJobItemDetail | null>(null)
  const [agentLoading, setAgentLoading] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [agentRunBusy, setAgentRunBusy] = useState(false)
  const trackingReadyRef = useRef(false)

  useEffect(() => {
    if (!id) return

    const fetchActivity = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await api.getActivity(id)
        const isTracking = Boolean(data.tracking || data.is_tracking)
        setActivity(data)
        setTracking(data.tracking ?? null)
        setPlanForm(buildTrackingPlanForm(data.tracking ?? null, isTracking))
        trackingReadyRef.current = isTracking
      } catch (err) {
        const message = err instanceof Error ? err.message : '获取活动详情失败'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    void fetchActivity()
  }, [id])

  useEffect(() => {
    if (!activity?.analysis_current_run_id || !activity.id) {
      setAgentJob(null)
      setAgentItem(null)
      setAgentError(null)
      setAgentLoading(false)
      return
    }

    const fetchAgentJob = async () => {
      setAgentLoading(true)
      setAgentError(null)

      try {
        const job = await api.getAgentAnalysisJob(activity.analysis_current_run_id as string)
        setAgentJob(job)
        setAgentItem(selectAgentAnalysisItem(job, activity.id))
      } catch (err) {
        const message = err instanceof Error ? err.message : '加载 agent analysis draft 失败'
        setAgentError(message)
        setAgentJob(null)
        setAgentItem(null)
      } finally {
        setAgentLoading(false)
      }
    }

    void fetchAgentJob()
  }, [activity?.analysis_current_run_id, activity?.id])

  const applyTrackingState = (nextTracking: TrackingState) => {
    trackingReadyRef.current = true
    setTracking(nextTracking)
    setPlanForm(buildTrackingPlanForm(nextTracking, true))
    setActivity(prev =>
      prev
        ? {
            ...prev,
            tracking: nextTracking,
            is_tracking: true,
            is_favorited: nextTracking.is_favorited,
          }
        : prev
    )
  }

  const handlePlanChange = <K extends keyof TrackingPlanForm>(key: K, value: TrackingPlanForm[K]) => {
    setPlanForm(prev => ({
      ...prev,
      [key]: value,
    }))
  }

  const handleTrack = async () => {
    if (!id || !activity) return

    setActionLoading('track')
    setActionError(null)

    try {
      trackingReadyRef.current = true
      setActivity(prev => (prev ? { ...prev, is_tracking: true } : prev))

      const nextTracking = tracking
        ? await api.updateTracking(id, { status: tracking.status === 'tracking' ? 'saved' : 'tracking' })
        : await api.createTracking(id, { status: 'tracking' })

      applyTrackingState(nextTracking)
      setToast({ type: 'success', message: '已加入跟进列表' })
    } catch (err) {
      const message = err instanceof Error ? err.message : '加入跟进失败'
      setActionError(message)
      setToast({ type: 'error', message })
    } finally {
      setActionLoading(null)
    }
  }

  const handleFavorite = async () => {
    if (!id || !activity) return

    setActionLoading('favorite')
    setActionError(null)

    try {
      if (!trackingReadyRef.current) {
        const created = await api.createTracking(id, { status: 'tracking' })
        applyTrackingState(created)
      }

      const updated = await api.updateTracking(id, { is_favorited: !activity.is_favorited })
      applyTrackingState(updated)
      setToast({
        type: 'success',
        message: updated.is_favorited ? '已加入收藏' : '已取消收藏',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新收藏失败'
      setActionError(message)
      setToast({ type: 'error', message })
    } finally {
      setActionLoading(null)
    }
  }

  const handleSavePlan = async () => {
    if (!id || !activity) return

    setActionLoading('plan')
    setActionError(null)

    const payload = {
      status: planForm.status,
      next_action: normalizeTextField(planForm.next_action),
      notes: normalizeTextField(planForm.notes),
      remind_at: planForm.remind_at || null,
    }

    try {
      const nextTracking =
        trackingReadyRef.current || tracking || activity.is_tracking
          ? await api.updateTracking(id, payload)
          : await api.createTracking(id, payload)

      applyTrackingState(nextTracking)
      setToast({ type: 'success', message: '跟进计划已保存' })
    } catch (err) {
      const message = err instanceof Error ? err.message : '保存跟进计划失败'
      setActionError(message)
      setToast({ type: 'error', message })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDigestCandidate = async () => {
    if (!id || !activity) return

    setActionLoading('digest')
    setActionError(null)

    try {
      if (activity.is_digest_candidate) {
        await api.removeDigestCandidate(id)
        setActivity(prev => (prev ? { ...prev, is_digest_candidate: false } : prev))
        setToast({ type: 'success', message: '已从今日日报候选移除' })
      } else {
        await api.addDigestCandidate(id)
        setActivity(prev => (prev ? { ...prev, is_digest_candidate: true } : prev))
        setToast({ type: 'success', message: '已加入今日日报候选' })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新日报候选失败'
      setActionError(message)
      setToast({ type: 'error', message })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDeepAnalysis = async () => {
    if (!activity) return

    setAgentRunBusy(true)
    setAgentError(null)

    try {
      const job = await api.createAgentAnalysisJob({
        scope_type: 'single',
        trigger_type: 'manual',
        activity_ids: [activity.id],
        template_id: defaultTemplate?.id,
      })

      const nextItem = selectAgentAnalysisItem(job, activity.id)
      setAgentJob(job)
      setAgentItem(nextItem)
      setActivity(prev => (prev ? { ...prev, analysis_current_run_id: job.id } : prev))
      setToast({ type: 'success', message: 'Deep analysis draft 已生成' })
    } catch (err) {
      const message = err instanceof Error ? err.message : '运行 deep analysis 失败'
      setAgentError(message)
      setToast({ type: 'error', message })
    } finally {
      setAgentRunBusy(false)
    }
  }

  const handleApproveAnalysis = async (note: string) => {
    if (!id || !activity || !agentItem) return

    const result = await approveItem(agentItem.id, {
      review_note: normalizeTextField(note),
    })

    if (!result) {
      return
    }

    setToast({ type: 'success', message: 'Draft 已批准并写回 activity' })

    try {
      const refreshed = await api.getActivity(id)
      const isTracking = Boolean(refreshed.tracking || refreshed.is_tracking)
      setActivity(refreshed)
      setTracking(refreshed.tracking ?? null)
      setPlanForm(buildTrackingPlanForm(refreshed.tracking ?? null, isTracking))
      trackingReadyRef.current = isTracking
    } catch (err) {
      const message = err instanceof Error ? err.message : '刷新 activity 详情失败'
      setAgentError(message)
    }
  }

  const handleRejectAnalysis = async (note: string) => {
    if (!agentItem) return

    const result = await rejectItem(agentItem.id, {
      review_note: normalizeTextField(note),
    })

    if (!result) {
      return
    }

    setToast({ type: 'success', message: 'Draft 已拒绝，主 activity 未被写回' })
  }

  if (loading) {
    return <Loading text="加载活动详情..." />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => window.location.reload()} />
  }

  if (!activity) {
    return (
      <div className="py-12 text-center">
        <div className="mb-4 text-5xl text-gray-400">◌</div>
        <p className="text-gray-500">活动不存在</p>
        <Link to="/activities" className="mt-4 inline-block text-primary-600 hover:underline">
          返回活动列表
        </Link>
      </div>
    )
  }

  const deadline = activity.dates?.deadline
  const days = deadline ? daysUntil(deadline) : null
  const expired = deadline ? isExpired(deadline) : false
  const deadlineLevel = activity.deadline_level ?? 'none'
  const analysisStatus = activity.analysis_status ?? null
  const displayTitle = buildActivityDisplayTitle(activity)
  const displaySourceName = localizeAnalysisText(activity.source_name)
  const displayScoreReason = localizeAnalysisText(activity.score_reason)
  const displaySummary = buildActivityDisplayExcerpt(activity, 280) || localizeAnalysisText(activity.full_content)
  const analysisReasons = (activity.analysis_summary_reasons ?? []).map(reason => localizeAnalysisText(reason))
  const analysisLayerResults = activity.analysis_layer_results ?? []
  const analysisFieldEntries = Object.entries(activity.analysis_fields ?? {}).filter(([key]) => !key.startsWith('_'))
  const analysisAdjustHref = analysisStatus ? `/activities?analysis_status=${analysisStatus}` : '/activities'
  const agentDraft = agentItem?.draft ?? activity.analysis_latest_draft ?? null
  const agentStructured =
    (agentItem?.draft?.structured as Record<string, unknown> | undefined) ??
    activity.analysis_latest_draft?.structured ??
    activity.analysis_structured ??
    {}
  const displayNextAction = localizeAnalysisText(tracking?.next_action)

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <button
        type="button"
        aria-label="返回上一页"
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        返回
      </button>

      <div className="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-lg">
        {activity.image_url && (
          <div className="relative h-72 bg-gray-100">
            <img
              src={activity.image_url}
              alt={displayTitle}
              decoding="async"
              className="h-full w-full object-cover"
              onError={event => {
                const container = (event.target as HTMLImageElement).parentElement
                if (container) {
                  container.style.display = 'none'
                }
              }}
            />
          </div>
        )}

        <div className="border-b border-gray-100 p-8">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${
                CATEGORY_COLOR_MAP[activity.category] || 'bg-gray-100 text-gray-800'
              }`}
            >
              <span>{CATEGORY_ICON_MAP[activity.category]}</span>
              <span>{CATEGORY_LABELS[activity.category]}</span>
            </span>

            {activity.score !== undefined && activity.score !== null && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
                评分 {activity.score.toFixed(1)}
              </span>
            )}

            {activity.trust_level && (
              <span className={`rounded-full px-3 py-1 text-sm font-medium ${TRUST_STYLES[activity.trust_level]}`}>
                可信度 {getTrustLevelLabel(activity.trust_level)}
              </span>
            )}

            <span className={`rounded-full px-3 py-1 text-sm font-medium ${DEADLINE_STYLES[deadlineLevel]}`}>
              {DEADLINE_LABELS[deadlineLevel]}
            </span>
          </div>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <h1 className="text-3xl font-bold text-gray-900">{displayTitle}</h1>
              <div className="text-sm text-gray-500">来自 {displaySourceName}</div>
              {activity.score_reason && (
                <p className="text-sm text-primary-700">{displayScoreReason}</p>
              )}
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                data-testid="detail-track-button"
                onClick={handleTrack}
                disabled={actionLoading === 'track'}
                className="btn btn-primary"
              >
                {activity.is_tracking ? '更新跟进' : '加入跟进'}
              </button>
              <button
                type="button"
                data-testid="detail-favorite-button"
                onClick={handleFavorite}
                disabled={actionLoading === 'favorite'}
                className="btn btn-secondary"
              >
                {activity.is_favorited ? '取消收藏' : '加入收藏'}
              </button>
              <button
                type="button"
                data-testid="detail-digest-button"
                onClick={handleDigestCandidate}
                disabled={actionLoading === 'digest'}
                className="btn btn-secondary"
              >
                {activity.is_digest_candidate ? '移出今日日报' : '加入今日日报'}
              </button>
              <a
                href={activity.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                打开原始链接
              </a>
            </div>
          </div>
        </div>

        <div className="space-y-8 p-8">
          {actionError && <ErrorMessage message={actionError} />}

          {(activity.summary || activity.full_content) && (
            <section className="rounded-2xl bg-slate-50 p-6">
              <h2 className="mb-3 text-lg font-semibold text-gray-900">机会摘要</h2>
              <p data-testid="activity-summary" className="whitespace-pre-wrap break-words leading-7 text-gray-700">
                {displaySummary}
              </p>
            </section>
          )}

          {(analysisStatus || analysisReasons.length > 0 || activity.analysis_fields) && (
            <section
              data-testid="activity-analysis-panel"
              className="rounded-2xl border border-sky-100 bg-sky-50/60 p-6"
            >
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">AI 分析</h2>
                  <p className="mt-1 text-sm text-gray-600">
                    先给你结论，再展开证据和下一步动作建议。
                  </p>
                  {localizedDefaultTemplate && (
                    <div
                      data-testid="activity-analysis-template-context"
                      className="mt-3 inline-flex rounded-full border border-sky-200 bg-white px-3 py-1 text-xs font-medium text-sky-800"
                    >
                      当前模板: {localizedDefaultTemplate.name}
                    </div>
                  )}
                  <div className="mt-3">
                    <Link
                      to={analysisAdjustHref}
                      data-testid="activity-analysis-adjust-link"
                      className="inline-flex items-center rounded-full border border-sky-200 bg-white px-3 py-1 text-xs font-medium text-sky-800 transition hover:border-sky-300 hover:text-sky-900"
                    >
                      去机会池继续调规则
                    </Link>
                  </div>
                </div>
                {analysisStatus && (
                  <span
                    data-testid="activity-analysis-status"
                    className={`inline-flex w-fit rounded-full px-3 py-1 text-sm font-medium ${ANALYSIS_STATUS_STYLES[analysisStatus]}`}
                  >
                    {getAnalysisStatusLabel(analysisStatus)}
                  </span>
                )}
              </div>

              {activity.analysis_failed_layer && (
                <p className="mt-4 text-sm text-gray-600">
                  淘汰层级: {getAnalysisFieldLabel(activity.analysis_failed_layer)}
                </p>
              )}

              {analysisReasons.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {analysisReasons.map((reason: string) => (
                    <span
                      key={reason}
                      className="rounded-full border border-sky-200 bg-white px-3 py-1 text-sm text-slate-700"
                    >
                      {reason}
                    </span>
                  ))}
                </div>
              )}

              {analysisLayerResults.length > 0 && (
                <div data-testid="activity-analysis-chain" className="mt-6 space-y-3">
                  <div className="text-sm font-semibold text-slate-900">判断链路</div>
                  {analysisLayerResults.map(layer => (
                    <div key={layer.key} className="rounded-2xl border border-sky-100 bg-white/80 p-4">
                      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="text-sm font-semibold text-slate-900">
                            {getAnalysisFieldLabel(layer.key) || localizeAnalysisText(layer.label)}
                          </div>
                          <div className="text-xs text-slate-500">{layer.key}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span
                            className={`rounded-full px-3 py-1 text-xs font-medium ${
                              LAYER_DECISION_STYLES[layer.decision as keyof typeof LAYER_DECISION_STYLES] ||
                              'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {LAYER_DECISION_LABELS[layer.decision as keyof typeof LAYER_DECISION_LABELS] ||
                              localizeAnalysisText(layer.decision)}
                          </span>
                          <span className="text-xs text-slate-500">得分 {layer.score.toFixed(2)}</span>
                        </div>
                      </div>
                      {layer.reasons.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {layer.reasons.map((reason: string) => (
                            <span
                              key={`${layer.key}-${reason}`}
                              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
                            >
                              {localizeAnalysisText(reason)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {analysisFieldEntries.length > 0 && (
                <div data-testid="activity-analysis-fields" className="mt-6">
                  <div className="text-sm font-semibold text-slate-900">结构化分析字段</div>
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                    {analysisFieldEntries.map(([key, value]) => (
                      <div key={key} className="rounded-2xl border border-sky-100 bg-white/80 p-4">
                        <div className="text-xs uppercase tracking-wide text-slate-500">{getAnalysisFieldLabel(key)}</div>
                        <div className="mt-2 text-sm font-medium text-slate-900">
                          {localizeAnalysisText(String(value))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          <section
            data-testid="activity-agent-analysis-workbench"
            className="rounded-2xl border border-slate-200 bg-slate-50/60 p-6"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">AI Agent Workbench</h2>
                <p className="mt-1 text-sm text-slate-600">
                  在详情页里直接运行深度分析、查看证据与执行轨迹，再决定是否写回主结论。
                </p>
              </div>
              {agentJob && (
                <div className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-500">
                  Current run: {agentJob.id}
                </div>
              )}
            </div>

            {agentError && (
              <div className="mt-4">
                <ErrorMessage message={agentError} />
              </div>
            )}
            {reviewError && (
              <div className="mt-4">
                <ErrorMessage message={reviewError} />
              </div>
            )}

            <div className="mt-5 grid grid-cols-1 gap-6 xl:grid-cols-2">
              <AgentVerdictCard
                snapshot={agentDraft}
                onRun={handleDeepAnalysis}
                running={agentRunBusy}
              />
              <StructuredFactorCard structured={agentStructured} />
            </div>

            {(agentItem || agentLoading) && (
              <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
                <EvidencePanel evidence={agentItem?.evidence ?? []} />
                <ExecutionTracePanel steps={agentItem?.steps ?? []} />
              </div>
            )}

            {agentItem && (
              <div className="mt-6">
                <ReviewActionBar
                  reviewing={reviewing}
                  onApprove={handleApproveAnalysis}
                  onReject={handleRejectAnalysis}
                />
              </div>
            )}
          </section>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-gray-100 p-5">
              <div className="text-sm text-gray-500">当前状态</div>
              <div className="mt-2 text-xl font-semibold text-gray-900">
                {getTrackingStatusLabel(tracking?.status || (activity.is_tracking ? 'tracking' : 'untracked'))}
              </div>
            </div>
            <div className="rounded-2xl border border-gray-100 p-5">
              <div className="text-sm text-gray-500">截止时间</div>
              <div className="mt-2 text-xl font-semibold text-gray-900">
                {deadline ? formatDateOnly(deadline) : '未提供'}
              </div>
              {deadline && !expired && days !== null && (
                <div className="mt-1 text-sm text-gray-500">{days === 0 ? '今天截止' : `${days} 天后截止`}</div>
              )}
              {expired && <div className="mt-1 text-sm text-red-600">已截止</div>}
            </div>
            <div className="rounded-2xl border border-gray-100 p-5">
              <div className="text-sm text-gray-500">下一步动作</div>
              <div className="mt-2 text-xl font-semibold text-gray-900">
                {displayNextAction || tracking?.next_action || '从这里开始判断'}
              </div>
              {tracking?.remind_at && (
                <div className="mt-1 text-sm text-gray-500">提醒：{formatDateTime(tracking.remind_at)}</div>
              )}
            </div>
          </div>

          <section className="rounded-2xl border border-primary-100 bg-primary-50/40 p-6">
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">行动计划</h2>
                <p className="mt-1 text-sm text-gray-600">
                  在详情页里直接保存跟进状态、下一步动作和提醒时间。
                </p>
              </div>
              {tracking?.updated_at && (
                <div className="text-xs text-gray-500">上次更新: {formatDateTime(tracking.updated_at)}</div>
              )}
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-gray-700">跟进状态</span>
                <select
                  aria-label="跟进状态"
                  value={planForm.status}
                  onChange={event => handlePlanChange('status', event.target.value as TrackingState['status'])}
                  className="select w-full"
                >
                  <option value="saved">已保存</option>
                  <option value="tracking">跟进中</option>
                  <option value="done">已完成</option>
                  <option value="archived">已归档</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-gray-700">提醒时间</span>
                <input
                  aria-label="提醒时间"
                  type="datetime-local"
                  value={planForm.remind_at}
                  onChange={event => handlePlanChange('remind_at', event.target.value)}
                  className="input w-full"
                />
              </label>

              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-medium text-gray-700">下一步动作</span>
                <input
                  aria-label="下一步动作"
                  type="text"
                  value={planForm.next_action}
                  onChange={event => handlePlanChange('next_action', event.target.value)}
                  placeholder="例如：确认资格、准备材料、提交申请"
                  className="input w-full"
                />
              </label>

              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-medium text-gray-700">跟进备注</span>
                <textarea
                  aria-label="跟进备注"
                  value={planForm.notes}
                  onChange={event => handlePlanChange('notes', event.target.value)}
                  rows={4}
                  placeholder="记录约束、联系人、提交素材或判断依据"
                  className="input min-h-28 w-full py-3"
                />
              </label>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                type="button"
                data-testid="detail-save-plan-button"
                onClick={handleSavePlan}
                disabled={actionLoading === 'plan'}
                className="btn btn-primary"
              >
                {actionLoading === 'plan' ? '保存中...' : '保存跟进计划'}
              </button>
              <div className="text-sm text-gray-500">
                {tracking ? '修改会直接同步到跟进列表。' : '首次保存会自动创建跟进记录。'}
              </div>
            </div>
          </section>

          {activity.description && (
            <section>
              <h2 className="mb-2 text-lg font-semibold text-gray-900">活动描述</h2>
              <p data-testid="activity-description" className="whitespace-pre-wrap break-words leading-7 text-gray-600">
                {localizeAnalysisText(activity.description)}
              </p>
            </section>
          )}

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {activity.prize && (
              <div className="rounded-2xl bg-green-50 p-5">
                <h3 className="mb-2 text-sm font-medium text-green-800">奖励信息</h3>
                <div className="text-2xl font-bold text-green-600">
                  {activity.prize.currency} {activity.prize.amount?.toLocaleString() || '待定'}
                </div>
                {activity.prize.description && (
                  <p className="mt-2 text-sm text-green-700">{localizeAnalysisText(activity.prize.description)}</p>
                )}
              </div>
            )}

            {activity.dates && (
              <div className="rounded-2xl bg-blue-50 p-5">
                <h3 className="mb-2 text-sm font-medium text-blue-800">时间节点</h3>
                <div className="space-y-2 text-sm">
                  {activity.dates.start_date && (
                    <div className="flex justify-between">
                      <span className="text-blue-600">开始</span>
                      <span className="text-blue-900">{formatDateOnly(activity.dates.start_date)}</span>
                    </div>
                  )}
                  {activity.dates.end_date && (
                    <div className="flex justify-between">
                      <span className="text-blue-600">结束</span>
                      <span className="text-blue-900">{formatDateOnly(activity.dates.end_date)}</span>
                    </div>
                  )}
                  {deadline && (
                    <div className="flex justify-between">
                      <span className="text-blue-600">截止</span>
                      <span className={expired ? 'text-red-600' : 'text-blue-900'}>{formatDateOnly(deadline)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <section className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
            {activity.organizer && (
              <div className="flex items-center gap-2">
                <span className="text-gray-500">主办方：</span>
                <span className="text-gray-900">{localizeAnalysisText(activity.organizer)}</span>
              </div>
            )}
            {activity.location && (
              <div className="flex items-center gap-2">
                <span className="text-gray-500">地点：</span>
                <span className="text-gray-900">{localizeAnalysisText(activity.location)}</span>
              </div>
            )}
            {activity.tags.length > 0 && (
              <div className="col-span-full flex items-center gap-2">
                <span className="text-gray-500">标签：</span>
                <div className="flex flex-wrap gap-1">
                  {activity.tags.map(tag => (
                    <span key={tag} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {activity.updated_fields && activity.updated_fields.length > 0 && (
              <div className="col-span-full flex items-center gap-2">
                <span className="text-gray-500">最近变化：</span>
                <div className="flex flex-wrap gap-1">
                  {activity.updated_fields.map(field => (
                    <span key={field} className="rounded bg-primary-50 px-2 py-0.5 text-xs text-primary-700">
                      {FIELD_LABELS[field] || field}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {activity.timeline && activity.timeline.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-gray-900">时间线</h2>
              <div className="space-y-3">
                {activity.timeline.map(item => (
                  <div key={item.key} className="flex items-center justify-between rounded-xl border border-gray-100 p-4">
                    <div className="font-medium text-gray-900">{localizeAnalysisText(item.label)}</div>
                    <div className="text-sm text-gray-500">{formatDateTime(item.timestamp)}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {activity.related_items && activity.related_items.length > 0 && (
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">相关机会</h2>
                <Link to="/activities" className="text-sm text-primary-600 hover:text-primary-700">
                  去机会池
                </Link>
              </div>
              <div className="space-y-3">
                {activity.related_items.map(item => (
                  <Link
                    key={item.id}
                    to={`/activities/${item.id}`}
                    className="block rounded-xl border border-gray-100 p-4 transition-all hover:border-primary-200 hover:bg-primary-50/30"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-gray-900">{localizeAnalysisText(item.title)}</div>
                        <div className="mt-1 text-sm text-gray-600">
                          {localizeAnalysisText(item.summary || item.description) || '暂无摘要'}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        {item.score !== undefined && item.score !== null && (
                          <span className="rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-700">
                            {item.score.toFixed(1)}
                          </span>
                        )}
                        {item.trust_level && (
                          <span className={`rounded-full px-2 py-1 font-medium ${TRUST_STYLES[item.trust_level]}`}>
                            {getTrustLevelLabel(item.trust_level)}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          <div className="space-y-1 border-t border-gray-100 pt-4 text-xs text-gray-400">
            <div>创建时间: {formatDateTime(activity.created_at)}</div>
            <div>更新时间: {formatDateTime(activity.updated_at)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ActivityDetailPage
