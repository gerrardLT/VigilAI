import { Link, useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { Toast } from '../../components/Toast'
import { useProductSelectionTracking } from '../../hooks/useProductSelectionTracking'
import type { ProductSelectionTrackingStatus } from '../../types'
import { useEffect, useState } from 'react'

const FILTERS: Array<{ value: ProductSelectionTrackingStatus | undefined; label: string }> = [
  { value: undefined, label: '全部' },
  { value: 'saved', label: '已保存' },
  { value: 'tracking', label: '跟进中' },
  { value: 'done', label: '已完成' },
  { value: 'archived', label: '已归档' },
]

function formatPlatform(platform: string) {
  return platform === 'taobao' ? '淘宝' : platform === 'xianyu' ? '闲鱼' : platform
}

function formatSourceMode(mode: string) {
  if (mode === 'live') return '实时'
  if (mode === 'fallback') return '回退'
  if (mode === 'failed') return '失败'
  return mode
}

function formatFallbackReason(reason: string) {
  if (reason === 'search_shell_only') return '只有搜索壳页'
  if (reason === 'captcha_challenge') return '触发验证码'
  if (reason === 'weak_listing_evidence') return '商品证据较弱'
  if (reason === 'weak_page_level_match_only') return '仅页面级弱匹配'
  if (reason === 'no_structured_results_extracted') return '未提取到结构化结果'
  if (reason === 'live_fetch_failed') return '实时抓取失败'
  return reason
}

function formatTrackingStatus(value: ProductSelectionTrackingStatus) {
  if (value === 'saved') return '已保存'
  if (value === 'tracking') return '跟进中'
  if (value === 'done') return '已完成'
  if (value === 'archived') return '已归档'
  return value
}

export function SelectionTrackingPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { items, loading, error, filters, setFilters, updateTracking, deleteTracking, refetch } =
    useProductSelectionTracking(searchParams.get('status') as ProductSelectionTrackingStatus | undefined, {
      source_mode: (searchParams.get('source_mode') as 'live' | 'fallback' | '') || '',
      fallback_reason: searchParams.get('fallback_reason') || '',
    })
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const fallbackReasonOptions = Array.from(
    new Set(
      items
        .map(item => String(item.opportunity.source_diagnostics?.fallback_reason || ''))
        .filter(Boolean)
    )
  ).sort()

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams)
    const managedEntries: Array<[string, string | undefined]> = [
      ['status', filters.status || undefined],
      ['source_mode', filters.source_mode || undefined],
      ['fallback_reason', filters.fallback_reason || undefined],
    ]

    managedEntries.forEach(([key, value]) => {
      if (value) {
        nextParams.set(key, value)
      } else {
        nextParams.delete(key)
      }
    })

    const nextSerialized = nextParams.toString()
    const currentSerialized = searchParams.toString()
    if (nextSerialized !== currentSerialized) {
      setSearchParams(nextParams, { replace: true })
    }
  }, [filters, searchParams, setSearchParams])

  async function handleStatusChange(opportunityId: string, status: ProductSelectionTrackingStatus) {
    const result = await updateTracking(opportunityId, { status })
    setToast({
      type: result ? 'success' : 'error',
      message: result ? '选品跟进已更新。' : '更新选品跟进失败。',
    })
  }

  async function handleDelete(opportunityId: string) {
    const success = await deleteTracking(opportunityId)
    setToast({
      type: success ? 'success' : 'error',
      message: success ? '已移除选品跟进。' : '移除选品跟进失败。',
    })
  }

  if (loading && items.length === 0) {
    return <Loading text="正在加载选品跟进..." />
  }

  if (error && items.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void refetch()} />
  }

  return (
    <main className="space-y-6" data-testid="selection-tracking-page">
      {toast ? <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} /> : null}

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">选品跟进</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              管理已跟进的选品机会，并保持下一步行动队列清晰。
            </p>
          </div>
          <Link to="/selection/opportunities" className="btn btn-secondary">
            返回机会池
          </Link>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map(filter => {
            const active = filters.status === filter.value
            return (
              <button
                key={filter.label}
                type="button"
                onClick={() => setFilters({ status: filter.value })}
                className={`rounded-full px-4 py-2 text-sm font-medium ${
                  active ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {filter.label}
              </button>
            )
          })}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[180px_220px_auto]">
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">来源模式</span>
            <select
              value={filters.source_mode || ''}
              onChange={event =>
                setFilters({
                  source_mode: event.target.value as typeof filters.source_mode,
                  fallback_reason: event.target.value === 'live' ? '' : filters.fallback_reason,
                })
              }
              className="select w-full"
            >
              <option value="">全部模式</option>
              <option value="live">实时</option>
              <option value="fallback">回退</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">回退原因</span>
            <select
              value={filters.fallback_reason || ''}
              onChange={event => setFilters({ fallback_reason: event.target.value, source_mode: 'fallback' })}
              className="select w-full"
              disabled={fallbackReasonOptions.length === 0}
            >
              <option value="">全部回退原因</option>
              {fallbackReasonOptions.map(reason => (
                <option key={reason} value={reason}>
                  {formatFallbackReason(reason)}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setFilters({ status: undefined, source_mode: '', fallback_reason: '' })}
            >
              重置筛选
            </button>
          </div>
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void refetch()} /> : null}

      {items.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          还没有选品跟进条目。
        </section>
      ) : (
        <section className="space-y-4">
          {items.map(item => (
            <article
              key={item.opportunity_id}
              className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                      {formatPlatform(item.opportunity.platform)}
                    </span>
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                      {formatTrackingStatus(item.status)}
                    </span>
                    <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-800">
                      {formatSourceMode(item.opportunity.source_mode)}
                    </span>
                    {item.is_favorited ? (
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
                        已收藏
                      </span>
                    ) : null}
                  </div>
                  <div>
                    <Link
                      to={`/selection/opportunities/${item.opportunity.id}`}
                      className="text-xl font-semibold text-slate-900 hover:text-sky-700"
                    >
                      {item.opportunity.title}
                    </Link>
                    <p className="mt-1 text-sm text-slate-500">
                      机会分 {item.opportunity.opportunity_score.toFixed(1)} | 置信度{' '}
                      {item.opportunity.confidence_score.toFixed(1)}
                    </p>
                  </div>
                  {item.next_action ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      下一步：{item.next_action}
                    </div>
                  ) : null}
                  {item.opportunity.source_mode === 'fallback' ? (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                      来源说明：{formatFallbackReason(String(item.opportunity.source_diagnostics?.fallback_reason || 'unknown'))}
                    </div>
                  ) : null}
                  {item.notes ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      备注：{item.notes}
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn btn-secondary" onClick={() => void handleStatusChange(item.opportunity_id, 'tracking')}>
                    标记为跟进中
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => void handleStatusChange(item.opportunity_id, 'done')}>
                    标记为已完成
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => void handleStatusChange(item.opportunity_id, 'archived')}>
                    归档
                  </button>
                  <button type="button" className="btn btn-secondary text-red-600 hover:text-red-700" onClick={() => void handleDelete(item.opportunity_id)}>
                    移除
                  </button>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  )
}

export default SelectionTrackingPage

