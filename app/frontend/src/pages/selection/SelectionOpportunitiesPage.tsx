import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { Pagination } from '../../components/Pagination'
import { SearchBox } from '../../components/SearchBox'
import { Toast } from '../../components/Toast'
import { useProductSelection } from '../../hooks/useProductSelection'
import type { ProductSelectionOpportunity, ProductSelectionSourceSummary } from '../../types'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? '淘宝' : platform === 'xianyu' ? '闲鱼' : platform
}

function formatPriceRange(low: number | null, mid: number | null, high: number | null) {
  const values = [low, mid, high].filter((value): value is number => value !== null)
  if (values.length === 0) return '暂无'
  if (values.length === 1) return `¥${values[0].toFixed(0)}`
  return `¥${Math.min(...values).toFixed(0)} - ¥${Math.max(...values).toFixed(0)}`
}

const SORT_OPTIONS = [
  { value: 'opportunity_score', label: '机会分' },
  { value: 'confidence_score', label: '置信度' },
  { value: 'price_mid', label: '中位价格' },
  { value: 'created_at', label: '创建时间' },
]

function formatSourceMode(mode: string) {
  if (mode === 'live') return '实时'
  if (mode === 'fallback') return '回退'
  if (mode === 'mixed') return '混合'
  if (mode === 'failed') return '失败'
  return mode
}

function getSourceTone(mode: string) {
  if (mode === 'live') return 'bg-emerald-50 text-emerald-800'
  if (mode === 'fallback') return 'bg-amber-50 text-amber-800'
  if (mode === 'failed') return 'bg-rose-50 text-rose-800'
  return 'bg-sky-50 text-sky-800'
}

function fallbackExplanation(opportunity: ProductSelectionOpportunity) {
  if (opportunity.source_mode !== 'fallback') return null
  return '该条目未能完成实时提取，行动前请先人工复核。'
}

function summarizeSourceSummary(summary: ProductSelectionSourceSummary | null) {
  if (!summary) return '暂无来源可信度数据。'
  if (summary.overall_mode === 'live') {
    return `${summary.mode_counts.live} 条结果来自实时提取。`
  }
  if (summary.overall_mode === 'mixed') {
    return `${summary.mode_counts.live} 条实时 / ${summary.mode_counts.fallback} 条回退。`
  }
  if (summary.overall_mode === 'failed') {
    return '实时提取失败，请补充真实页面样本后重试。'
  }
  return `${summary.mode_counts.fallback} 条结果来自非实时回退数据。`
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

function formatSellerType(value: string | null) {
  if (value === 'enterprise') return '企业卖家'
  if (value === 'personal') return '个人卖家'
  return '卖家类型未知'
}

export function SelectionOpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [queryText, setQueryText] = useState(searchParams.get('query_text') || '')
  const [queryType, setQueryType] = useState<'keyword' | 'category' | 'listing_url'>(
    (searchParams.get('query_type') as 'keyword' | 'category' | 'listing_url' | null) || 'keyword'
  )
  const [platformScope, setPlatformScope] = useState<'taobao' | 'xianyu' | 'both'>(
    (searchParams.get('platform_scope') as 'taobao' | 'xianyu' | 'both' | null) || 'both'
  )
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
    sourceSummary,
    setFilters,
    setPage,
    createResearchJob,
    refetch,
  } = useProductSelection({
    query_id: searchParams.get('query_id') || '',
    platform: searchParams.get('platform') || '',
    search: searchParams.get('search') || '',
    source_mode: (searchParams.get('source_mode') as 'live' | 'fallback' | '') || '',
    fallback_reason: searchParams.get('fallback_reason') || '',
    sort_by:
      (searchParams.get('sort_by') as
        | 'opportunity_score'
        | 'confidence_score'
        | 'created_at'
        | 'updated_at'
        | 'price_mid'
        | null) || 'opportunity_score',
    sort_order: (searchParams.get('sort_order') as 'asc' | 'desc' | null) || 'desc',
    page: Number(searchParams.get('page') || '1'),
  })

  const compareHref = useMemo(() => {
    const ids = selectedIds.map(id => `ids=${encodeURIComponent(id)}`).join('&')
    return ids ? `/selection/compare?${ids}` : '/selection/compare'
  }, [selectedIds])

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams)
    const managedEntries: Array<[string, string | undefined]> = [
      ['query_id', filters.query_id || undefined],
      ['platform', filters.platform || undefined],
      ['search', filters.search || undefined],
      ['risk_tag', filters.risk_tag || undefined],
      ['source_mode', filters.source_mode || undefined],
      ['fallback_reason', filters.fallback_reason || undefined],
      ['sort_by', filters.sort_by || undefined],
      ['sort_order', filters.sort_order || undefined],
      ['page', filters.page && filters.page > 1 ? String(filters.page) : undefined],
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

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams)
    const managedEntries: Array<[string, string | undefined]> = [
      ['query_text', queryText.trim() || undefined],
      ['query_type', queryType !== 'keyword' ? queryType : undefined],
      ['platform_scope', platformScope !== 'both' ? platformScope : undefined],
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
  }, [platformScope, queryText, queryType, searchParams, setSearchParams])

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
      setToast({
        type: job.job.status === 'completed' ? 'success' : 'error',
        message:
          job.job.status === 'completed'
            ? '研究任务已完成。'
            : '实时提取失败，请补充真实页面样本后重试。',
      })
    } else {
      setToast({ type: 'error', message: '创建研究任务失败。' })
    }
  }

  return (
    <main className="space-y-6" data-testid="selection-opportunities-page">
      {toast ? <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} /> : null}

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">选品机会池</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              发起选品研究任务，筛选生成的机会池，并决定哪些条目进入跟进或对比。
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {latestJob ? (
              <div>
                最近任务：<span className="font-medium text-slate-900">{latestJob.job.query_text}</span>
              </div>
            ) : (
              <div>还没有研究任务。</div>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <form className="grid gap-4 lg:grid-cols-[1fr_180px_180px_auto]" onSubmit={handleCreateResearchJob}>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">研究关键词</span>
            <input
              value={queryText}
              onChange={event => setQueryText(event.target.value)}
              placeholder="例如：宠物饮水机"
              className="input w-full"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">查询类型</span>
            <select
              value={queryType}
              onChange={event => setQueryType(event.target.value as typeof queryType)}
              className="select w-full"
            >
              <option value="keyword">关键词</option>
              <option value="category">类目</option>
              <option value="listing_url">商品链接</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">平台范围</span>
            <select
              value={platformScope}
              onChange={event => setPlatformScope(event.target.value as typeof platformScope)}
              className="select w-full"
            >
              <option value="both">全部</option>
              <option value="taobao">淘宝</option>
              <option value="xianyu">闲鱼</option>
            </select>
          </label>
          <div className="flex items-end">
            <button type="submit" className="btn btn-primary w-full" disabled={loading || !queryText.trim()}>
              {loading ? '运行中...' : '开始研究'}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_160px_160px_220px_180px_auto]">
          <div>
            <SearchBox
              value={filters.search || ''}
              onChange={value => setFilters({ search: value })}
              placeholder="搜索机会"
            />
          </div>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">平台</span>
            <select
              value={filters.platform || ''}
              onChange={event => setFilters({ platform: event.target.value })}
              className="select w-full"
            >
              <option value="">全部平台</option>
              <option value="taobao">淘宝</option>
              <option value="xianyu">闲鱼</option>
            </select>
          </label>
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
              disabled={!sourceSummary?.fallback_reasons.length}
            >
              <option value="">全部回退原因</option>
              {(sourceSummary?.fallback_reasons || []).map(reason => (
                <option key={reason} value={reason}>
                  {formatFallbackReason(reason)}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700">排序</span>
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
                  source_mode: '',
                  fallback_reason: '',
                  sort_by: 'opportunity_score',
                  sort_order: 'desc',
                })
              }
            >
              重置
            </button>
            <Link
              to={compareHref}
              className={`btn btn-secondary ${selectedIds.length < 2 ? 'pointer-events-none opacity-50' : ''}`}
            >
              对比
            </Link>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          <span>{total} 条机会</span>
          <span>已选 {selectedIds.length} 条</span>
          {latestJob ? <span>当前查询：{latestJob.job.query_text}</span> : null}
          <span>{summarizeSourceSummary(sourceSummary)}</span>
        </div>
        {sourceSummary ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <div className="text-xs uppercase tracking-wide text-slate-500">提取健康度</div>
              <div className="mt-1 font-medium text-slate-900">
                {sourceSummary.extraction_stats_summary.accepted_candidates} 条采纳 /{' '}
                {sourceSummary.extraction_stats_summary.http_candidates_seen +
                  sourceSummary.extraction_stats_summary.platform_candidates_seen}{' '}条扫描
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <div className="text-xs uppercase tracking-wide text-slate-500">卖家结构</div>
              <div className="mt-1 font-medium text-slate-900">
                {sourceSummary.seller_mix.enterprise} 企业 / {sourceSummary.seller_mix.personal} 个人
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <div className="text-xs uppercase tracking-wide text-slate-500">销量信号</div>
              <div className="mt-1 font-medium text-slate-900">
                {sourceSummary.seller_mix.with_sales_volume} 条含销量数据
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <div className="text-xs uppercase tracking-wide text-slate-500">卖家深度</div>
              <div className="mt-1 font-medium text-slate-900">
                {sourceSummary.seller_mix.with_seller_count} 条含卖家数数据
              </div>
            </div>
          </div>
        ) : null}
        {sourceSummary?.fallback_used ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            当前结果中有部分条目使用了回退数据。原因：
            {sourceSummary.fallback_reasons.join(', ') || '未知'}。
          </div>
        ) : null}
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void refetch()} /> : null}

      {loading && opportunities.length === 0 ? (
        <Loading text="正在加载选品机会..." />
      ) : opportunities.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          先运行一次研究任务，生成第一批机会结果。
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
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${getSourceTone(opportunity.source_mode)}`}
                      >
                        {formatSourceMode(opportunity.source_mode)}
                      </span>
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                        机会分 {opportunity.opportunity_score.toFixed(1)}
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                        置信度 {opportunity.confidence_score.toFixed(1)}
                      </span>
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-slate-900">{opportunity.title}</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        {opportunity.category_path || '未分类'}
                      </p>
                    </div>
                    <div className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                      <div>价格带：{formatPriceRange(opportunity.price_low, opportunity.price_mid, opportunity.price_high)}</div>
                      <div>{formatSellerType(opportunity.seller_type)}</div>
                      <div>
                        销量：{opportunity.sales_volume !== null ? opportunity.sales_volume : '暂无'}
                      </div>
                      <div>
                        在售卖家数：{opportunity.seller_count !== null ? opportunity.seller_count : '暂无'}
                      </div>
                      <div>需求分：{opportunity.demand_score.toFixed(1)}</div>
                      <div>竞争分：{opportunity.competition_score.toFixed(1)}</div>
                      <div>风险分：{opportunity.risk_score.toFixed(1)}</div>
                    </div>
                    {opportunity.seller_name ? (
                      <div className="text-sm text-slate-600">卖家：{opportunity.seller_name}</div>
                    ) : null}
                    {opportunity.reason_blocks.length > 0 ? (
                      <p className="text-sm leading-6 text-slate-600">
                        {opportunity.reason_blocks[0]}
                      </p>
                    ) : null}
                    {fallbackExplanation(opportunity) ? (
                      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                        {fallbackExplanation(opportunity)}
                      </div>
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
                    选择
                  </label>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Link to={`/selection/opportunities/${opportunity.id}`} className="btn btn-secondary">
                    查看详情
                  </Link>
                  {opportunity.is_tracking ? (
                    <Link to="/selection/tracking" className="btn btn-secondary">
                      打开跟进
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

