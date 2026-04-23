import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useAgentAnalysisJobs } from '../hooks/useAgentAnalysisJobs'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { useWorkspace } from '../hooks/useWorkspace'
import { api } from '../services/api'
import type { ActivityListItem, AgentAnalysisJobDetail, AgentAnalysisJobSummary, TrackingState } from '../types'
import { CATEGORY_LABELS } from '../types'
import { CATEGORY_COLOR_MAP } from '../utils/constants'
import { formatDateOnly, formatDateTime } from '../utils/formatDate'
import {
  getAnalysisStatusLabel,
  getDeadlineLevelLabel,
  getSourceStatusLabel,
  getTrustLevelLabel,
  localizeAnalysisTemplate,
  localizeAnalysisText,
} from '../utils/analysisI18n'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'

function countHighValueOpportunities(activities: ActivityListItem[]) {
  return activities.filter(activity => (activity.score ?? 0) >= 8 || Boolean(activity.prize?.amount)).length
}

function countUrgentActions(activities: ActivityListItem[]) {
  return activities.filter(
    activity => activity.deadline_level === 'urgent' || activity.deadline_level === 'soon'
  ).length
}

function formatShare(value: number, total: number) {
  if (total <= 0) {
    return '0%'
  }

  return `${Math.round((value / total) * 100)}%`
}

function summarizeBlockedReasons(activities: ActivityListItem[]) {
  const counts = new Map<string, number>()

  activities.forEach(activity => {
    activity.analysis_summary_reasons?.forEach(reason => {
      const localizedReason = localizeAnalysisText(reason)
      counts.set(localizedReason, (counts.get(localizedReason) ?? 0) + 1)
    })
  })

  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 3)
}

function buildWorkspaceSnapshot(args: {
  recentActivities: number
  highValueCount: number
  urgentCount: number
  alertCount: number
}) {
  const segments: string[] = []

  if (args.recentActivities > 0) {
    segments.push(`今天新增 ${args.recentActivities} 条机会`)
  } else {
    segments.push('今天暂时没有新增机会')
  }

  if (args.highValueCount > 0) {
    segments.push(`${args.highValueCount} 条高价值机会值得优先判断`)
  }

  if (args.urgentCount > 0) {
    segments.push(`${args.urgentCount} 条机会需要尽快处理`)
  }

  if (args.alertCount > 0) {
    segments.push(`${args.alertCount} 个来源需要排查`)
  } else {
    segments.push('来源状态稳定')
  }

  return `${segments.join('，')}。`
}

function buildTemplateDiagnosis(args: {
  total: number
  passed: number
  watch: number
  rejected: number
  blockedReasonSummary: Array<[string, number]>
}) {
  const { total, passed, watch, rejected, blockedReasonSummary } = args
  const mainReason = blockedReasonSummary[0]?.[0]

  if (total <= 0) {
    return {
      title: '当前还没有模板判断样本',
      description: '先运行一次分析，系统才会告诉你模板是偏严还是偏宽。',
      suggestion: '先去跑一轮模板分析',
      tone: 'slate' as const,
    }
  }

  if (rejected / total >= 0.85 && passed === 0 && watch <= 1) {
    return {
      title: '当前模板偏严格',
      description: '几乎所有机会都被拦掉了，说明规则把潜在机会挡在了前面。',
      suggestion: mainReason ? `优先放宽一条硬门槛：${mainReason}` : '优先放宽一条硬门槛',
      tone: 'rose' as const,
    }
  }

  if (passed / total >= 0.7 && rejected <= 1 && total >= 4) {
    return {
      title: '当前模板偏宽松',
      description: '放行比例偏高，建议再补一条约束，避免低质量机会混进来。',
      suggestion: '补一条最关键的过滤条件，再跑一轮结果对比',
      tone: 'amber' as const,
    }
  }

  return {
    title: '当前模板基本平衡',
    description: '通过、观察、拦截三类结果都有，说明规则已经开始形成筛选能力。',
    suggestion: mainReason ? `继续观察高频拦截原因：${mainReason}` : '继续观察高频拦截原因，再做小步微调',
    tone: 'emerald' as const,
  }
}

function buildAlertDiagnosis(alertCount: number) {
  if (alertCount <= 0) {
    return {
      title: '今天没有系统告警',
      description: '来源抓取和更新节奏都比较稳定，你可以把精力放在机会判断上。',
      tone: 'emerald' as const,
    }
  }

  return {
    title: alertCount === 1 ? '有 1 个来源需要排查' : `有 ${alertCount} 个来源需要排查`,
    description: '建议先处理来源异常，避免后续判断建立在过期数据上。',
    tone: 'rose' as const,
  }
}

const DIGEST_NOISE_LINE_PATTERNS = [
  /^(?:关于我们|联系我们|原文链接|更多|下载APP|回到顶部)$/i,
  /^(?:today|yesterday)\s+\d{1,2}:\d{2}$/i,
  /^(?:今天|昨日|昨天)\s+\d{1,2}:\d{2}$/i,
  /^(?:follow us|share this|social media|copyright)$/i,
]

function normalizeDigestPreviewLine(text: string) {
  return text
    .replace(/\\\\/g, ' ')
    .replace(/\)\]\(|\]\(|\)\[|\]\[/g, ' ')
    .replace(/!\[[^\]]*\]\(([^)]+)\)/g, ' ')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/https?:\/\/\S+/gi, ' ')
    .replace(/\b(?:[\w-]+\.)+[a-z]{2,}\S*/gi, ' ')
    .replace(/%[0-9A-Fa-f]{2}/g, ' ')
    .replace(/\b[a-z]+=(?:[^&\s]+&){1,}[^&\s]+/gi, ' ')
    .replace(/\bresize=\d+x\d+\b/gi, ' ')
    .replace(/(^|\s)(?:关于我们|联系我们|原文链接|更多|下载APP|回到顶部|Homepage recommendation)(?=\s|$)/gi, ' ')
    .replace(/[`>#*_]+/g, ' ')
    .replace(/[|·]/g, ' ')
    .replace(/[\[\]]+/g, ' ')
    .replace(/(?:(?<=\s)|^)[()]+(?=\s|$)/g, ' ')
    .replace(/\(\s*\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function buildDigestPreviewExcerpt(content: string, maxLines = 4) {
  if (!content) {
    return 'AI 正在整理今日日报。'
  }

  const lines: string[] = []
  const seen = new Set<string>()

  content
    .split(/\r?\n+/)
    .map(normalizeDigestPreviewLine)
    .filter(line => line.length >= 4)
    .filter(line => !DIGEST_NOISE_LINE_PATTERNS.some(pattern => pattern.test(line)))
    .forEach(line => {
      const localizedLine = localizeAnalysisText(line)
      const dedupeKey = localizedLine.toLowerCase()
      if (!localizedLine || seen.has(dedupeKey)) return
      seen.add(dedupeKey)
      lines.push(localizedLine)
    })

  if (lines.length === 0) {
    return localizeAnalysisText(normalizeDigestPreviewLine(content)) || 'AI 正在整理今日日报。'
  }

  return lines.slice(0, maxLines).join('\n')
}

function pickLatestBatchJob(jobs: AgentAnalysisJobSummary[]) {
  return jobs.find(job => job.scope_type === 'batch') ?? null
}

function countDraftReviewItems(job: AgentAnalysisJobDetail | null) {
  return (job?.items ?? []).filter(item => item.draft && item.reviews.length === 0).length
}

function countLowConfidenceItems(job: AgentAnalysisJobDetail | null) {
  return (job?.items ?? []).filter(item => {
    const confidenceBand = item.draft?.structured?.confidence_band
    return item.draft?.risk_flags?.includes('low_confidence') || confidenceBand === 'low'
  }).length
}

function getToneClasses(tone: 'emerald' | 'rose' | 'amber' | 'slate') {
  if (tone === 'emerald') return 'border-emerald-200 bg-emerald-50/70 text-emerald-950'
  if (tone === 'rose') return 'border-rose-200 bg-rose-50/80 text-rose-950'
  if (tone === 'amber') return 'border-amber-200 bg-amber-50/80 text-amber-950'
  return 'border-slate-200 bg-slate-50 text-slate-900'
}

function getOpportunitySummary(activity: ActivityListItem) {
  return buildActivityDisplayExcerpt(activity) || localizeAnalysisText(activity.score_reason) || '暂无摘要'
}

export function WorkspacePage() {
  const { defaultTemplate } = useAnalysisTemplates()
  const localizedDefaultTemplate = defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null
  const { jobs: agentJobs, activeJob: activeAgentJob } = useAgentAnalysisJobs()
  const { workspace, loading, error, refetch } = useWorkspace()

  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [opportunityOverrides, setOpportunityOverrides] = useState<
    Record<string, Pick<ActivityListItem, 'is_tracking' | 'is_favorited'>>
  >({})

  const workspaceSyncKey = workspace
    ? `${workspace.overview.last_update ?? 'none'}:${workspace.top_opportunities.map(item => item.id).join(',')}`
    : 'empty'

  useEffect(() => {
    setOpportunityOverrides({})
  }, [workspaceSyncKey])

  if (loading && !workspace) return <Loading text="正在加载工作台..." />
  if (error && !workspace) return <ErrorMessage message={error} onRetry={refetch} />
  if (!workspace) return null

  const {
    overview,
    top_opportunities,
    digest_preview,
    trends,
    alert_sources,
    first_actions,
    analysis_overview = { total: 0, passed: 0, watch: 0, rejected: 0 },
    blocked_opportunities = [],
  } = workspace

  const topOpportunities = top_opportunities.map(activity => ({ ...activity, ...opportunityOverrides[activity.id] }))
  const firstActions = first_actions.map(activity => ({ ...activity, ...opportunityOverrides[activity.id] }))
  const highValueCount = countHighValueOpportunities(topOpportunities)
  const urgentActionCount = countUrgentActions(firstActions)
  const blockedReasonSummary = summarizeBlockedReasons(blocked_opportunities)
  const passRate = formatShare(analysis_overview.passed, analysis_overview.total)
  const watchRate = formatShare(analysis_overview.watch, analysis_overview.total)
  const rejectedRate = formatShare(analysis_overview.rejected, analysis_overview.total)
  const digestPreviewExcerpt = digest_preview ? buildDigestPreviewExcerpt(digest_preview.content) : ''
  const workspaceSnapshot = buildWorkspaceSnapshot({
    recentActivities: overview.recent_activities,
    highValueCount,
    urgentCount: urgentActionCount,
    alertCount: alert_sources.length,
  })
  const templateDiagnosis = buildTemplateDiagnosis({ ...analysis_overview, blockedReasonSummary })
  const alertDiagnosis = buildAlertDiagnosis(alert_sources.length)
  const latestBatchJob = pickLatestBatchJob(agentJobs)
  const activeBatchJob = activeAgentJob?.scope_type === 'batch' ? activeAgentJob : null
  const draftReviewCount = countDraftReviewItems(activeBatchJob)
  const lowConfidenceCount = countLowConfidenceItems(activeBatchJob)
  const failedDraftCount = activeBatchJob
    ? activeBatchJob.items.filter(item => item.status === 'failed').length
    : latestBatchJob?.failed_items ?? 0
  const maxTrendCount = Math.max(...trends.map(item => item.count), 1)

  function applyTrackingState(activityId: string, tracking: TrackingState) {
    setOpportunityOverrides(prev => ({
      ...prev,
      [activityId]: { is_tracking: true, is_favorited: tracking.is_favorited },
    }))
  }

  async function handleTrack(activity: ActivityListItem) {
    setActionLoading(`track:${activity.id}`)
    try {
      const tracking = activity.is_tracking
        ? await api.updateTracking(activity.id, { status: 'tracking' })
        : await api.createTracking(activity.id, { status: 'tracking' })
      applyTrackingState(activity.id, tracking)
      setToast({ type: 'success', message: activity.is_tracking ? '跟进状态已更新。' : '已加入跟进。' })
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : '更新跟进失败' })
    } finally {
      setActionLoading(null)
    }
  }

  async function handleFavorite(activity: ActivityListItem) {
    setActionLoading(`favorite:${activity.id}`)
    try {
      if (!activity.is_tracking) {
        const created = await api.createTracking(activity.id, { status: 'tracking' })
        applyTrackingState(activity.id, created)
      }

      const tracking = await api.updateTracking(activity.id, { is_favorited: !activity.is_favorited })
      applyTrackingState(activity.id, tracking)
      setToast({ type: 'success', message: tracking.is_favorited ? '已加入收藏。' : '已取消收藏。' })
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : '更新收藏状态失败' })
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-8" data-testid="workspace-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <section className="rounded-[28px] bg-gradient-to-br from-slate-950 via-slate-900 to-sky-900 p-8 text-white shadow-xl">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl space-y-4">
            <div className="text-sm uppercase tracking-[0.28em] text-sky-200">AI 智能代理决策驾驶舱</div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">机会工作台</h1>
            <p className="max-w-2xl text-sm leading-7 text-slate-100" data-testid="workspace-summary-banner">
              {workspaceSnapshot}
            </p>
            <p className="max-w-2xl text-sm leading-7 text-slate-300">
              这里不是信息总览，而是今天该先看什么、为什么值得看、下一步怎么推进的决策入口。
            </p>
            {localizedDefaultTemplate && (
              <div
                data-testid="workspace-default-template"
                className="inline-flex w-fit items-center rounded-full border border-sky-300/40 bg-white/10 px-4 py-2 text-sm text-sky-100"
              >
                当前 AI 模板：{localizedDefaultTemplate.name}
              </div>
            )}
            <div className="flex flex-wrap gap-3">
              <Link to="/activities?sort_by=score" className="btn border-0 bg-white text-slate-900 hover:bg-slate-100">
                打开机会池
              </Link>
              <Link to="/tracking" className="btn btn-secondary border-slate-300 text-white hover:bg-white/10">
                打开跟进列表
              </Link>
            </div>
          </div>

          <div className="grid w-full max-w-xl gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-sky-100">今日新增</div>
              <div className="mt-3 text-3xl font-semibold">{overview.recent_activities}</div>
              <div className="mt-2 text-sm text-slate-200">新增情报已进入当前判断队列。</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-sky-100">待处理</div>
              <div className="mt-3 text-3xl font-semibold">{urgentActionCount}</div>
              <div className="mt-2 text-sm text-slate-200">建议先推进临近截止和高优先级机会。</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-sky-100">告警数量</div>
              <div className="mt-3 text-3xl font-semibold">{alert_sources.length}</div>
              <div className="mt-2 text-sm text-slate-200">来源异常会直接影响后续判断可信度。</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 sm:col-span-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-sky-100">最后更新</div>
                  <div className="mt-2 text-base font-medium">
                    {overview.last_update ? formatDateTime(overview.last_update) : '暂无数据'}
                  </div>
                </div>
                <button
                  type="button"
                  data-testid="workspace-refresh-button"
                  onClick={() => {
                    void refetch()
                  }}
                  className="btn btn-secondary border-slate-300 text-white hover:bg-white/10"
                >
                  刷新
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        data-testid="workspace-agent-analysis-summary"
        className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-sm font-medium text-slate-500">Agent analysis summary</div>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">最近一轮批次复核概览</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              聚焦当前默认模板、最近批次作业，以及仍待人工确认的 draft 工作量。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/analysis/results" className="btn btn-secondary">
              打开批次结果
            </Link>
            <Link to="/analysis/templates" className="btn btn-secondary">
              调整模板
            </Link>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-2xl bg-slate-50 p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">Active template</div>
            <div className="mt-2 text-lg font-semibold text-slate-900">
              {defaultTemplate?.name ?? 'No active template'}
            </div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">Latest batch</div>
            <div className="mt-2 text-lg font-semibold text-slate-900">
              {latestBatchJob?.id ?? 'No batch job yet'}
            </div>
            {latestBatchJob?.created_at && (
              <div className="mt-1 text-xs text-slate-500">{formatDateTime(latestBatchJob.created_at)}</div>
            )}
          </div>
          <div className="rounded-2xl bg-amber-50 p-4">
            <div className="text-xs uppercase tracking-wide text-amber-700">Draft reviews</div>
            <div className="mt-2 text-3xl font-semibold text-amber-800">{draftReviewCount}</div>
          </div>
          <div className="rounded-2xl bg-rose-50 p-4">
            <div className="text-xs uppercase tracking-wide text-rose-700">Low confidence</div>
            <div className="mt-2 text-3xl font-semibold text-rose-800">{lowConfidenceCount}</div>
          </div>
          <div className="rounded-2xl bg-sky-50 p-4">
            <div className="text-xs uppercase tracking-wide text-sky-700">Failed or blocked</div>
            <div className="mt-2 text-3xl font-semibold text-sky-800">
              {failedDraftCount + blocked_opportunities.length}
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.25fr_1fr_1fr]">
        <article data-testid="workspace-priority-panel" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-medium text-slate-500">今日结论</div>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">先处理高优先级机会</h2>
            </div>
            <Link to="/activities?sort_by=score" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              进入机会池
            </Link>
          </div>

          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">立即处理</div>
            <div className="mt-2 text-sm leading-6 text-slate-700">
              当前有 {firstActions.length} 条第一步动作、{urgentActionCount} 条临近截止机会、{highValueCount} 条高价值机会。
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {firstActions.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                目前还没有需要立刻处理的动作，建议先去机会池补充判断样本。
              </div>
            ) : (
              firstActions.slice(0, 3).map(activity => (
                <Link
                  key={activity.id}
                  to={`/activities/${activity.id}`}
                  className="block rounded-2xl border border-slate-200 bg-slate-50/70 p-4 transition-all hover:border-sky-200 hover:bg-sky-50/40"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="font-medium text-slate-900">{buildActivityDisplayTitle(activity)}</div>
                      <div className="mt-1 text-sm leading-6 text-slate-600">{getOpportunitySummary(activity)}</div>
                    </div>
                    <div className="shrink-0 rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700">
                      {getDeadlineLevelLabel(activity.deadline_level || 'normal')}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </article>

        <article
          data-testid="workspace-template-diagnosis"
          className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-medium text-slate-500">模板诊断</div>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">{templateDiagnosis.title}</h2>
            </div>
            <Link to="/analysis/templates" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              去优化模板
            </Link>
          </div>

          <div className={`mt-4 rounded-2xl border p-4 ${getToneClasses(templateDiagnosis.tone)}`}>
            <p className="text-sm leading-6">{templateDiagnosis.description}</p>
            <p className="mt-3 text-sm font-medium">{templateDiagnosis.suggestion}</p>
          </div>

          <div data-testid="workspace-template-performance" className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-medium text-slate-900">
              {localizedDefaultTemplate ? `${localizedDefaultTemplate.name} 当前表现` : '模板当前表现'}
            </div>
            <div className="mt-2 text-sm text-slate-600">
              已覆盖 {analysis_overview.total} 条机会，当前通过率 {passRate}。
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-white p-3">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-500">通过率</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{passRate}</div>
              </div>
              <div className="rounded-2xl bg-white p-3">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-500">观察占比</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{watchRate}</div>
              </div>
              <div className="rounded-2xl bg-white p-3">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-500">拦截占比</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{rejectedRate}</div>
              </div>
            </div>

            <div className="mt-4">
              <div className="text-xs uppercase tracking-[0.16em] text-slate-500">高频拦截原因</div>
              {blockedReasonSummary.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">当前还没有明显的拦截模式。</p>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  {blockedReasonSummary.map(([reason, count]) => (
                    <span
                      key={reason}
                      className="inline-flex items-center rounded-full border border-rose-200 bg-white px-3 py-1 text-xs font-medium text-rose-700"
                    >
                      {reason} · {count}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </article>

        <article data-testid="workspace-alert-panel" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-medium text-slate-500">系统告警</div>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">{alertDiagnosis.title}</h2>
            </div>
            <Link to="/sources" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              去处理
            </Link>
          </div>

          <div className={`mt-4 rounded-2xl border p-4 ${getToneClasses(alertDiagnosis.tone)}`}>
            <p className="text-sm leading-6">{alertDiagnosis.description}</p>
          </div>

          <div className="mt-4 space-y-3">
            {alert_sources.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">今天没有来源异常。</div>
            ) : (
              alert_sources.slice(0, 3).map(source => (
                <div key={source.id} className="rounded-2xl border border-rose-100 bg-rose-50/80 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="font-medium text-slate-900">{localizeAnalysisText(source.name)}</div>
                      <div className="mt-1 text-sm leading-6 text-slate-600">
                        {localizeAnalysisText(source.error_message) || '该来源需要人工排查。'}
                      </div>
                    </div>
                    <div className="shrink-0 text-xs font-medium uppercase tracking-[0.16em] text-rose-700">
                      {getSourceStatusLabel(source.status)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_1fr]">
        <div data-testid="workspace-analysis-overview" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-slate-950">分析结果概览</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">这里保留证据层，方便你快速复核模板到底放行了什么，又拦掉了什么。</p>
            </div>
            <Link to="/analysis/results" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              查看结果页
            </Link>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-emerald-50 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-emerald-700">通过</div>
              <div className="mt-2 text-3xl font-semibold text-emerald-900">{analysis_overview.passed}</div>
            </div>
            <div className="rounded-2xl bg-amber-50 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-amber-700">待观察</div>
              <div className="mt-2 text-3xl font-semibold text-amber-900">{analysis_overview.watch}</div>
            </div>
            <div className="rounded-2xl bg-rose-50 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-rose-700">拦截</div>
              <div className="mt-2 text-3xl font-semibold text-rose-900">{analysis_overview.rejected}</div>
            </div>
          </div>
        </div>

        <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-slate-950">被拦截的机会</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">适合快速回看规则是否拦得过早。</p>
            </div>
            <Link to="/activities?analysis_status=rejected" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              查看全部
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {blocked_opportunities.length === 0 ? (
              <p className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">当前没有被拦截的机会。</p>
            ) : (
              blocked_opportunities.map(activity => (
                <Link
                  key={activity.id}
                  to={`/activities/${activity.id}`}
                  className="block rounded-2xl border border-rose-100 bg-rose-50/70 p-4 transition-all hover:border-rose-200 hover:bg-rose-50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="font-medium text-slate-900">{buildActivityDisplayTitle(activity)}</div>
                      <div className="mt-1 text-sm leading-6 text-slate-600">{getOpportunitySummary(activity)}</div>
                    </div>
                    <div className="shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-rose-700">
                      {getAnalysisStatusLabel(activity.analysis_status || 'rejected')}
                    </div>
                  </div>
                  {activity.analysis_summary_reasons && activity.analysis_summary_reasons.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {activity.analysis_summary_reasons.slice(0, 2).map(reason => (
                        <span key={`${activity.id}-${reason}`} className="rounded-full border border-rose-200 bg-white px-2 py-1 text-xs text-rose-700">
                          {localizeAnalysisText(reason)}
                        </span>
                      ))}
                    </div>
                  )}
                </Link>
              ))
            )}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-slate-950">今日重点机会</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">结合评分、时效和可信度，优先展示今天最值得推进的机会。</p>
            </div>
            <Link to="/activities?sort_by=score" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              查看全部
            </Link>
          </div>

          {topOpportunities.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">今天还没有明显突出的机会。</p>
          ) : (
            <div className="space-y-4">
              {topOpportunities.map(activity => (
                <div
                  key={activity.id}
                  className="rounded-[24px] border border-slate-200 p-5 transition-all hover:border-primary-200 hover:shadow-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                        CATEGORY_COLOR_MAP[activity.category] || 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {CATEGORY_LABELS[activity.category]}
                    </span>
                    {activity.score !== undefined && activity.score !== null && (
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                        评分 {activity.score.toFixed(1)}
                      </span>
                    )}
                    {activity.trust_level && (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        可信度 {getTrustLevelLabel(activity.trust_level)}
                      </span>
                    )}
                    {activity.is_tracking && (
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">跟进中</span>
                    )}
                    {activity.is_favorited && (
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">已收藏</span>
                    )}
                  </div>

                  <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <h3 className="text-xl font-semibold text-slate-950">{buildActivityDisplayTitle(activity)}</h3>
                      <p className="mt-2 text-sm leading-7 text-slate-600">{getOpportunitySummary(activity)}</p>
                      {activity.score_reason && (
                        <p className="mt-2 text-sm text-primary-700">{localizeAnalysisText(activity.score_reason)}</p>
                      )}
                    </div>
                    <div className="grid shrink-0 gap-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600 sm:min-w-[180px]">
                      <div className="flex items-center justify-between gap-3">
                        <span>来源</span>
                        <span className="font-medium text-slate-900">{localizeAnalysisText(activity.source_name)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span>截止</span>
                        <span className="font-medium text-slate-900">
                          {activity.dates?.deadline ? formatDateOnly(activity.dates.deadline) : '暂无'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link to={`/activities/${activity.id}`} className="btn btn-secondary">
                      查看详情
                    </Link>
                    <button
                      type="button"
                      data-testid={`workspace-favorite-${activity.id}`}
                      onClick={() => {
                        void handleFavorite(activity)
                      }}
                      disabled={actionLoading === `favorite:${activity.id}`}
                      className="btn btn-secondary"
                    >
                      {activity.is_favorited ? '取消收藏' : '收藏'}
                    </button>
                    <button
                      type="button"
                      data-testid={`workspace-track-${activity.id}`}
                      onClick={() => {
                        void handleTrack(activity)
                      }}
                      disabled={actionLoading === `track:${activity.id}`}
                      className="btn btn-primary"
                    >
                      {activity.is_tracking ? '继续跟进' : '加入跟进'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="space-y-6">
          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-slate-950">今日日报</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">先看 1 分钟摘要，再决定是否展开完整内容。</p>
              </div>
              <Link to="/digests" className="text-sm font-medium text-primary-600 hover:text-primary-700">
                打开日报
              </Link>
            </div>

            {digest_preview ? (
              <div className="mt-4 space-y-4">
                <div>
                  <div className="text-sm text-slate-500">{digest_preview.digest_date}</div>
                  <div className="text-lg font-semibold text-slate-900">{localizeAnalysisText(digest_preview.title)}</div>
                </div>
                {digest_preview.summary && (
                  <p className="text-sm leading-6 text-slate-600">{localizeAnalysisText(digest_preview.summary)}</p>
                )}
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">1 分钟速览</div>
                  <div data-testid="workspace-digest-excerpt" className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {digestPreviewExcerpt}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">今天的日报还没生成。</div>
            )}
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div>
              <h2 className="text-2xl font-semibold text-slate-950">最近 7 天趋势</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">观察新增机会量，帮助判断今天是该筛选还是该冲刺。</p>
            </div>
            <div className="mt-4 space-y-3">
              {trends.length === 0 ? (
                <p className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">趋势数据还在积累中。</p>
              ) : (
                trends.map(trend => {
                  const width = `${Math.max((trend.count / maxTrendCount) * 100, 8)}%`
                  return (
                    <div key={trend.date}>
                      <div className="flex items-center justify-between text-sm text-slate-600">
                        <span>{trend.date}</span>
                        <span>{trend.count}</span>
                      </div>
                      <div className="mt-2 h-2 rounded-full bg-slate-100">
                        <div className="h-2 rounded-full bg-sky-500" style={{ width }} />
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

export default WorkspacePage
