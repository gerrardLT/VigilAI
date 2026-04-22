import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useAgentAnalysisJobs } from '../hooks/useAgentAnalysisJobs'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { useWorkspace } from '../hooks/useWorkspace'
import { api } from '../services/api'
import { CATEGORY_COLOR_MAP } from '../utils/constants'
import { formatDateOnly, formatDateTime } from '../utils/formatDate'
import type {
  ActivityListItem,
  AgentAnalysisJobDetail,
  AgentAnalysisJobSummary,
  Category,
  TrackingState,
} from '../types'

const CATEGORY_LABELS: Record<Category, string> = {
  hackathon: '黑客松',
  data_competition: '数据竞赛',
  coding_competition: '编程竞赛',
  other_competition: '其他比赛',
  airdrop: '空投',
  bounty: '悬赏',
  grant: '资助',
  dev_event: '开发者活动',
  news: '资讯',
}

function OverviewCard({
  label,
  value,
  hint,
  href,
}: {
  label: string
  value: string | number
  hint?: string
  href?: string
}) {
  const content = (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm transition-all hover:shadow-md">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-gray-900">{value}</div>
      {hint && <div className="mt-2 text-xs text-gray-500">{hint}</div>}
    </div>
  )

  if (href) {
    return <Link to={href}>{content}</Link>
  }

  return content
}

function countHighValueOpportunities(activities: ActivityListItem[]) {
  return activities.filter(activity => (activity.score ?? 0) >= 8 || Boolean(activity.prize?.amount)).length
}

function countUrgentActions(activities: ActivityListItem[]) {
  return activities.filter(
    activity => activity.deadline_level === 'urgent' || activity.deadline_level === 'soon'
  ).length
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

  return segments.join('，') + '。'
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
      counts.set(reason, (counts.get(reason) ?? 0) + 1)
    })
  })

  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 3)
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

const quickActions = [
  {
    testId: 'workspace-quick-action-opportunities',
    label: '查看机会池',
    description: '直接进入当前机会的评分排序视图。',
    href: '/activities?sort_by=score',
  },
  {
    testId: 'workspace-quick-action-tracking',
    label: '查看跟进列表',
    description: '继续推进已经收藏或跟进中的机会。',
    href: '/tracking',
  },
  {
    testId: 'workspace-quick-action-analysis-results',
    label: '查看分析结果',
    description: '查看当前模板的通过、观察和拦截结果流。',
    href: '/analysis/results',
  },
  {
    testId: 'workspace-quick-action-digest',
    label: '查看今日日报',
    description: '快速检查今天的摘要和推送内容。',
    href: '/digests',
  },
  {
    testId: 'workspace-quick-action-sources',
    label: '检查来源健康',
    description: '优先处理需要刷新或修复的来源。',
    href: '/sources',
  },
] as const

export function WorkspacePage() {
  const { defaultTemplate } = useAnalysisTemplates()
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

  if (loading && !workspace) {
    return <Loading text="正在加载工作台..." />
  }

  if (error && !workspace) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  if (!workspace) {
    return null
  }

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

  const topOpportunities = top_opportunities.map(activity => ({
    ...activity,
    ...opportunityOverrides[activity.id],
  }))

  const firstActions = first_actions.map(activity => ({
    ...activity,
    ...opportunityOverrides[activity.id],
  }))

  const highValueCount = countHighValueOpportunities(topOpportunities)
  const urgentActionCount = countUrgentActions(firstActions)
  const workspaceSnapshot = buildWorkspaceSnapshot({
    recentActivities: overview.recent_activities,
    highValueCount,
    urgentCount: urgentActionCount,
    alertCount: alert_sources.length,
  })
  const blockedReasonSummary = summarizeBlockedReasons(blocked_opportunities)
  const passRate = formatShare(analysis_overview.passed, analysis_overview.total)
  const watchRate = formatShare(analysis_overview.watch, analysis_overview.total)
  const rejectedRate = formatShare(analysis_overview.rejected, analysis_overview.total)
  const latestBatchJob = pickLatestBatchJob(agentJobs)
  const activeBatchJob = activeAgentJob?.scope_type === 'batch' ? activeAgentJob : null
  const draftReviewCount = countDraftReviewItems(activeBatchJob)
  const lowConfidenceCount = countLowConfidenceItems(activeBatchJob)
  const failedDraftCount = activeBatchJob
    ? activeBatchJob.items.filter(item => item.status === 'failed').length
    : latestBatchJob?.failed_items ?? 0

  function applyTrackingState(activityId: string, tracking: TrackingState) {
    setOpportunityOverrides(prev => ({
      ...prev,
      [activityId]: {
        is_tracking: true,
        is_favorited: tracking.is_favorited,
      },
    }))
  }

  async function handleTrack(activity: ActivityListItem) {
    setActionLoading(`track:${activity.id}`)

    try {
      const tracking = activity.is_tracking
        ? await api.updateTracking(activity.id, { status: 'tracking' })
        : await api.createTracking(activity.id, { status: 'tracking' })

      applyTrackingState(activity.id, tracking)
      setToast({
        type: 'success',
        message: activity.is_tracking ? '跟进状态已更新。' : '已加入跟进。',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新跟进失败'
      setToast({ type: 'error', message })
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
      setToast({
        type: 'success',
        message: tracking.is_favorited ? '已加入收藏。' : '已取消收藏。',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新收藏状态失败'
      setToast({ type: 'error', message })
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-8" data-testid="workspace-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <section className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-sky-900 p-8 text-white shadow-xl">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl space-y-4">
            <div className="text-sm uppercase tracking-[0.2em] text-sky-200">VigilAI Workspace</div>
            <h1 className="text-3xl font-bold">机会工作台</h1>
            <p className="leading-7 text-slate-100" data-testid="workspace-summary-banner">
              {workspaceSnapshot}
            </p>
            <p className="leading-7 text-slate-200">
              这里不是信息清单，而是你每天进入产品后的第一张行动面板。先处理高价值机会，再检查来源健康，最后把下一步跟进推进下去。
            </p>
            {defaultTemplate && (
              <div
                data-testid="workspace-default-template"
                className="inline-flex w-fit items-center rounded-full border border-sky-300/40 bg-white/10 px-4 py-2 text-sm text-sky-100"
              >
                当前 AI 模板：{defaultTemplate.name}
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

          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/10 p-4 text-sm text-slate-100">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-sky-100">最后更新</div>
                <div className="mt-1 font-medium">
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
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-black/10 p-3">
                <div className="text-xs text-sky-100">今日新增</div>
                <div className="mt-1 text-2xl font-semibold">{overview.recent_activities}</div>
              </div>
              <div className="rounded-xl bg-black/10 p-3">
                <div className="text-xs text-sky-100">待处理</div>
                <div className="mt-1 text-2xl font-semibold">{urgentActionCount}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5" data-testid="workspace-quick-actions">
        {quickActions.map(action => (
          <Link
            key={action.testId}
            to={action.href}
            data-testid={action.testId}
            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-200 hover:shadow-md"
          >
            <div className="text-sm font-semibold text-gray-900">{action.label}</div>
            <div className="mt-2 text-sm text-gray-500">{action.description}</div>
          </Link>
        ))}
      </section>

      <section
        data-testid="workspace-agent-analysis-summary"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Agent analysis summary</h2>
            <p className="mt-1 text-sm text-gray-500">
              聚焦当前默认模板、最新批次作业，以及待人工复核的 draft 工作量。
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

        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-900">Recent batch health</div>
            <div className="mt-2 text-sm text-slate-600">
              {latestBatchJob
                ? `状态 ${latestBatchJob.status}，共 ${latestBatchJob.item_count} 条，失败 ${latestBatchJob.failed_items} 条。`
                : '还没有批次分析作业，建议先启动一次批量 screening。'}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-900">Needs research</div>
            <div className="mt-2 text-sm text-slate-600">
              {latestBatchJob
                ? `${latestBatchJob.needs_research_count} 条机会需要补充 research。`
                : '暂无需要 research 的批次项。'}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-900">Blocked opportunities</div>
            <div className="mt-2 text-sm text-slate-600">
              当前有 {blocked_opportunities.length} 条被模板拦截，优先复核低信心和高价值机会。
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <OverviewCard label="今日新增" value={overview.recent_activities} hint="今天新进入系统的机会。" href="/activities?sort_by=created_at" />
        <OverviewCard label="高价值机会" value={highValueCount} hint="评分高或奖励明确的机会。" href="/activities?sort_by=score" />
        <OverviewCard label="72 小时内截止" value={urgentActionCount} hint="需要马上判断的机会。" href="/activities?deadline_level=urgent&sort_by=score" />
        <OverviewCard label="已跟进" value={overview.tracked_count} hint={`已收藏 ${overview.favorited_count} 条`} href="/tracking" />
        <OverviewCard label="异常来源" value={alert_sources.length} hint="需要排查或修复的抓取来源。" href="/sources" />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_1fr]">
        <div
          data-testid="workspace-analysis-overview"
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">当前模板表现</h2>
              <p className="mt-1 text-sm text-gray-500">快速查看当前 AI 模板是怎么筛机会的。</p>
            </div>
            {defaultTemplate && (
              <div className="rounded-full bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700">
                {defaultTemplate.name}
              </div>
            )}
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-emerald-50 p-4">
              <div className="text-xs uppercase tracking-wide text-emerald-700">通过</div>
              <div className="mt-2 text-3xl font-semibold text-emerald-800">{analysis_overview.passed}</div>
            </div>
            <div className="rounded-2xl bg-amber-50 p-4">
              <div className="text-xs uppercase tracking-wide text-amber-700">观察</div>
              <div className="mt-2 text-3xl font-semibold text-amber-800">{analysis_overview.watch}</div>
            </div>
            <div className="rounded-2xl bg-rose-50 p-4">
              <div className="text-xs uppercase tracking-wide text-rose-700">拦截</div>
              <div className="mt-2 text-3xl font-semibold text-rose-800">{analysis_overview.rejected}</div>
            </div>
          </div>

          <div
            data-testid="workspace-template-performance"
            className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4"
          >
            <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  {defaultTemplate ? `${defaultTemplate.name} 当前表现` : '模板当前表现'}
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  已覆盖 {analysis_overview.total} 条机会，当前通过率 {passRate}。
                </div>
              </div>
              <Link to="/analysis/templates" className="text-sm font-medium text-primary-600 transition hover:text-primary-700">
                去优化模板
              </Link>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-white p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">通过率</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{passRate}</div>
              </div>
              <div className="rounded-2xl bg-white p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">观察占比</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{watchRate}</div>
              </div>
              <div className="rounded-2xl bg-white p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">拦截占比</div>
                <div className="mt-2 text-2xl font-semibold text-slate-900">{rejectedRate}</div>
              </div>
            </div>

            <div className="mt-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">高频拦截原因</div>
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
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">被拦截的机会</h2>
              <p className="mt-1 text-sm text-gray-500">适合快速复核那些被当前模板挡掉的机会。</p>
            </div>
            <Link to="/activities?analysis_status=rejected" className="text-sm text-primary-600 hover:text-primary-700">
              查看全部
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {blocked_opportunities.length === 0 ? (
              <p className="text-sm text-gray-500">当前没有被拦截的机会。</p>
            ) : (
              blocked_opportunities.map(activity => (
                <Link
                  key={activity.id}
                  to={`/activities/${activity.id}`}
                  className="block rounded-2xl border border-rose-100 bg-rose-50/70 p-4 transition-all hover:border-rose-200 hover:bg-rose-50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium text-gray-900">{activity.title}</div>
                      <div className="mt-1 text-sm text-gray-600">
                        {activity.summary || activity.description || '被当前模板拦截。'}
                      </div>
                    </div>
                    <div className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-rose-700">
                      {activity.analysis_status || 'rejected'}
                    </div>
                  </div>
                  {activity.analysis_summary_reasons && activity.analysis_summary_reasons.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {activity.analysis_summary_reasons.slice(0, 2).map(reason => (
                        <span
                          key={`${activity.id}-${reason}`}
                          className="rounded-full border border-rose-200 bg-white px-2 py-1 text-xs text-rose-700"
                        >
                          {reason}
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

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_1fr]">
        <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">今天最值得先看的机会</h2>
              <p className="mt-1 text-sm text-gray-500">综合评分、时效和可信度排序。</p>
            </div>
            <Link to="/activities?sort_by=score" className="text-sm text-primary-600 hover:text-primary-700">
              查看全部
            </Link>
          </div>

          {topOpportunities.length === 0 ? (
            <p className="text-sm text-gray-500">今天还没有明显突出的机会。</p>
          ) : (
            <div className="space-y-4">
              {topOpportunities.map(activity => (
                <div
                  key={activity.id}
                  className="rounded-xl border border-gray-100 p-4 transition-all hover:border-primary-200 hover:shadow-sm"
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
                        可信度 {activity.trust_level}
                      </span>
                    )}
                    {activity.is_tracking && (
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                        跟进中
                      </span>
                    )}
                    {activity.is_favorited && (
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
                        已收藏
                      </span>
                    )}
                  </div>

                  <div className="mt-3 flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{activity.title}</h3>
                      <p className="mt-2 line-clamp-2 text-sm text-gray-600">
                        {activity.summary || activity.description || '暂无摘要'}
                      </p>
                      {activity.score_reason && <p className="mt-2 text-xs text-primary-700">{activity.score_reason}</p>}
                    </div>
                    <div className="min-w-[96px] text-right text-xs text-gray-500">
                      <div>{activity.source_name}</div>
                      <div className="mt-2">
                        {activity.dates?.deadline ? formatDateOnly(activity.dates.deadline) : '无截止时间'}
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
          <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">今日日报预览</h2>
              <Link to="/digests" className="text-sm text-primary-600 hover:text-primary-700">
                打开日报
              </Link>
            </div>
            {digest_preview ? (
              <div className="mt-4 space-y-4">
                <div>
                  <div className="text-sm text-gray-500">{digest_preview.digest_date}</div>
                  <div className="text-lg font-semibold text-gray-900">{digest_preview.title}</div>
                </div>
                {digest_preview.summary && <p className="text-sm text-gray-600">{digest_preview.summary}</p>}
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-500">1 分钟速览</div>
                  <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{digest_preview.content}</div>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-gray-200 p-4 text-sm text-gray-500">
                今天的日报还没生成。
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">最近 7 天趋势</h2>
              <div className="text-xs text-gray-500">新增机会数量</div>
            </div>
            <div className="mt-4 space-y-3">
              {trends.length === 0 ? (
                <p className="text-sm text-gray-500">趋势数据还在积累中。</p>
              ) : (
                trends.map(trend => {
                  const maxCount = Math.max(...trends.map(item => item.count), 1)
                  const width = `${Math.max((trend.count / maxCount) * 100, 8)}%`
                  return (
                    <div key={trend.date}>
                      <div className="flex items-center justify-between text-sm text-gray-600">
                        <span>{trend.date}</span>
                        <span>{trend.count}</span>
                      </div>
                      <div className="mt-1 h-2 rounded-full bg-slate-100">
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">异常来源</h2>
            <Link to="/sources" className="text-sm text-primary-600 hover:text-primary-700">
              去处理
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {alert_sources.length === 0 ? (
              <p className="text-sm text-gray-500">今天没有来源异常。</p>
            ) : (
              alert_sources.map(source => (
                <div key={source.id} className="rounded-xl border border-red-100 bg-red-50 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-gray-900">{source.name}</div>
                      <div className="mt-1 text-sm text-gray-600">
                        {source.error_message || '该来源需要人工排查。'}
                      </div>
                    </div>
                    <div className="text-xs uppercase tracking-wide text-red-700">{source.status}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">第一步动作</h2>
            <Link to="/tracking" className="text-sm text-primary-600 hover:text-primary-700">
              打开跟进
            </Link>
          </div>
          <div className="mt-2 text-sm text-gray-500">给自己一个清晰的下一步，而不是继续停留在浏览状态。</div>
          <div className="mt-4 space-y-3">
            {firstActions.length === 0 ? (
              <p className="text-sm text-gray-500">目前还没有需要立刻处理的动作。</p>
            ) : (
              firstActions.map(activity => (
                <Link
                  key={activity.id}
                  to={`/activities/${activity.id}`}
                  className="flex items-center justify-between gap-4 rounded-xl border border-gray-100 p-4 transition-all hover:border-primary-200 hover:bg-primary-50/30"
                >
                  <div>
                    <div className="font-medium text-gray-900">{activity.title}</div>
                    <div className="mt-1 text-sm text-gray-600">
                      {activity.summary || activity.score_reason || '下一步先处理这条机会。'}
                    </div>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <div>{activity.deadline_level || 'normal'}</div>
                    <div className="mt-1">
                      {activity.dates?.deadline ? formatDateOnly(activity.dates.deadline) : '无截止时间'}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

export default WorkspacePage
