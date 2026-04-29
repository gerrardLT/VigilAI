import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { productSelectionApi } from '../../services/productSelectionApi'
import type { ProductSelectionOpportunityDetail } from '../../types'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? '淘宝' : platform === 'xianyu' ? '闲鱼' : platform
}

function formatRiskTag(tag: string) {
  if (tag === 'after-sale') return '售后风险'
  if (tag === 'copyright') return '版权风险'
  if (tag === 'logistics') return '物流风险'
  if (tag === 'compliance') return '合规风险'
  return tag
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
          setError(err instanceof Error ? err.message : '加载对比数据失败')
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
    return <Loading text="正在加载对比视图..." />
  }

  return (
    <main className="space-y-6" data-testid="selection-compare-page">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">选品对比</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              最多支持 5 条机会并排对比价格、信号、风险与建议动作。
            </p>
          </div>
          <Link to="/selection/opportunities" className="btn btn-secondary">
            返回机会池
          </Link>
        </div>
      </section>

      {error ? <ErrorMessage message={error} /> : null}

      {ids.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          至少从机会池中选择一条机会，才能进入对比模式。
        </section>
      ) : (
        <section className="overflow-x-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <table className="min-w-full table-auto border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-sm text-slate-500">
                <th className="px-4 py-3 font-medium">指标</th>
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
                <td className="px-4 py-3 font-medium">平台</td>
                {items.map(item => (
                  <td key={`${item.id}-platform`} className="px-4 py-3">
                    {formatPlatform(item.platform)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">机会分</td>
                {items.map(item => (
                  <td key={`${item.id}-score`} className="px-4 py-3">
                    {item.opportunity_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">置信度</td>
                {items.map(item => (
                  <td key={`${item.id}-confidence`} className="px-4 py-3">
                    {item.confidence_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">需求分</td>
                {items.map(item => (
                  <td key={`${item.id}-demand`} className="px-4 py-3">
                    {item.demand_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">竞争分</td>
                {items.map(item => (
                  <td key={`${item.id}-competition`} className="px-4 py-3">
                    {item.competition_score.toFixed(1)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">风险标签</td>
                {items.map(item => (
                  <td key={`${item.id}-risk`} className="px-4 py-3">
                    {item.risk_tags.map(formatRiskTag).join('，') || '暂无'}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">建议动作</td>
                {items.map(item => (
                  <td key={`${item.id}-action`} className="px-4 py-3 align-top">
                    {item.recommended_action || '暂无'}
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
