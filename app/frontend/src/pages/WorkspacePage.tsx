import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useAgentAnalysisJobs } from '../hooks/useAgentAnalysisJobs'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { useTracking } from '../hooks/useTracking'
import { useWorkspace } from '../hooks/useWorkspace'
import { api } from '../services/api'
import type { ActivityListItem, TrackingItem } from '../types'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'
import { formatDateOnly, formatDateTime } from '../utils/formatDate'
import { localizeAnalysisTemplate } from '../utils/analysisI18n'

const DEFAULT_NEXT_ACTION = '先确认参赛要求，再拆出报名和交付准备'
const TRACKING_UPDATED_EVENT = 'vigilai:tracking-updated'

function cleanDigestExcerpt(content: string) {
  return content
    .replace(/\)\]\(/g, ' ')
    .replace(/https?:\/\/\S+/g, ' ')
    .replace(/\b\S*=\S*\b/g, ' ')
    .replace(/\bresize=\d+x\d+\b/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function isHighValue(activity: ActivityListItem) {
  return (activity.score ?? 0) >= 8
}

function isReminderToday(item: TrackingItem, now: Date) {
  if (!item.remind_at) return false
  const remindAt = new Date(item.remind_at)
  if (Number.isNaN(remindAt.getTime())) return false
  return (
    remindAt.getFullYear() === now.getFullYear() &&
    remindAt.getMonth() === now.getMonth() &&
    remindAt.getDate() === now.getDate()
  )
}

function isReminderOverdue(item: TrackingItem, now: Date) {
  if (!item.remind_at) return false
  const remindAt = new Date(item.remind_at)
  if (Number.isNaN(remindAt.getTime())) return false
  return remindAt.getTime() < now.getTime()
}

function isBacklog(item: TrackingItem, now: Date) {
  if (item.stage === 'to_decide') return true
  const updatedAt = new Date(item.updated_at)
  if (Number.isNaN(updatedAt.getTime())) return false
  return now.getTime() - updatedAt.getTime() > 48 * 60 * 60 * 1000
}

export function WorkspacePage() {
  const { workspace, loading, error, refetch } = useWorkspace()
  const { defaultTemplate } = useAnalysisTemplates()
  const { jobs, activeJob } = useAgentAnalysisJobs()
  const { items: trackingItems } = useTracking()

  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [closureFeedback, setClosureFeedback] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncNonce, setSyncNonce] = useState(0)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [trackingOverrides, setTrackingOverrides] = useState<Record<string, { is_tracking: boolean; is_favorited: boolean }>>({})

  useEffect(() => {
    const handleTrackingUpdated = () => {
      setSyncing(true)
      setSyncNonce(value => value + 1)
    }

    window.addEventListener(TRACKING_UPDATED_EVENT, handleTrackingUpdated)
    return () => window.removeEventListener(TRACKING_UPDATED_EVENT, handleTrackingUpdated)
  }, [])

  useEffect(() => {
    if (!syncing) return
    const timer = window.setTimeout(() => setSyncing(false), 120)
    return () => window.clearTimeout(timer)
  }, [syncing, syncNonce])

  const now = new Date()
  const localizedDefaultTemplate = defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null

  const reminderTodayItems = useMemo(
    () => trackingItems.filter(item => isReminderToday(item, now)),
    [trackingItems, syncNonce]
  )
  const reminderOverdueItems = useMemo(
    () => trackingItems.filter(item => isReminderOverdue(item, now)),
    [trackingItems, syncNonce]
  )
  const backlogItems = useMemo(
    () => trackingItems.filter(item => isBacklog(item, now)),
    [trackingItems, syncNonce]
  )

  if (loading && !workspace) {
    return <Loading text="正在加载工作台..." />
  }

  if (error && !workspace) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  if (!workspace) {
    return null
  }

  const topOpportunities = workspace.top_opportunities.map(item => ({
    ...item,
    ...(trackingOverrides[item.id] ?? {}),
  }))
  const firstActions = workspace.first_actions.map(item => ({
    ...item,
    ...(trackingOverrides[item.id] ?? {}),
  }))
  const untrackedHighValue = topOpportunities.filter(item => isHighValue(item) && !item.is_tracking)
  const batchJob = activeJob?.scope_type === 'batch' ? activeJob : jobs.find(job => job.scope_type === 'batch')
  const templatePassRate =
    workspace.analysis_overview && workspace.analysis_overview.total > 0
      ? `${Math.round((workspace.analysis_overview.passed / workspace.analysis_overview.total) * 100)}%`
      : '0%'

  async function pushToTracking(activity: ActivityListItem, source: 'track' | 'today' | 'convert') {
    setActionLoading(activity.id)
    try {
      const result = await api.createTracking(activity.id, {
        status: 'saved',
        stage: 'to_decide',
        next_action: DEFAULT_NEXT_ACTION,
        remind_at: null,
      })
      setTrackingOverrides(prev => ({
        ...prev,
        [activity.id]: { is_tracking: true, is_favorited: result.is_favorited },
      }))
      setClosureFeedback(source === 'today' ? '已加入推进，可去跟进页补全下一步。' : '已加入推进清单，可继续补全下一步。')
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : '加入推进失败' })
    } finally {
      setActionLoading(null)
    }
  }

  async function favoriteActivity(activity: ActivityListItem) {
    setActionLoading(`favorite-${activity.id}`)
    try {
      const result = await api.updateTracking(activity.id, { is_favorited: true })
      setTrackingOverrides(prev => ({
        ...prev,
        [activity.id]: { is_tracking: true, is_favorited: true },
      }))
      setClosureFeedback(result.is_favorited ? '已加入收藏，可去待判断列表继续推进。' : '收藏状态已更新。')
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : '收藏失败' })
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-6" data-testid="workspace-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <section className="rounded-[28px] bg-gradient-to-br from-slate-950 via-slate-900 to-sky-900 p-8 text-white">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.28em] text-sky-200">AI 智能代理决策驾驶舱</p>
            <h1 className="text-3xl font-semibold">机会工作台</h1>
            <p className="max-w-2xl text-sm text-slate-200" data-testid="workspace-summary-banner">
              今天新增 {workspace.overview.recent_activities} 条机会，跟进中 {workspace.overview.tracked_count} 条，收藏 {workspace.overview.favorited_count} 条。
            </p>
            <div className="flex flex-wrap gap-3">
              <div
                data-testid="workspace-default-template"
                className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm"
              >
                当前模板：{localizedDefaultTemplate?.name ?? '未设置'}
              </div>
              <button
                type="button"
                data-testid="workspace-refresh-button"
                onClick={() => {
                  void refetch()
                }}
                className="btn btn-secondary border-white/20 text-white hover:bg-white/10"
              >
                刷新
              </button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-white/10 p-4">
              <div className="text-xs text-sky-100">最近批量分析</div>
              <div className="mt-2 text-lg font-semibold">{batchJob?.id ?? '暂无'}</div>
            </div>
            <div className="rounded-2xl bg-white/10 p-4" data-testid="workspace-analysis-overview">
              <div className="text-xs text-sky-100">通过数量</div>
              <div className="mt-2 text-lg font-semibold">{workspace.analysis_overview?.passed ?? 0}</div>
            </div>
            <div className="rounded-2xl bg-white/10 p-4" data-testid="workspace-template-performance">
              <div className="text-xs text-sky-100">模板通过率</div>
              <div className="mt-2 text-lg font-semibold">{templatePassRate}</div>
            </div>
          </div>
        </div>
      </section>

      <section
        data-testid="workspace-agent-analysis-summary"
        className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-950">Agent 分析摘要</h2>
            <p className="mt-1 text-sm text-slate-600">
              当前模板 {localizedDefaultTemplate?.name ?? '未设置'}，最近批量任务 {batchJob?.finished_at ? formatDateTime(batchJob.finished_at) : '暂无结果'}。
            </p>
          </div>
          <Link to="/analysis/results" className="text-sm text-primary-700 hover:text-primary-800">
            查看分析结果
          </Link>
        </div>
      </section>

      {closureFeedback && (
        <section
          data-testid="workspace-closure-feedback"
          className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
        >
          {closureFeedback}
          <Link to="/tracking?stage=to_decide" className="ml-2 font-medium underline">
            去待判断列表
          </Link>
        </section>
      )}

      <section
        data-testid="workspace-sync-feedback"
        className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
      >
        {syncing ? '正在同步最新跟进结果...' : `当前跟进 ${workspace.overview.tracked_count} 条，超时提醒 ${reminderOverdueItems.length} 条。`}
      </section>

      <section data-testid="workspace-action-cards" className="grid gap-4 md:grid-cols-3 xl:grid-cols-7">
        <Link to="/activities?sort_by=created_at&sort_order=desc" data-testid="workspace-action-card-recent" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">今日新增</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{workspace.overview.recent_activities}</div>
        </Link>
        <Link to="/activities?sort_by=score&sort_order=desc" data-testid="workspace-action-card-high-value" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">高价值待看</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{untrackedHighValue.length}</div>
        </Link>
        <Link to="/tracking?focus=due_soon" data-testid="workspace-action-card-due-soon" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">临近截止</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{firstActions.length}</div>
        </Link>
        <Link to="/tracking?focus=backlog" data-testid="workspace-action-card-backlog" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">推进积压</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{backlogItems.length}</div>
        </Link>
        <Link to="/tracking?focus=remind_today" data-testid="workspace-action-card-remind-today" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">今日提醒</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{reminderTodayItems.length}</div>
        </Link>
        <Link to="/tracking?focus=remind_overdue" data-testid="workspace-action-card-remind-overdue" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">超时提醒</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{reminderOverdueItems.length}</div>
        </Link>
        <Link to="/sources" data-testid="workspace-action-card-alerts" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">源告警</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{workspace.alert_sources.length}</div>
        </Link>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <section data-testid="workspace-untracked-high-value-panel" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">高价值待转化</h2>
                <p className="mt-1 text-sm text-slate-600">先把高分机会转进推进流，再补下一步动作。</p>
              </div>
              <Link to="/activities?sort_by=score&sort_order=desc" className="text-sm text-primary-700 hover:text-primary-800">
                查看更多
              </Link>
            </div>
            <div className="space-y-4">
              {untrackedHighValue.slice(0, 3).map(activity => (
                <div key={activity.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium text-slate-950">{buildActivityDisplayTitle(activity)}</div>
                      <div className="mt-1 text-sm text-slate-600">
                        {buildActivityDisplayExcerpt(activity) || '暂无摘要'}
                      </div>
                    </div>
                    <button
                      type="button"
                      data-testid={`workspace-convert-track-${activity.id}`}
                      disabled={actionLoading === activity.id}
                      onClick={() => {
                        void pushToTracking(activity, 'convert')
                      }}
                      className="btn btn-primary"
                    >
                      转为跟进
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section data-testid="workspace-today-actions" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-slate-950">今日先做什么</h2>
              <p className="mt-1 text-sm text-slate-600">这批是今天最适合先推进的机会。</p>
            </div>
            <div className="space-y-4">
              {firstActions.slice(0, 3).map(activity => (
                <div key={activity.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium text-slate-950">{buildActivityDisplayTitle(activity)}</div>
                      <div className="mt-1 text-sm text-slate-600">
                        {buildActivityDisplayExcerpt(activity) || '暂无摘要'}
                      </div>
                    </div>
                    <button
                      type="button"
                      data-testid={`workspace-today-action-track-${activity.id}`}
                      disabled={actionLoading === activity.id}
                      onClick={() => {
                        void pushToTracking(activity, 'today')
                      }}
                      className="btn btn-primary"
                    >
                      加入推进
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">今日重点机会</h2>
                <p className="mt-1 text-sm text-slate-600">从首页直接完成加入推进和收藏。</p>
              </div>
            </div>
            <div className="space-y-4">
              {topOpportunities.map(activity => (
                <div key={activity.id} className="rounded-2xl border border-slate-200 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium text-slate-950">{buildActivityDisplayTitle(activity)}</div>
                      <div className="mt-1 text-sm text-slate-600">
                        {buildActivityDisplayExcerpt(activity) || '暂无摘要'}
                      </div>
                    </div>
                    <div className="text-sm text-slate-500">
                      {activity.dates?.deadline ? `截止 ${formatDateOnly(activity.dates.deadline)}` : '暂无截止时间'}
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link to={`/activities/${activity.id}`} className="btn btn-secondary">
                      查看详情
                    </Link>
                    <button
                      type="button"
                      data-testid={`workspace-track-${activity.id}`}
                      disabled={actionLoading === activity.id}
                      onClick={() => {
                        void pushToTracking(activity, 'track')
                      }}
                      className="btn btn-primary"
                    >
                      加入推进
                    </button>
                    <button
                      type="button"
                      data-testid={`workspace-favorite-${activity.id}`}
                      disabled={actionLoading === `favorite-${activity.id}`}
                      onClick={() => {
                        void favoriteActivity(activity)
                      }}
                      className="btn btn-secondary"
                    >
                      收藏
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section data-testid="workspace-backlog-panel" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">推进积压</h2>
                <p className="mt-1 text-sm text-slate-600">优先清掉长期未动和待判断项。</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {backlogItems.slice(0, 3).map(item => (
                <div key={item.activity_id} className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                  <div className="font-medium text-slate-950">{buildActivityDisplayTitle(item.activity)}</div>
                  <div className="mt-1">下一步：{item.next_action || '还没有明确下一步'}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <Link to="/tracking?focus=backlog" data-testid="workspace-backlog-link-backlog" className="text-primary-700 hover:text-primary-800">
                查看全部积压
              </Link>
              <Link to="/tracking?focus=backlog&stage=to_decide" data-testid="workspace-backlog-link-to-decide" className="text-primary-700 hover:text-primary-800">
                查看待判断
              </Link>
            </div>
          </section>

          <section data-testid="workspace-reminder-panel" className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div>
              <h2 className="text-xl font-semibold text-slate-950">提醒驱动推进</h2>
              <p className="mt-1 text-sm text-slate-600">把“今天该做”和“已经超时”的跟进工作单独拉出来。</p>
            </div>
            <div className="mt-4 grid gap-3">
              <Link to="/tracking?focus=remind_today" data-testid="workspace-reminder-link-today" className="rounded-2xl bg-sky-50 p-4">
                <div className="text-sm text-slate-500">今日提醒</div>
                <div className="mt-1 text-lg font-semibold text-slate-950">{reminderTodayItems.length}</div>
              </Link>
              <Link to="/tracking?focus=remind_overdue" data-testid="workspace-reminder-link-overdue" className="rounded-2xl bg-rose-50 p-4">
                <div className="text-sm text-slate-500">超时提醒</div>
                <div className="mt-1 text-lg font-semibold text-slate-950">{reminderOverdueItems.length}</div>
              </Link>
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">今日日报</h2>
                <p className="mt-1 text-sm text-slate-600">先看清洗后的摘要，再决定今天的处理顺序。</p>
              </div>
              <Link to="/digests" className="text-sm text-primary-700 hover:text-primary-800">
                打开日报
              </Link>
            </div>
            {workspace.digest_preview && (
              <div className="mt-4 space-y-3">
                <div className="text-sm text-slate-500">{workspace.digest_preview.digest_date}</div>
                <div data-testid="workspace-digest-excerpt" className="whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                  {cleanDigestExcerpt(workspace.digest_preview.content)}
                </div>
              </div>
            )}
          </section>
        </div>
      </section>
    </div>
  )
}

export default WorkspacePage
