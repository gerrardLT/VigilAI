import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useTracking } from '../hooks/useTracking'
import type { TrackingItem, TrackingStatus } from '../types'
import { getTrackingStatusLabel, localizeAnalysisText } from '../utils/analysisI18n'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'
import { daysUntil, formatDateOnly, formatDateTime } from '../utils/formatDate'

const FILTERS: Array<{ value: TrackingStatus | undefined; label: string }> = [
  { value: undefined, label: '全部' },
  { value: 'saved', label: '已保存' },
  { value: 'tracking', label: '跟进中' },
  { value: 'done', label: '已完成' },
  { value: 'archived', label: '已归档' },
]

const STATUS_STYLES: Record<TrackingStatus, string> = {
  saved: 'bg-slate-100 text-slate-700',
  tracking: 'bg-sky-100 text-sky-700',
  done: 'bg-emerald-100 text-emerald-700',
  archived: 'bg-gray-100 text-gray-600',
}

type FocusFilter = 'all' | 'due_today' | 'due_soon' | 'needs_action'

function parseDate(dateString: string | null | undefined) {
  if (!dateString) {
    return null
  }

  const parsed = new Date(dateString)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function getHoursUntil(dateString: string | null | undefined, now: Date) {
  const parsed = parseDate(dateString)
  if (!parsed) {
    return null
  }

  return (parsed.getTime() - now.getTime()) / (1000 * 60 * 60)
}

function isSameLocalDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function isDueToday(item: TrackingItem, now: Date) {
  const deadline = parseDate(item.activity.dates?.deadline)
  return Boolean(deadline && isSameLocalDay(deadline, now))
}

function isDueSoon(item: TrackingItem, now: Date) {
  const hoursUntil = getHoursUntil(item.activity.dates?.deadline, now)
  return hoursUntil !== null && hoursUntil >= 0 && hoursUntil <= 72
}

function isRecentUpdate(item: TrackingItem, now: Date) {
  const updatedAt = parseDate(item.updated_at)
  if (!updatedAt) {
    return false
  }

  return now.getTime() - updatedAt.getTime() <= 24 * 60 * 60 * 1000
}

function isStale(item: TrackingItem, now: Date) {
  const updatedAt = parseDate(item.updated_at)
  if (!updatedAt || item.status === 'done' || item.status === 'archived') {
    return false
  }

  return now.getTime() - updatedAt.getTime() > 72 * 60 * 60 * 1000
}

function isNeedsAction(item: TrackingItem) {
  return item.status === 'saved' || item.status === 'tracking'
}

function getDeadlineTone(item: TrackingItem, now: Date) {
  const hoursUntil = getHoursUntil(item.activity.dates?.deadline, now)

  if (hoursUntil === null) {
    return {
      label: '无截止',
      className: 'bg-slate-100 text-slate-700',
    }
  }

  if (hoursUntil < 0) {
    return {
      label: '已截止',
      className: 'bg-gray-200 text-gray-700',
    }
  }

  if (hoursUntil <= 24) {
    return {
      label: '今日截止',
      className: 'bg-rose-100 text-rose-700',
    }
  }

  if (hoursUntil <= 72) {
    return {
      label: '72 小时内截止',
      className: 'bg-amber-100 text-amber-700',
    }
  }

  return {
    label: `${daysUntil(item.activity.dates?.deadline) ?? '--'} 天后`,
    className: 'bg-sky-100 text-sky-700',
  }
}

function getSortWeight(item: TrackingItem, now: Date) {
  if (isDueToday(item, now)) {
    return 0
  }

  if (isDueSoon(item, now)) {
    return 1
  }

  if (isRecentUpdate(item, now)) {
    return 2
  }

  if (isStale(item, now)) {
    return 4
  }

  return 3
}

function sortTrackingItems(items: TrackingItem[], now: Date) {
  return [...items].sort((left, right) => {
    const weightDifference = getSortWeight(left, now) - getSortWeight(right, now)
    if (weightDifference !== 0) {
      return weightDifference
    }

    return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
  })
}

export function TrackingPage() {
  const {
    items,
    loading,
    error,
    statusFilter,
    setStatusFilter,
    refetch,
    updateTracking,
    deleteTracking,
  } = useTracking()
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [focusFilter, setFocusFilter] = useState<FocusFilter>('all')
  const dueTodayItems = useMemo(() => {
    const currentTime = new Date()
    return items.filter(item => isDueToday(item, currentTime))
  }, [items])
  const dueSoonItems = useMemo(() => {
    const currentTime = new Date()
    return items.filter(item => isDueSoon(item, currentTime))
  }, [items])
  const recentUpdatedItems = useMemo(() => {
    const currentTime = new Date()
    return items.filter(item => isRecentUpdate(item, currentTime))
  }, [items])
  const staleItems = useMemo(() => {
    const currentTime = new Date()
    return items.filter(item => isStale(item, currentTime))
  }, [items])
  const itemsByStatus = useMemo(
    () =>
      items.reduce<Record<string, number>>((accumulator, item) => {
        accumulator[item.status] = (accumulator[item.status] ?? 0) + 1
        return accumulator
      }, {}),
    [items]
  )

  const filteredItems = useMemo(() => {
    const currentTime = new Date()
    let nextItems = items

    if (focusFilter === 'due_today') {
      nextItems = nextItems.filter(item => isDueToday(item, currentTime))
    } else if (focusFilter === 'due_soon') {
      nextItems = nextItems.filter(item => isDueSoon(item, currentTime))
    } else if (focusFilter === 'needs_action') {
      nextItems = nextItems.filter(isNeedsAction)
    }

    return sortTrackingItems(nextItems, currentTime)
  }, [focusFilter, items])

  async function handleStatusChange(activityId: string, status: TrackingStatus) {
    setActionLoading(`${activityId}:${status}`)
    const result = await updateTracking(activityId, { status })
    setActionLoading(null)

    if (result) {
      setToast({ type: 'success', message: '跟进状态已更新' })
    } else {
      setToast({ type: 'error', message: '更新跟进状态失败' })
    }
  }

  async function handleDelete(activityId: string) {
    setActionLoading(`${activityId}:delete`)
    const success = await deleteTracking(activityId)
    setActionLoading(null)

    if (success) {
      setToast({ type: 'success', message: '已从跟进列表移除' })
    } else {
      setToast({ type: 'error', message: '移除失败' })
    }
  }

  if (loading && items.length === 0) {
    return <Loading text="加载跟进列表..." />
  }

  if (error && items.length === 0) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  return (
    <div className="space-y-6" data-testid="tracking-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">跟进</h1>
          <p className="mt-1 text-sm text-gray-500">管理你已关注的机会、下一步动作和临近截止提醒。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="tracking-focus-due-soon"
            onClick={() => setFocusFilter('due_soon')}
            className="btn btn-secondary"
          >
            只看临近截止
          </button>
          <button
            type="button"
            data-testid="tracking-focus-needs-action"
            onClick={() => setFocusFilter('needs_action')}
            className="btn btn-secondary"
          >
            只看待处理
          </button>
          <Link to="/activities" className="btn btn-secondary">
            回到机会池
          </Link>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map(filter => {
            const active = statusFilter === filter.value
            const count = filter.value === undefined ? items.length : itemsByStatus[filter.value] ?? 0

            return (
              <button
                key={filter.label}
                onClick={() => setStatusFilter(filter.value)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  active ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filter.label} {count > 0 ? `(${count})` : ''}
              </button>
            )
          })}
        </div>
      </div>

      <section className="rounded-2xl border border-sky-100 bg-sky-50/80 p-5" data-testid="tracking-reminder-strip">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-xs tracking-[0.2em] text-sky-600">今日跟进焦点</div>
            <div className="mt-2 text-lg font-semibold text-slate-900">
              今天有 {dueTodayItems.length} 条机会今日截止，{dueSoonItems.length} 条机会将在 72 小时内截止。
            </div>
            <div className="mt-1 text-sm text-slate-600">
              另外还有 {staleItems.length} 条机会已经超过 3 天没有处理，适合优先清理。
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="tracking-focus-due-today"
              onClick={() => setFocusFilter('due_today')}
              className="btn btn-secondary"
            >
              只看今日截止
            </button>
            <button type="button" onClick={() => setFocusFilter('all')} className="btn btn-secondary">
              查看全部
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-xl bg-white/90 p-4">
            <div className="text-xs text-slate-500">今日截止</div>
            <div className="mt-2 text-2xl font-semibold text-slate-900" data-testid="tracking-summary-due-today-count">
              {dueTodayItems.length}
            </div>
          </div>
          <div className="rounded-xl bg-white/90 p-4">
            <div className="text-xs text-slate-500">72 小时内截止</div>
            <div className="mt-2 text-2xl font-semibold text-slate-900" data-testid="tracking-summary-due-soon-count">
              {dueSoonItems.length}
            </div>
          </div>
          <div className="rounded-xl bg-white/90 p-4">
            <div className="text-xs text-slate-500">长时间未处理</div>
            <div className="mt-2 text-2xl font-semibold text-slate-900" data-testid="tracking-summary-stale-count">
              {staleItems.length}
            </div>
          </div>
        </div>
      </section>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center shadow-sm">
          <div className="text-lg font-medium text-gray-900">你还没有加入任何跟进机会</div>
          <p className="mt-2 text-sm text-gray-500">
            从工作台或机会池中选择值得关注的机会，加入跟进后会在这里持续管理。
          </p>
          <div className="mt-4 flex justify-center gap-3">
            <Link to="/workspace" className="btn btn-secondary">
              去工作台
            </Link>
            <Link to="/activities" className="btn btn-primary">
              去机会池
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_320px]">
          <div className="space-y-4" data-testid="tracking-list">
            {filteredItems.length === 0 ? (
              <div className="rounded-2xl border border-gray-100 bg-white p-8 text-center text-sm text-gray-500 shadow-sm">
                当前筛选下没有匹配的跟进项，试试切回全部或查看机会池。
              </div>
            ) : (
              filteredItems.map(item => {
                const deadlineTone = getDeadlineTone(item, new Date())

                return (
                  <div
                    key={item.activity_id}
                    data-testid={`tracking-card-${item.activity_id}`}
                    className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Link
                            to={`/activities/${item.activity.id}`}
                            className="text-lg font-semibold text-gray-900 hover:text-primary-700"
                          >
                            {buildActivityDisplayTitle(item.activity)}
                          </Link>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_STYLES[item.status]}`}>
                            {getTrackingStatusLabel(item.status)}
                          </span>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${deadlineTone.className}`}>
                            {deadlineTone.label}
                          </span>
                          {item.is_favorited && (
                            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                              已收藏
                            </span>
                          )}
                        </div>

                        <div className="text-sm text-gray-600">
                          {buildActivityDisplayExcerpt(item.activity) || '暂无摘要'}
                        </div>

                        <div className="grid gap-2 text-sm text-gray-500 md:grid-cols-3">
                          <div>来源：{localizeAnalysisText(item.activity.source_name)}</div>
                          <div>下一步：{localizeAnalysisText(item.next_action) || '未填写'}</div>
                          <div>提醒：{item.remind_at ? formatDateTime(item.remind_at) : '未设置'}</div>
                        </div>

                        {item.notes && (
                          <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                            {localizeAnalysisText(item.notes)}
                          </div>
                        )}

                        <div className="text-xs text-gray-400">
                          更新时间：{formatDateTime(item.updated_at)}
                          {item.activity.dates?.deadline && ` · 截止：${formatDateOnly(item.activity.dates.deadline)}`}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 lg:justify-end">
                        <Link to={`/activities/${item.activity.id}`} className="btn btn-secondary">
                          查看详情
                        </Link>
                        <button
                          data-testid={`tracking-done-${item.activity_id}`}
                          onClick={() => handleStatusChange(item.activity_id, 'done')}
                          disabled={actionLoading === `${item.activity_id}:done`}
                          className="btn btn-secondary"
                        >
                          标记完成
                        </button>
                        <button
                          onClick={() => handleStatusChange(item.activity_id, 'tracking')}
                          disabled={actionLoading === `${item.activity_id}:tracking`}
                          className="btn btn-secondary"
                        >
                          继续跟进
                        </button>
                        <button
                          onClick={() => handleStatusChange(item.activity_id, 'archived')}
                          disabled={actionLoading === `${item.activity_id}:archived`}
                          className="btn btn-secondary"
                        >
                          归档
                        </button>
                        <button
                          onClick={() => handleDelete(item.activity_id)}
                          disabled={actionLoading === `${item.activity_id}:delete`}
                          className="btn btn-secondary text-red-600 hover:text-red-700"
                        >
                          移除
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          <aside className="space-y-4" data-testid="tracking-alerts-panel">
            <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
              <div className="text-lg font-semibold text-gray-900">今日截止</div>
              <div className="mt-3 space-y-3">
                {dueTodayItems.length > 0 ? (
                  dueTodayItems.map(item => (
                    <Link
                      key={`today-${item.activity_id}`}
                      to={`/activities/${item.activity.id}`}
                      className="block rounded-xl border border-rose-100 bg-rose-50 p-3 text-sm"
                    >
                      <div className="font-medium text-gray-900">{buildActivityDisplayTitle(item.activity)}</div>
                      <div className="mt-1 text-rose-700">
                        {item.activity.dates?.deadline ? formatDateTime(item.activity.dates.deadline) : '今天处理'}
                      </div>
                    </Link>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">今天没有立即到期的机会。</div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
              <div className="text-lg font-semibold text-gray-900">最近更新</div>
              <div className="mt-3 space-y-3">
                {recentUpdatedItems.length > 0 ? (
                  recentUpdatedItems.map(item => (
                    <Link
                      key={`recent-${item.activity_id}`}
                      to={`/activities/${item.activity.id}`}
                      className="block rounded-xl border border-sky-100 bg-sky-50 p-3 text-sm"
                    >
                      <div className="font-medium text-gray-900">{buildActivityDisplayTitle(item.activity)}</div>
                      <div className="mt-1 text-sky-700">更新于 {formatDateTime(item.updated_at)}</div>
                    </Link>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">最近 24 小时没有新的状态变化。</div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
              <div className="text-lg font-semibold text-gray-900">长时间未处理</div>
              <div className="mt-3 space-y-3">
                {staleItems.length > 0 ? (
                  staleItems.map(item => (
                    <Link
                      key={`stale-${item.activity_id}`}
                      to={`/activities/${item.activity.id}`}
                      className="block rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm"
                    >
                      <div className="font-medium text-gray-900">{buildActivityDisplayTitle(item.activity)}</div>
                      <div className="mt-1 text-amber-700">上次更新 {formatDateTime(item.updated_at)}</div>
                    </Link>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">当前没有拖延过久的跟进事项。</div>
                )}
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}

export default TrackingPage
