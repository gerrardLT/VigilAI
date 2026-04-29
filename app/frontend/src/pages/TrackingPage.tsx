import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useTracking } from '../hooks/useTracking'
import type { TrackingItem, TrackingStageValue, TrackingUpsertRequest } from '../types'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'
import { formatDateOnly, formatDateTime } from '../utils/formatDate'
import { deriveTrackingStage, mapTrackingStageToStatus } from '../utils/trackingStage'

const BATCH_SUGGESTION = '今晚前确认资格并整理材料'

type FocusKey = 'all' | 'due_soon' | 'remind_overdue' | 'remind_today' | 'backlog'

function isSameDay(left: Date, right: Date) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  )
}

function parseDate(value: string | null | undefined) {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function toLocalInputValue(value: string | null | undefined) {
  const parsed = parseDate(value)
  if (!parsed) return ''
  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

function normalizeDateTimeLocal(value: string) {
  if (!value) return null
  return value
}

function getReminderToday(items: TrackingItem[], now: Date) {
  return items.filter(item => {
    const remindAt = parseDate(item.remind_at)
    return Boolean(remindAt && isSameDay(remindAt, now))
  })
}

function getReminderOverdue(items: TrackingItem[], now: Date) {
  return items.filter(item => {
    const remindAt = parseDate(item.remind_at)
    return Boolean(remindAt && remindAt.getTime() < now.getTime())
  })
}

function getDueToday(items: TrackingItem[], now: Date) {
  return items.filter(item => {
    const deadline = parseDate(item.activity.dates?.deadline)
    return Boolean(deadline && isSameDay(deadline, now))
  })
}

function getDueSoon(items: TrackingItem[], now: Date) {
  return items.filter(item => {
    const deadline = parseDate(item.activity.dates?.deadline)
    if (!deadline) return false
    const diff = deadline.getTime() - now.getTime()
    return diff >= 0 && diff <= 72 * 60 * 60 * 1000
  })
}

function getStale(items: TrackingItem[], now: Date) {
  return items.filter(item => {
    const updatedAt = parseDate(item.updated_at)
    if (!updatedAt) return false
    return now.getTime() - updatedAt.getTime() > 72 * 60 * 60 * 1000
  })
}

function isBacklog(item: TrackingItem, now: Date) {
  if (item.stage === 'to_decide') return true
  const updatedAt = parseDate(item.updated_at)
  if (!updatedAt) return false
  return now.getTime() - updatedAt.getTime() > 72 * 60 * 60 * 1000
}

function getEntryFeedback(focus: FocusKey, stage: string | null) {
  if (focus === 'remind_overdue') return '你是从超时提醒进入的，请先处理已经错过提醒时间的项目。'
  if (focus === 'backlog') return '你是从推进积压入口进入的，请优先补齐下一步并清理停滞项。'
  if (stage === 'to_decide') return '当前只看待判断项目，适合先做筛选和下一步定义。'
  if (focus === 'remind_today') return '当前只看今天要提醒的项目，适合安排今日执行顺序。'
  return '在这里统一处理截止、提醒、积压和推进状态。'
}

function getClosureFeedbackText(stage: TrackingStageValue) {
  if (stage === 'preparing') return '已批量切换为准备参与。'
  if (stage === 'dropped') return '已标记为放弃，可查看已放弃列表。'
  if (stage === 'submitted') return '已标记为已提交。'
  return '跟进状态已更新。'
}

export function TrackingPage() {
  const {
    items,
    loading,
    error,
    refetch,
    updateTracking,
    batchUpdateTracking,
    deleteTracking,
  } = useTracking()

  const [searchParams] = useSearchParams()
  const focus = (searchParams.get('focus') as FocusKey | null) ?? 'all'
  const stage = searchParams.get('stage')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [closureFeedback, setClosureFeedback] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [batchNextAction, setBatchNextAction] = useState('')
  const [focusFilter, setFocusFilter] = useState<FocusKey>(focus)
  const [draftValues, setDraftValues] = useState<Record<string, { stage: TrackingStageValue; block_reason: string; abandon_reason: string; remind_at: string }>>({})

  const now = new Date()

  const dueTodayItems = useMemo(() => getDueToday(items, now), [items])
  const dueSoonItems = useMemo(() => getDueSoon(items, now), [items])
  const remindTodayItems = useMemo(() => getReminderToday(items, now), [items])
  const remindOverdueItems = useMemo(() => getReminderOverdue(items, now), [items])
  const staleItems = useMemo(() => getStale(items, now), [items])
  const backlogItems = useMemo(() => items.filter(item => isBacklog(item, now)), [items])

  const filteredItems = useMemo(() => {
    let next = [...items]
    if (focusFilter === 'due_soon') next = dueSoonItems
    if (focusFilter === 'remind_overdue') next = remindOverdueItems
    if (focusFilter === 'remind_today') next = remindTodayItems
    if (focusFilter === 'backlog') next = backlogItems
    if (stage) next = next.filter(item => deriveTrackingStage(item) === stage)
    return next
  }, [items, focusFilter, stage, dueSoonItems, remindOverdueItems, remindTodayItems, backlogItems])

  function getDraft(item: TrackingItem) {
    return (
      draftValues[item.activity_id] ?? {
        stage: deriveTrackingStage(item),
        block_reason: item.block_reason ?? '',
        abandon_reason: item.abandon_reason ?? '',
        remind_at: toLocalInputValue(item.remind_at),
      }
    )
  }

  function patchDraft(
    activityId: string,
    current: { stage: TrackingStageValue; block_reason: string; abandon_reason: string; remind_at: string },
    partial: Partial<{ stage: TrackingStageValue; block_reason: string; abandon_reason: string; remind_at: string }>
  ) {
    setDraftValues(prev => ({
      ...prev,
      [activityId]: {
        ...(prev[activityId] ?? current),
        ...partial,
      },
    }))
  }

  function toggleSelected(activityId: string) {
    setSelectedIds(prev => (prev.includes(activityId) ? prev.filter(id => id !== activityId) : [...prev, activityId]))
  }

  async function handleDone(activityId: string) {
    await updateTracking(activityId, { status: 'done', stage: 'submitted' })
  }

  async function handleBatchPreparing() {
    const payload: TrackingUpsertRequest = {
      status: 'tracking',
      stage: 'preparing',
      next_action: batchNextAction,
      remind_at: undefined,
    }
    const success = await batchUpdateTracking(selectedIds, payload)
    if (success) {
      setClosureFeedback('批量处理完成，已切到准备参与。')
      setSelectedIds([])
    }
  }

  async function handleSave(item: TrackingItem) {
    const draft = getDraft(item)
    const nextStage = draft.stage
    const payload: TrackingUpsertRequest = {
      status: mapTrackingStageToStatus(nextStage),
      stage: nextStage,
      next_action: item.next_action,
      remind_at: normalizeDateTimeLocal(draft.remind_at),
      block_reason: draft.block_reason || null,
      abandon_reason: draft.abandon_reason || null,
    }
    await updateTracking(item.activity_id, payload)
    setClosureFeedback(getClosureFeedbackText(nextStage))
  }

  if (loading && items.length === 0) {
    return <Loading text="正在加载跟进列表..." />
  }

  if (error && items.length === 0) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  return (
    <div className="space-y-6" data-testid="tracking-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">跟进页</h1>
          <p className="mt-1 text-sm text-slate-600">把待判断、提醒、截止和推进状态集中处理。</p>
        </div>
        <Link to="/activities" className="btn btn-secondary">
          查看机会池
        </Link>
      </div>

      <section
        data-testid="tracking-entry-feedback"
        className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950"
      >
        {getEntryFeedback(focusFilter, stage)}
      </section>

      {closureFeedback && (
        <section
          data-testid="tracking-closure-feedback"
          className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
        >
          {closureFeedback}
          {closureFeedback.includes('放弃') && (
            <Link to="/tracking?stage=dropped" className="ml-2 underline">
              查看已放弃
            </Link>
          )}
        </section>
      )}

      <section data-testid="tracking-reminder-strip" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-950">今日跟进焦点</h2>
          <p className="mt-1 text-sm text-slate-600">先看截止，再看提醒，最后处理长期停滞项目。</p>
        </div>
        <div className="grid gap-3 md:grid-cols-5">
          <button type="button" data-testid="tracking-focus-due-soon" onClick={() => setFocusFilter('due_soon')} className="rounded-2xl bg-amber-50 p-4 text-left">
            <div className="text-xs text-slate-500">即将截止</div>
            <div data-testid="tracking-summary-due-soon-count" className="mt-2 text-2xl font-semibold text-slate-950">{dueSoonItems.length}</div>
          </button>
          <div className="rounded-2xl bg-rose-50 p-4">
            <div className="text-xs text-slate-500">今日截止</div>
            <div data-testid="tracking-summary-due-today-count" className="mt-2 text-2xl font-semibold text-slate-950">{dueTodayItems.length}</div>
          </div>
          <div className="rounded-2xl bg-sky-50 p-4">
            <div className="text-xs text-slate-500">今日提醒</div>
            <div data-testid="tracking-summary-remind-today-count" className="mt-2 text-2xl font-semibold text-slate-950">{remindTodayItems.length}</div>
          </div>
          <button type="button" data-testid="tracking-focus-remind-overdue" onClick={() => setFocusFilter('remind_overdue')} className="rounded-2xl bg-rose-50 p-4 text-left">
            <div className="text-xs text-slate-500">超时提醒</div>
            <div data-testid="tracking-summary-remind-overdue-count" className="mt-2 text-2xl font-semibold text-slate-950">{remindOverdueItems.length}</div>
          </button>
          <div className="rounded-2xl bg-slate-100 p-4">
            <div className="text-xs text-slate-500">长时间未处理</div>
            <div data-testid="tracking-summary-stale-count" className="mt-2 text-2xl font-semibold text-slate-950">{staleItems.length}</div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
        <section data-testid="tracking-list" className="space-y-4">
          {selectedIds.length > 0 && (
            <div data-testid="tracking-batch-toolbar" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-center">
                <input
                  data-testid="tracking-batch-next-action"
                  value={batchNextAction}
                  onChange={event => setBatchNextAction(event.target.value)}
                  placeholder="填写统一下一步动作"
                  className="input flex-1"
                />
                <button
                  type="button"
                  data-testid="tracking-batch-fill-suggestion"
                  onClick={() => setBatchNextAction(BATCH_SUGGESTION)}
                  className="btn btn-secondary"
                >
                  填入建议动作
                </button>
                <button
                  type="button"
                  data-testid="tracking-batch-preparing"
                  onClick={() => {
                    void handleBatchPreparing()
                  }}
                  className="btn btn-primary"
                >
                  设为准备参与
                </button>
              </div>
            </div>
          )}

          {filteredItems.map(item => {
            const draft = getDraft(item)
            return (
              <article key={item.activity_id} data-testid={`tracking-card-${item.activity_id}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        data-testid={`tracking-select-${item.activity_id}`}
                        checked={selectedIds.includes(item.activity_id)}
                        onChange={() => toggleSelected(item.activity_id)}
                      />
                      <Link to={`/activities/${item.activity.id}`} className="text-lg font-semibold text-slate-950 hover:text-primary-700">
                        {buildActivityDisplayTitle(item.activity)}
                      </Link>
                    </div>
                    <p className="text-sm text-slate-600">{buildActivityDisplayExcerpt(item.activity) || '暂无摘要'}</p>
                    <div className="grid gap-3 md:grid-cols-2">
                      <label className="space-y-1 text-sm">
                        <span className="text-slate-500">推进阶段</span>
                        <select
                          data-testid={`tracking-stage-${item.activity_id}`}
                          value={draft.stage}
                          onChange={event => patchDraft(item.activity_id, draft, { stage: event.target.value as TrackingStageValue })}
                          className="select w-full"
                        >
                          <option value="to_decide">待判断</option>
                          <option value="watching">已关注</option>
                          <option value="preparing">准备参与</option>
                          <option value="submitted">已提交</option>
                          <option value="dropped">已放弃</option>
                        </select>
                      </label>
                      <label className="space-y-1 text-sm">
                        <span className="text-slate-500">提醒时间</span>
                        <input
                          type="datetime-local"
                          value={draft.remind_at}
                          onChange={event => patchDraft(item.activity_id, draft, { remind_at: event.target.value })}
                          className="input w-full"
                        />
                      </label>
                      <label className="space-y-1 text-sm">
                        <span className="text-slate-500">阻塞原因</span>
                        <input
                          data-testid={`tracking-block-reason-${item.activity_id}`}
                          value={draft.block_reason}
                          onChange={event => patchDraft(item.activity_id, draft, { block_reason: event.target.value })}
                          className="input w-full"
                        />
                      </label>
                      <label className="space-y-1 text-sm">
                        <span className="text-slate-500">放弃原因</span>
                        <input
                          data-testid={`tracking-abandon-reason-${item.activity_id}`}
                          value={draft.abandon_reason}
                          onChange={event => patchDraft(item.activity_id, draft, { abandon_reason: event.target.value })}
                          className="input w-full"
                        />
                      </label>
                    </div>
                    <div className="text-sm text-slate-500">
                      下一步：{item.next_action || '未填写'} | 截止：{item.activity.dates?.deadline ? formatDateOnly(item.activity.dates.deadline) : '暂无'}
                    </div>
                    <div className="text-xs text-slate-400">最近更新：{formatDateTime(item.updated_at)}</div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <button type="button" data-testid={`tracking-done-${item.activity_id}`} onClick={() => { void handleDone(item.activity_id) }} className="btn btn-secondary">
                      标记完成
                    </button>
                    <button
                      type="button"
                      data-testid={`tracking-save-${item.activity_id}`}
                      onClick={() => {
                        void handleSave(item)
                      }}
                      className="btn btn-primary"
                    >
                      保存
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        void deleteTracking(item.activity_id)
                      }}
                      className="btn btn-secondary"
                    >
                      移除
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </section>

        <aside className="space-y-4">
          <section data-testid="tracking-backlog-panel" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-950">推进积压</h2>
            <div className="mt-3 space-y-3">
              {backlogItems.map(item => (
                <div key={item.activity_id} className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                  <div className="font-medium text-slate-950">{buildActivityDisplayTitle(item.activity)}</div>
                  <div className="mt-1">下一步：{item.next_action || '待补充'}</div>
                </div>
              ))}
            </div>
          </section>

          <section data-testid="tracking-alerts-panel" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-950">提醒面板</h2>
              <Link to="/tracking" className="text-sm text-primary-700 hover:text-primary-800">
                查看全部
              </Link>
            </div>
            <div className="mt-4 space-y-3">
              <div className="rounded-2xl bg-rose-50 p-3 text-sm text-slate-800">今日截止 {dueTodayItems.length} 条</div>
              <div className="rounded-2xl bg-rose-50 p-3 text-sm text-slate-800">超时提醒 {remindOverdueItems.length} 条</div>
              <div className="rounded-2xl bg-slate-100 p-3 text-sm text-slate-800">长时间未处理 {staleItems.length} 条</div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}

export default TrackingPage
