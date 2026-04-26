import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { Toast } from '../../components/Toast'
import { productSelectionApi } from '../../services/productSelectionApi'
import type { ProductSelectionOpportunityDetail } from '../../types'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? 'Taobao' : platform === 'xianyu' ? 'Xianyu' : platform
}

function formatPriceRange(low: number | null, mid: number | null, high: number | null) {
  const values = [low, mid, high].filter((value): value is number => value !== null)
  if (values.length === 0) return 'N/A'
  if (values.length === 1) return `¥${values[0].toFixed(0)}`
  return `¥${Math.min(...values).toFixed(0)} - ¥${Math.max(...values).toFixed(0)}`
}

export function SelectionOpportunityDetailPage() {
  const { id = '' } = useParams()
  const [detail, setDetail] = useState<ProductSelectionOpportunityDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  async function loadDetail() {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const response = await productSelectionApi.getOpportunity(id)
      setDetail(response)
    } catch (err) {
      setDetail(null)
      setError(err instanceof Error ? err.message : 'Failed to load opportunity detail')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDetail()
  }, [id])

  async function handleTrack() {
    if (!detail) return
    const nextStatus = detail.tracking ? 'tracking' : 'saved'
    try {
      const tracking = detail.tracking
        ? await productSelectionApi.updateTracking(detail.id, { status: 'tracking' })
        : await productSelectionApi.createTracking(detail.id, { status: nextStatus })
      setDetail(current => (current ? { ...current, tracking } : current))
      setToast({ type: 'success', message: 'Selection tracking updated.' })
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : 'Tracking failed.' })
    }
  }

  async function handleFavorite() {
    if (!detail) return
    try {
      const tracking = detail.tracking
        ? await productSelectionApi.updateTracking(detail.id, {
            is_favorited: !detail.tracking.is_favorited,
          })
        : await productSelectionApi.createTracking(detail.id, {
            status: 'saved',
            is_favorited: true,
          })
      setDetail(current => (current ? { ...current, tracking } : current))
      setToast({ type: 'success', message: 'Favorite state updated.' })
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : 'Favorite update failed.' })
    }
  }

  if (loading && !detail) {
    return <Loading text="Loading selection detail..." />
  }

  if (error && !detail) {
    return <ErrorMessage message={error} onRetry={() => void loadDetail()} />
  }

  if (!detail) {
    return null
  }

  return (
    <main className="space-y-6" data-testid="selection-opportunity-detail-page">
      {toast ? <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} /> : null}

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                {formatPlatform(detail.platform)}
              </span>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                Score {detail.opportunity_score.toFixed(1)}
              </span>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                Confidence {detail.confidence_score.toFixed(1)}
              </span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">{detail.title}</h1>
              <p className="mt-2 text-sm text-slate-500">
                {detail.category_path || 'Uncategorized'} |{' '}
                {formatPriceRange(detail.price_low, detail.price_mid, detail.price_high)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-secondary" onClick={() => void handleFavorite()}>
              {detail.tracking?.is_favorited ? 'Unfavorite' : 'Favorite'}
            </button>
            <button type="button" className="btn btn-primary" onClick={() => void handleTrack()}>
              {detail.tracking ? 'Update Tracking' : 'Add Tracking'}
            </button>
          </div>
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void loadDetail()} /> : null}

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Reason Blocks</h2>
          <div className="mt-4 space-y-3">
            {detail.reason_blocks.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                No explanation yet.
              </div>
            ) : (
              detail.reason_blocks.map(reason => (
                <div key={reason} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  {reason}
                </div>
              ))
            )}
          </div>

          <div className="mt-6">
            <h3 className="text-lg font-semibold text-slate-900">Signals</h3>
            <div className="mt-4 space-y-3">
              {detail.signals.map(signal => (
                <div key={signal.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-slate-900">{signal.signal_type}</div>
                    <div className="text-xs text-slate-500">
                      {formatPlatform(signal.platform)} | sample {signal.sample_size}
                    </div>
                  </div>
                  <pre className="mt-3 whitespace-pre-wrap break-words text-xs text-slate-600">
                    {JSON.stringify(signal.value_json, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="space-y-6">
          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Decision Summary</h2>
            <div className="mt-4 grid gap-3 text-sm text-slate-600">
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>Recommended action</span>
                <span className="max-w-[60%] text-right font-medium text-slate-900">
                  {detail.recommended_action || 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>Demand score</span>
                <span className="font-medium text-slate-900">{detail.demand_score.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>Competition score</span>
                <span className="font-medium text-slate-900">{detail.competition_score.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>Price-fit score</span>
                <span className="font-medium text-slate-900">{detail.price_fit_score.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>Cross-platform signal</span>
                <span className="font-medium text-slate-900">
                  {detail.cross_platform_signal_score.toFixed(1)}
                </span>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Tracking</h2>
            <div className="mt-4 space-y-3">
              {detail.tracking ? (
                <>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    Status: <span className="font-medium text-slate-900">{detail.tracking.status}</span>
                  </div>
                  {detail.tracking.next_action ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      Next action: {detail.tracking.next_action}
                    </div>
                  ) : null}
                  {detail.tracking.notes ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      Notes: {detail.tracking.notes}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  Not in tracking yet.
                </div>
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Actions</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/selection/opportunities" className="btn btn-secondary">
                Back to Pool
              </Link>
              <Link to={`/selection/compare?ids=${detail.id}`} className="btn btn-secondary">
                Open Compare
              </Link>
            </div>
          </article>
        </div>
      </section>
    </main>
  )
}

export default SelectionOpportunityDetailPage
