import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { productSelectionApi } from '../../services/productSelectionApi'
import type { ProductSelectionOpportunityDetail } from '../../types'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? 'Taobao' : platform === 'xianyu' ? 'Xianyu' : platform
}

function parseIds(searchParams: URLSearchParams) {
  const ids = [...searchParams.getAll('ids')]
  if (ids.length > 0) return ids

  const fallback = searchParams.get('ids')
  return fallback ? fallback.split(',').filter(Boolean) : []
}

export function SelectionComparePage() {
  const [searchParams] = useSearchParams()
  const [items, setItems] = useState<ProductSelectionOpportunityDetail[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ids = parseIds(searchParams).slice(0, 5)

  useEffect(() => {
    if (ids.length === 0) {
      setItems([])
      return
    }

    let cancelled = false

    async function loadItems() {
      setLoading(true)
      setError(null)
      try {
        const responses = await Promise.all(ids.map(id => productSelectionApi.getOpportunity(id)))
        if (!cancelled) setItems(responses)
      } catch (err) {
        if (!cancelled) {
          setItems([])
          setError(err instanceof Error ? err.message : 'Failed to load compare data')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void loadItems()

    return () => {
      cancelled = true
    }
  }, [ids.join('|')])

  if (loading && items.length === 0) {
    return <Loading text="Loading compare view..." />
  }

  return (
    <main className="space-y-6" data-testid="selection-compare-page">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Selection Compare</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Compare up to five opportunities side by side on price, signals, risk, and
              recommended action.
            </p>
          </div>
          <Link to="/selection/opportunities" className="btn btn-secondary">
            Back to Pool
          </Link>
        </div>
      </section>

      {error ? <ErrorMessage message={error} /> : null}

      {ids.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          Select at least one opportunity from the pool to open compare mode.
        </section>
      ) : (
        <section className="overflow-x-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <table className="min-w-full table-auto border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-sm text-slate-500">
                <th className="px-4 py-3 font-medium">Metric</th>
                {items.map(item => (
                  <th key={item.id} className="px-4 py-3 font-medium text-slate-900">
                    <Link to={`/selection/opportunities/${item.id}`} className="hover:text-sky-700">
                      {item.title}
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-sm text-slate-700">
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">Platform</td>
                {items.map(item => (
                  <td key={`${item.id}-platform`} className="px-4 py-3">
                    {formatPlatform(item.platform)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">Opportunity Score</td>
                {items.map(item => (
                  <td key={`${item.id}-score`} className="px-4 py-3">
                    {item.opportunity_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">Confidence</td>
                {items.map(item => (
                  <td key={`${item.id}-confidence`} className="px-4 py-3">
                    {item.confidence_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">Demand</td>
                {items.map(item => (
                  <td key={`${item.id}-demand`} className="px-4 py-3">
                    {item.demand_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">Competition</td>
                {items.map(item => (
                  <td key={`${item.id}-competition`} className="px-4 py-3">
                    {item.competition_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">Risk Tags</td>
                {items.map(item => (
                  <td key={`${item.id}-risk`} className="px-4 py-3">
                    {item.risk_tags.join(', ') || 'N/A'}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Recommended Action</td>
                {items.map(item => (
                  <td key={`${item.id}-action`} className="px-4 py-3 align-top">
                    {item.recommended_action || 'N/A'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </section>
      )}
    </main>
  )
}

export default SelectionComparePage
