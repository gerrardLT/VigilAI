import { Link } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { Toast } from '../../components/Toast'
import { useProductSelectionTracking } from '../../hooks/useProductSelectionTracking'
import type { ProductSelectionTrackingStatus } from '../../types'
import { useState } from 'react'

const FILTERS: Array<{ value: ProductSelectionTrackingStatus | undefined; label: string }> = [
  { value: undefined, label: 'All' },
  { value: 'saved', label: 'Saved' },
  { value: 'tracking', label: 'Tracking' },
  { value: 'done', label: 'Done' },
  { value: 'archived', label: 'Archived' },
]

function formatPlatform(platform: string) {
  return platform === 'taobao' ? 'Taobao' : platform === 'xianyu' ? 'Xianyu' : platform
}

export function SelectionTrackingPage() {
  const { items, loading, error, statusFilter, setStatusFilter, updateTracking, deleteTracking, refetch } =
    useProductSelectionTracking()
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  async function handleStatusChange(opportunityId: string, status: ProductSelectionTrackingStatus) {
    const result = await updateTracking(opportunityId, { status })
    setToast({
      type: result ? 'success' : 'error',
      message: result ? 'Selection tracking updated.' : 'Failed to update selection tracking.',
    })
  }

  async function handleDelete(opportunityId: string) {
    const success = await deleteTracking(opportunityId)
    setToast({
      type: success ? 'success' : 'error',
      message: success ? 'Selection tracking removed.' : 'Failed to remove selection tracking.',
    })
  }

  if (loading && items.length === 0) {
    return <Loading text="Loading selection tracking..." />
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
            <h1 className="text-3xl font-bold text-slate-900">Selection Tracking</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage followed-up selection opportunities and keep the next action queue clean.
            </p>
          </div>
          <Link to="/selection/opportunities" className="btn btn-secondary">
            Back to Opportunity Pool
          </Link>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map(filter => {
            const active = statusFilter === filter.value
            return (
              <button
                key={filter.label}
                type="button"
                onClick={() => setStatusFilter(filter.value)}
                className={`rounded-full px-4 py-2 text-sm font-medium ${
                  active ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {filter.label}
              </button>
            )
          })}
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void refetch()} /> : null}

      {items.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          No tracked selection item yet.
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
                      {item.status}
                    </span>
                    {item.is_favorited ? (
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
                        Favorited
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
                      Score {item.opportunity.opportunity_score.toFixed(1)} | Confidence{' '}
                      {item.opportunity.confidence_score.toFixed(1)}
                    </p>
                  </div>
                  {item.next_action ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      Next action: {item.next_action}
                    </div>
                  ) : null}
                  {item.notes ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      Notes: {item.notes}
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn btn-secondary" onClick={() => void handleStatusChange(item.opportunity_id, 'tracking')}>
                    Mark Tracking
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => void handleStatusChange(item.opportunity_id, 'done')}>
                    Mark Done
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => void handleStatusChange(item.opportunity_id, 'archived')}>
                    Archive
                  </button>
                  <button type="button" className="btn btn-secondary text-red-600 hover:text-red-700" onClick={() => void handleDelete(item.opportunity_id)}>
                    Remove
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
