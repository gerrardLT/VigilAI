import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { Pagination } from '../../components/Pagination'
import { SearchBox } from '../../components/SearchBox'
import { Toast } from '../../components/Toast'
import { useProductSelection } from '../../hooks/useProductSelection'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? 'Taobao' : platform === 'xianyu' ? 'Xianyu' : platform
}

function formatPriceRange(low: number | null, mid: number | null, high: number | null) {
  const values = [low, mid, high].filter((value): value is number => value !== null)
  if (values.length === 0) return 'N/A'
  if (values.length === 1) return `¥${values[0].toFixed(0)}`
  return `¥${Math.min(...values).toFixed(0)} - ¥${Math.max(...values).toFixed(0)}`
}

const SORT_OPTIONS = [
  { value: 'opportunity_score', label: 'Opportunity Score' },
  { value: 'confidence_score', label: 'Confidence' },
  { value: 'price_mid', label: 'Mid Price' },
  { value: 'created_at', label: 'Created Time' },
]

export function SelectionOpportunitiesPage() {
  const [searchParams] = useSearchParams()
  const [queryText, setQueryText] = useState('')
  const [queryType, setQueryType] = useState<'keyword' | 'category' | 'listing_url'>('keyword')
  const [platformScope, setPlatformScope] = useState<'taobao' | 'xianyu' | 'both'>('both')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const {
    opportunities,
    total,
    page,
    totalPages,
    filters,
    loading,
    error,
    latestJob,
    setFilters,
    setPage,
    createResearchJob,
    refetch,
  } = useProductSelection({
    query_id: searchParams.get('query_id') || '',
  })

  const compareHref = useMemo(() => {
    const ids = selectedIds.map(id => `ids=${encodeURIComponent(id)}`).join('&')
    return ids ? `/selection/compare?${ids}` : '/selection/compare'
  }, [selectedIds])

  function toggleSelection(id: string) {
    setSelectedIds(current =>
      current.includes(id) ? current.filter(existing => existing !== id) : [...current, id]
    )
  }

  async function handleCreateResearchJob(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = queryText.trim()
    if (!trimmed) return

    const job = await createResearchJob({
      query_type: queryType,
      query_text: trimmed,
      platform_scope: platformScope,
    })

    if (job) {
      setSelectedIds([])
      setToast({ type: 'success', message: 'Research job completed.' })
    } else {
      setToast({ type: 'error', message: 'Failed to create research job.' })
    }
  }

  return (
    <main className="space-y-6" data-testid="selection-opportunities-page">
      {toast ? <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} /> : null}

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Selection Opportunity Pool</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Create a product-selection research job, filter the resulting opportunity pool, and
              decide what should enter tracking or compare view.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {latestJob ? (
              <div>
                Latest job: <span className="font-medium text-slate-900">{latestJob.job.query_text}</span>
              </div>
            ) : (
              <div>No research job yet.</div>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <form className="grid gap-4 lg:grid-cols-[1fr_180px_180px_auto]" onSubmit={handleCreateResearchJob}>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">Research Query</span>
            <input
              value={queryText}
              onChange={event => setQueryText(event.target.value)}
              placeholder="Example: pet water fountain"
              className="input w-full"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">Query Type</span>
            <select
              value={queryType}
              onChange={event => setQueryType(event.target.value as typeof queryType)}
              className="select w-full"
            >
              <option value="keyword">Keyword</option>
              <option value="category">Category</option>
              <option value="listing_url">Listing URL</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">Platform Scope</span>
            <select
              value={platformScope}
              onChange={event => setPlatformScope(event.target.value as typeof platformScope)}
              className="select w-full"
            >
              <option value="both">Both</option>
              <option value="taobao">Taobao</option>
              <option value="xianyu">Xianyu</option>
            </select>
          </label>
          <div className="flex items-end">
            <button type="submit" className="btn btn-primary w-full" disabled={loading || !queryText.trim()}>
              {loading ? 'Running...' : 'Start Research'}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 lg:grid-cols-[1fr_180px_180px_auto]">
          <div>
            <SearchBox
              value={filters.search || ''}
              onChange={value => setFilters({ search: value })}
              placeholder="Search opportunities"
            />
          </div>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">Platform</span>
            <select
              value={filters.platform || ''}
              onChange={event => setFilters({ platform: event.target.value })}
              className="select w-full"
            >
              <option value="">All platforms</option>
              <option value="taobao">Taobao</option>
              <option value="xianyu">Xianyu</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">Sort</span>
            <select
              value={filters.sort_by || 'opportunity_score'}
              onChange={event => setFilters({ sort_by: event.target.value as typeof filters.sort_by })}
              className="select w-full"
            >
              {SORT_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end gap-2">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() =>
                setFilters({
                  query_id: '',
                  platform: '',
                  search: '',
                  risk_tag: '',
                  sort_by: 'opportunity_score',
                  sort_order: 'desc',
                })
              }
            >
              Reset
            </button>
            <Link
              to={compareHref}
              className={`btn btn-secondary ${selectedIds.length < 2 ? 'pointer-events-none opacity-50' : ''}`}
            >
              Compare
            </Link>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          <span>{total} opportunities</span>
          <span>{selectedIds.length} selected</span>
          {latestJob ? <span>Current query: {latestJob.job.query_text}</span> : null}
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void refetch()} /> : null}

      {loading && opportunities.length === 0 ? (
        <Loading text="Loading selection opportunities..." />
      ) : opportunities.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          Run a research job to generate the first opportunity set.
        </section>
      ) : (
        <>
          <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {opportunities.map(opportunity => (
              <article
                key={opportunity.id}
                className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                        {formatPlatform(opportunity.platform)}
                      </span>
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                        Score {opportunity.opportunity_score.toFixed(1)}
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                        Confidence {opportunity.confidence_score.toFixed(1)}
                      </span>
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-slate-900">{opportunity.title}</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        {opportunity.category_path || 'Uncategorized'}
                      </p>
                    </div>
                    <div className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                      <div>Price band: {formatPriceRange(opportunity.price_low, opportunity.price_mid, opportunity.price_high)}</div>
                      <div>Demand: {opportunity.demand_score.toFixed(1)}</div>
                      <div>Competition: {opportunity.competition_score.toFixed(1)}</div>
                      <div>Risk: {opportunity.risk_score.toFixed(1)}</div>
                    </div>
                    {opportunity.reason_blocks.length > 0 ? (
                      <p className="text-sm leading-6 text-slate-600">
                        {opportunity.reason_blocks[0]}
                      </p>
                    ) : null}
                    <div className="flex flex-wrap gap-2">
                      {opportunity.risk_tags.map(tag => (
                        <span
                          key={`${opportunity.id}-${tag}`}
                          className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs text-rose-700"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  <label className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(opportunity.id)}
                      onChange={() => toggleSelection(opportunity.id)}
                    />
                    Select
                  </label>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Link to={`/selection/opportunities/${opportunity.id}`} className="btn btn-secondary">
                    View Detail
                  </Link>
                  {opportunity.is_tracking ? (
                    <Link to="/selection/tracking" className="btn btn-secondary">
                      Open Tracking
                    </Link>
                  ) : null}
                </div>
              </article>
            ))}
          </section>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </main>
  )
}

export default SelectionOpportunitiesPage
