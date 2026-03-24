import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Toast } from '../components/Toast'
import { useWorkspace } from '../hooks/useWorkspace'
import { Loading } from '../components/Loading'
import { ErrorMessage } from '../components/ErrorMessage'
import { api } from '../services/api'
import { formatDateOnly, formatDateTime } from '../utils/formatDate'
import { CATEGORY_COLOR_MAP } from '../utils/constants'
import { CATEGORY_LABELS, type ActivityListItem, type TrackingState } from '../types'

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
    <div className="rounded-xl bg-white shadow-sm border border-gray-100 p-5 transition-all hover:shadow-md">
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
    segments.push(`${args.highValueCount} 条值得优先看`)
  }

  if (args.urgentCount > 0) {
    segments.push(`${args.urgentCount} 条需要尽快处理`)
  }

  if (args.alertCount > 0) {
    segments.push(`${args.alertCount} 个来源需要关注`)
  } else {
    segments.push('来源状态稳定')
  }

  return `${segments.join('，')}。`
}

export function WorkspacePage() {
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
    return <Loading text="加载工作台..." />
  }

  if (error && !workspace) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  if (!workspace) {
    return null
  }

  const { overview, top_opportunities, digest_preview, trends, alert_sources, first_actions } = workspace

  const topOpportunities = useMemo(
    () =>
      top_opportunities.map(activity => ({
        ...activity,
        ...opportunityOverrides[activity.id],
      })),
    [opportunityOverrides, top_opportunities]
  )

  const firstActions = useMemo(
    () =>
      first_actions.map(activity => ({
        ...activity,
        ...opportunityOverrides[activity.id],
      })),
    [first_actions, opportunityOverrides]
  )

  const highValueCount = countHighValueOpportunities(topOpportunities)
  const urgentActionCount = countUrgentActions(firstActions)
  const workspaceSnapshot = buildWorkspaceSnapshot({
    recentActivities: overview.recent_activities,
    highValueCount,
    urgentCount: urgentActionCount,
    alertCount: alert_sources.length,
  })

  const quickActions = [
    {
      testId: 'workspace-quick-action-opportunities',
      label: '查看高优先机会',
      description: '按推荐分排序进入机会池',
      href: '/activities?sort_by=score',
    },
    {
      testId: 'workspace-quick-action-tracking',
      label: '查看跟进列表',
      description: '继续推进已收藏和已跟进事项',
      href: '/tracking',
    },
    {
      testId: 'workspace-quick-action-digest',
      label: '生成或查看日报',
      description: '快速回顾今天的重点变化',
      href: '/digests',
    },
    {
      testId: 'workspace-quick-action-sources',
      label: '检查来源健康',
      description: '优先处理异常来源和陈旧抓取',
      href: '/sources',
    },
  ]

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
        message: activity.is_tracking ? '已更新跟进状态' : '已加入跟进列表',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '加入跟进失败'
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
        message: tracking.is_favorited ? '已加入收藏' : '已取消收藏',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新收藏失败'
      setToast({ type: 'error', message })
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-8" data-testid="workspace-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <section className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-sky-900 text-white p-8 shadow-xl">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4 max-w-3xl">
            <div className="text-sm uppercase tracking-[0.2em] text-sky-200">VigilAI Workspace</div>
            <h1 className="text-3xl font-bold">机会工作台</h1>
            <p className="text-slate-100 leading-7" data-testid="workspace-summary-banner">
              {workspaceSnapshot}
            </p>
            <p className="text-slate-200 leading-7">
              这里不是信息清单，而是每天进入产品后的第一张行动面板。先处理高价值机会，再核查异常来源，
              最后把今天的跟进动作落下来。
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/activities?sort_by=score" className="btn bg-white text-slate-900 hover:bg-slate-100 border-0">
                查看机会池
              </Link>
              <Link to="/tracking" className="btn btn-secondary border-slate-300 text-white hover:bg-white/10">
                打开跟进列表
              </Link>
            </div>
          </div>
          <div className="w-full max-w-sm rounded-2xl bg-white/10 border border-white/10 p-4 text-sm text-slate-100">
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
                刷新工作台
              </button>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-black/10 p-3">
                <div className="text-xs text-sky-100">今日新增</div>
                <div className="mt-1 text-2xl font-semibold">{overview.recent_activities}</div>
              </div>
              <div className="rounded-xl bg-black/10 p-3">
                <div className="text-xs text-sky-100">需优先处理</div>
                <div className="mt-1 text-2xl font-semibold">{urgentActionCount}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" data-testid="workspace-quick-actions">
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

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <OverviewCard
          label="今日新增"
          value={overview.recent_activities}
          hint="从新增机会里快速找出今天的新信号"
          href="/activities?sort_by=created_at"
        />
        <OverviewCard
          label="高价值机会"
          value={highValueCount}
          hint="优先检查高分或带奖金的机会"
          href="/activities?sort_by=score"
        />
        <OverviewCard
          label="72h 内截止"
          value={urgentActionCount}
          hint="优先处理临近截止的事项"
          href="/activities?deadline_level=urgent&sort_by=score"
        />
        <OverviewCard
          label="已跟进"
          value={overview.tracked_count}
          hint={`已收藏 ${overview.favorited_count} 条，适合继续推进`}
          href="/tracking"
        />
        <OverviewCard
          label="异常来源"
          value={alert_sources.length}
          hint="需要核查抓取状态和来源健康"
          href="/sources"
        />
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_1fr]">
        <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">今天最值得先看的机会</h2>
              <p className="text-sm text-gray-500 mt-1">按价值、时效性和来源可信度综合排序</p>
            </div>
            <Link to="/activities?sort_by=score" className="text-sm text-primary-600 hover:text-primary-700">
              查看全部
            </Link>
          </div>

          {topOpportunities.length === 0 ? (
            <p className="text-sm text-gray-500">今天还没有明显突出的机会，建议先查看最新更新或完善关注偏好。</p>
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
                        Score {activity.score.toFixed(1)}
                      </span>
                    )}
                    {activity.trust_level && (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        Trust {activity.trust_level}
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
                      <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                        {activity.summary || activity.description || '暂无摘要'}
                      </p>
                      {activity.score_reason && (
                        <p className="mt-2 text-xs text-primary-700">{activity.score_reason}</p>
                      )}
                    </div>
                    <div className="text-right text-xs text-gray-500 min-w-[96px]">
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
          <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">今日摘要</h2>
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
                  <div className="mt-2 text-sm text-slate-700 whitespace-pre-wrap">{digest_preview.content}</div>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-gray-200 p-4 text-sm text-gray-500">
                今天的日报还没生成，先去生成一版摘要，再把它作为今天的行动底稿。
              </div>
            )}
          </section>

          <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">最近 7 天趋势</h2>
              <div className="text-xs text-gray-500">新增机会数量</div>
            </div>
            <div className="mt-4 space-y-3">
              {trends.length === 0 ? (
                <p className="text-sm text-gray-500">过去 7 天的数据还在积累中。</p>
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
        <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">异常来源</h2>
            <Link to="/sources" className="text-sm text-primary-600 hover:text-primary-700">
              去处理
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {alert_sources.length === 0 ? (
              <p className="text-sm text-gray-500">今天没有来源异常，抓取状态稳定。</p>
            ) : (
              alert_sources.map(source => (
                <div key={source.id} className="rounded-xl border border-red-100 bg-red-50 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-gray-900">{source.name}</div>
                      <div className="mt-1 text-sm text-gray-600">
                        {source.error_message || '最近成功更新时间较久，请检查来源可用性。'}
                      </div>
                    </div>
                    <div className="text-xs text-red-700 uppercase tracking-wide">{source.status}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">First Action</h2>
            <Link to="/tracking" className="text-sm text-primary-600 hover:text-primary-700">
              打开跟进页
            </Link>
          </div>
          <div className="mt-2 text-sm text-gray-500">给自己一个清晰的下一步，而不是停留在浏览状态。</div>
          <div className="mt-4 space-y-3">
            {firstActions.length === 0 ? (
              <p className="text-sm text-gray-500">目前没有需要立即处理的动作，先去机会池看看新的机会。</p>
            ) : (
              firstActions.map(activity => (
                <Link
                  key={activity.id}
                  to={`/activities/${activity.id}`}
                  className="flex items-center justify-between gap-4 rounded-xl border border-gray-100 p-4 hover:border-primary-200 hover:bg-primary-50/30 transition-all"
                >
                  <div>
                    <div className="font-medium text-gray-900">{activity.title}</div>
                    <div className="mt-1 text-sm text-gray-600">
                      {activity.summary || activity.score_reason || '优先处理这条机会'}
                    </div>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <div>{activity.deadline_level || 'normal'}</div>
                    <div className="mt-1">
                      {activity.dates?.deadline ? formatDateOnly(activity.dates.deadline) : '无截止'}
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
