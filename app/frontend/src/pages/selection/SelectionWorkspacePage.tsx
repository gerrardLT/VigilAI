import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { productSelectionApi } from '../../services/productSelectionApi'
import type {
  ProductSelectionPlatformScope,
  ProductSelectionResearchJobResponse,
  ProductSelectionWorkspaceResponse,
} from '../../types'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? '淘宝' : platform === 'xianyu' ? '闲鱼' : platform
}

function formatSourceMode(mode: string) {
  if (mode === 'live') return '实时'
  if (mode === 'fallback') return '回退'
  if (mode === 'mixed') return '混合'
  if (mode === 'failed') return '失败'
  return mode
}

function formatPriceRange(low: number | null, mid: number | null, high: number | null) {
  const values = [low, mid, high].filter((value): value is number => value !== null)
  if (values.length === 0) return '暂无'
  if (values.length === 1) return `¥${values[0].toFixed(0)}`
  return `¥${Math.min(...values).toFixed(0)} - ¥${Math.max(...values).toFixed(0)}`
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
  if (value === 'enterprise') return '企业'
  if (value === 'personal') return '个人'
  return '未知'
}

function formatQueryType(value: string) {
  if (value === 'keyword') return '关键词'
  if (value === 'category') return '类目'
  if (value === 'listing_url') return '商品链接'
  return value
}

function formatPlatformScope(value: string) {
  if (value === 'taobao') return '淘宝'
  if (value === 'xianyu') return '闲鱼'
  if (value === 'both') return '全部平台'
  return value
}

function formatResearchStatus(value: string) {
  if (value === 'completed') return '已完成'
  if (value === 'running') return '运行中'
  if (value === 'pending') return '排队中'
  if (value === 'failed') return '失败'
  return value
}

function formatTrackingStatus(value: string) {
  if (value === 'saved') return '已保存'
  if (value === 'tracking') return '跟进中'
  if (value === 'done') return '已完成'
  if (value === 'archived') return '已归档'
  return value
}

export function SelectionWorkspacePage() {
  const [workspace, setWorkspace] = useState<ProductSelectionWorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [researchLoading, setResearchLoading] = useState(false)
  const [researchError, setResearchError] = useState<string | null>(null)
  const [latestResearchJob, setLatestResearchJob] = useState<ProductSelectionResearchJobResponse | null>(null)
  const [queryText, setQueryText] = useState('Mate X6')
  const [platformScope, setPlatformScope] = useState<ProductSelectionPlatformScope>('xianyu')
  const [renderedSnapshotPath, setRenderedSnapshotPath] = useState('docs/goofish-rendered-search.html')
  const [renderedSnapshotHtml, setRenderedSnapshotHtml] = useState('')
  const [detailSnapshotManifestPath, setDetailSnapshotManifestPath] = useState(
    'app/backend/tests/fixtures/product_selection/goofish_detail_pages.manifest.json'
  )

  async function loadWorkspace() {
    setLoading(true)
    setError(null)
    try {
      const response = await productSelectionApi.getWorkspace()
      setWorkspace(response)
    } catch (err) {
      setWorkspace(null)
      setError(err instanceof Error ? err.message : '加载选品工作台失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadWorkspace()
  }, [])

  async function handleResearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setResearchLoading(true)
    setResearchError(null)

    try {
      const job = await productSelectionApi.createResearchJob({
        query_type: 'keyword',
        query_text: queryText,
        platform_scope: platformScope,
        rendered_snapshot_path: renderedSnapshotPath || undefined,
        rendered_snapshot_html: renderedSnapshotPath ? undefined : renderedSnapshotHtml || undefined,
        detail_snapshot_manifest_path: detailSnapshotManifestPath || undefined,
      })
      setLatestResearchJob(job)
      await loadWorkspace()
    } catch (err) {
      setResearchError(err instanceof Error ? err.message : '运行本地样本研究失败')
    } finally {
      setResearchLoading(false)
    }
  }

  if (loading && !workspace) {
    return <Loading text="正在加载选品工作台..." />
  }

  if (error && !workspace) {
    return <ErrorMessage message={error} onRetry={() => void loadWorkspace()} />
  }

  if (!workspace) {
    return null
  }

  const topOpportunitiesHref =
    workspace.top_opportunities_source_summary.fallback_used
      ? `/selection/opportunities?source_mode=fallback${
          workspace.top_opportunities_source_summary.fallback_reasons[0]
            ? `&fallback_reason=${encodeURIComponent(workspace.top_opportunities_source_summary.fallback_reasons[0])}`
            : ''
        }`
      : '/selection/opportunities?source_mode=live'

  const trackingQueueHref =
    workspace.tracking_queue_source_summary.fallback_used
      ? `/selection/tracking?source_mode=fallback${
          workspace.tracking_queue_source_summary.fallback_reasons[0]
            ? `&fallback_reason=${encodeURIComponent(workspace.tracking_queue_source_summary.fallback_reasons[0])}`
            : ''
        }`
      : '/selection/tracking?source_mode=live'

  return (
    <main className="space-y-6" data-testid="selection-workspace-page">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
              选品 MVP
            </span>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">选品工作台</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                查看最近研究任务、高分机会，以及当前淘宝和闲鱼选品的跟进队列。
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link to="/selection/opportunities" className="btn btn-primary">
              打开机会池
            </Link>
            <Link to="/selection/tracking" className="btn btn-secondary">
              打开跟进
            </Link>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm" data-testid="selection-local-research-panel">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold text-slate-900">本地样本研究</h2>
          <p className="text-sm leading-6 text-slate-600">
            直接基于渲染后的搜索快照和详情页 manifest 运行研究任务。
          </p>
        </div>

        <form className="mt-5 grid gap-4 lg:grid-cols-2" onSubmit={handleResearchSubmit}>
          <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
            查询词
            <input
              className="rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900"
              value={queryText}
              onChange={event => setQueryText(event.target.value)}
              placeholder="Mate X6"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
            平台
            <select
              className="rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900"
              value={platformScope}
              onChange={event => setPlatformScope(event.target.value as ProductSelectionPlatformScope)}
            >
              <option value="xianyu">闲鱼</option>
              <option value="taobao">淘宝</option>
              <option value="both">全部</option>
            </select>
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-700 lg:col-span-2">
            渲染搜索快照路径
            <input
              className="rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900"
              value={renderedSnapshotPath}
              onChange={event => setRenderedSnapshotPath(event.target.value)}
              placeholder="docs/goofish-rendered-search.html"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-700 lg:col-span-2">
            渲染搜索快照 HTML 备用内容
            <textarea
              className="min-h-[180px] rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900"
              value={renderedSnapshotHtml}
              onChange={event => setRenderedSnapshotHtml(event.target.value)}
              placeholder="<html>...</html>"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-700 lg:col-span-2">
            详情页 Manifest 路径
            <input
              className="rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900"
              value={detailSnapshotManifestPath}
              onChange={event => setDetailSnapshotManifestPath(event.target.value)}
              placeholder="app/backend/tests/fixtures/product_selection/goofish_detail_pages.manifest.json"
            />
          </label>

          <div className="flex flex-wrap items-center gap-3 lg:col-span-2">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={researchLoading || !queryText.trim()}
            >
              {researchLoading ? '运行中...' : '运行样本研究'}
            </button>
            {latestResearchJob ? (
              <Link
                to={`/selection/opportunities?query_id=${encodeURIComponent(latestResearchJob.job.id)}`}
                className="btn btn-secondary"
              >
                打开最新结果
              </Link>
            ) : null}
          </div>
        </form>

        {researchError ? (
          <div className="mt-4">
            <ErrorMessage message={researchError} />
          </div>
        ) : null}

        {latestResearchJob ? (
          <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
            {latestResearchJob.job.status === 'completed'
              ? `任务 ${latestResearchJob.job.id} 已完成，得到 ${latestResearchJob.total} 条机会，其中 ${latestResearchJob.source_summary.mode_counts.live} 条来自实时提取。`
              : `任务 ${latestResearchJob.job.id} 失败，原因是没有提取到可用于生产判断的实时结果。`}
          </div>
        ) : null}
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void loadWorkspace()} /> : null}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">查询数</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.query_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">机会数</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.opportunity_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">跟进中</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.tracked_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">已收藏</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.favorited_count}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-slate-700">市场来源可信度</span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800">
            {formatSourceMode(workspace.source_summary.overall_mode)}
          </span>
          <span className="text-sm text-slate-500">
            {workspace.source_summary.mode_counts.live} 条实时 / {workspace.source_summary.mode_counts.fallback} 条回退
          </span>
        </div>
        {workspace.source_summary.fallback_used ? (
          <p className="mt-3 text-sm leading-6 text-amber-900">
            部分机会仍依赖非实时回退数据，正式判断前请重新抓取真实市场页面。
          </p>
        ) : (
          <p className="mt-3 text-sm leading-6 text-slate-500">
            当前高优先级机会由实时市场提取结果支撑。
          </p>
        )}
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <div className="text-xs uppercase tracking-wide text-slate-500">采纳商品数</div>
            <div className="mt-1 font-medium text-slate-900">
              {workspace.source_summary.extraction_stats_summary.accepted_candidates}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <div className="text-xs uppercase tracking-wide text-slate-500">查询不匹配拒绝数</div>
            <div className="mt-1 font-medium text-slate-900">
              {workspace.source_summary.extraction_stats_summary.rejected_query_miss}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <div className="text-xs uppercase tracking-wide text-slate-500">企业 / 个人</div>
            <div className="mt-1 font-medium text-slate-900">
              {workspace.source_summary.seller_mix.enterprise} / {workspace.source_summary.seller_mix.personal}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <div className="text-xs uppercase tracking-wide text-slate-500">销量 / 卖家数据</div>
            <div className="mt-1 font-medium text-slate-900">
              {workspace.source_summary.seller_mix.with_sales_volume} / {workspace.source_summary.seller_mix.with_seller_count}
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">高优先级机会来源</h2>
              <p className="mt-1 text-sm text-slate-500">当前决策池的来源质量。</p>
            </div>
            <Link
              to={topOpportunitiesHref}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800 hover:bg-slate-200"
            >
              {formatSourceMode(workspace.top_opportunities_source_summary.overall_mode)}
            </Link>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <span>{workspace.top_opportunities_source_summary.mode_counts.live} 条实时</span>
            <span>{workspace.top_opportunities_source_summary.mode_counts.fallback} 条回退</span>
          </div>
          {workspace.top_opportunities_source_summary.fallback_reasons.length > 0 ? (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              原因：
              {workspace.top_opportunities_source_summary.fallback_reasons
                .map(formatFallbackReason)
                .join(', ')}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              当前高优先级机会由实时市场提取结果支撑。
            </div>
          )}
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">跟进队列来源</h2>
              <p className="mt-1 text-sm text-slate-500">已进入后续跟进条目的可信度。</p>
            </div>
            <Link
              to={trackingQueueHref}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800 hover:bg-slate-200"
            >
              {formatSourceMode(workspace.tracking_queue_source_summary.overall_mode)}
            </Link>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <span>{workspace.tracking_queue_source_summary.mode_counts.live} 条实时</span>
            <span>{workspace.tracking_queue_source_summary.mode_counts.fallback} 条回退</span>
          </div>
          {workspace.tracking_queue_source_summary.fallback_reasons.length > 0 ? (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              原因：
              {workspace.tracking_queue_source_summary.fallback_reasons
                .map(formatFallbackReason)
                .join(', ')}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              当前队列中没有非实时回退条目。
            </div>
          )}
        </article>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">高优先级机会</h2>
              <p className="mt-1 text-sm text-slate-500">
                当前选品池中得分最高的一批条目。
              </p>
            </div>
            <Link to="/selection/opportunities" className="text-sm font-medium text-sky-700">
              查看全部
            </Link>
          </div>

          <div className="mt-4 space-y-4">
            {workspace.top_opportunities.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                还没有研究结果。
              </div>
            ) : (
              workspace.top_opportunities.map(opportunity => (
                <Link
                  key={opportunity.id}
                  to={`/selection/opportunities/${opportunity.id}`}
                  className="block rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:border-sky-200 hover:bg-sky-50/40"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                      {formatPlatform(opportunity.platform)}
                    </span>
                    <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-800">
                      {formatSourceMode(opportunity.source_mode)}
                    </span>
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                      机会分 {opportunity.opportunity_score.toFixed(1)}
                    </span>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                      置信度 {opportunity.confidence_score.toFixed(1)}
                    </span>
                  </div>
                  <h3 className="mt-3 text-lg font-semibold text-slate-900">{opportunity.title}</h3>
                  <div className="mt-2 text-sm text-slate-600">
                    {opportunity.category_path || '未分类'} |{' '}
                    {formatPriceRange(
                      opportunity.price_low,
                      opportunity.price_mid,
                      opportunity.price_high
                    )}
                  </div>
                  <div className="mt-2 grid gap-1 text-xs text-slate-500 sm:grid-cols-2">
                    <div>卖家类型：{formatSellerType(opportunity.seller_type)}</div>
                    <div>销量：{opportunity.sales_volume !== null ? opportunity.sales_volume : '暂无'}</div>
                    <div>在售卖家数：{opportunity.seller_count !== null ? opportunity.seller_count : '暂无'}</div>
                    {opportunity.seller_name ? <div>卖家：{opportunity.seller_name}</div> : null}
                  </div>
                </Link>
              ))
            )}
          </div>
        </article>

        <div className="space-y-6">
          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">最近查询</h2>
            <div className="mt-4 space-y-3">
              {workspace.recent_queries.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  还没有研究任务。
                </div>
              ) : (
                workspace.recent_queries.map(query => (
                  <div key={query.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-sm font-semibold text-slate-900">{query.query_text}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {formatQueryType(query.query_type)} | {formatPlatformScope(query.platform_scope)} |{' '}
                      {formatResearchStatus(query.status)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">跟进队列</h2>
            <div className="mt-4 space-y-3">
              {workspace.tracking_queue.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  还没有跟进条目。
                </div>
              ) : (
                workspace.tracking_queue.map(item => (
                  <Link
                    key={item.opportunity_id}
                    to={`/selection/opportunities/${item.opportunity_id}`}
                    className="block rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:border-sky-200"
                  >
                    <div className="text-sm font-semibold text-slate-900">{item.opportunity.title}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {formatTrackingStatus(item.status)} | {formatPlatform(item.opportunity.platform)}
                    </div>
                    {item.next_action ? (
                      <div className="mt-2 text-sm text-slate-600">{item.next_action}</div>
                    ) : null}
                  </Link>
                ))
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">平台分布</h2>
            <div className="mt-4 space-y-3">
              {workspace.platform_breakdown.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  还没有平台数据。
                </div>
              ) : (
                workspace.platform_breakdown.map(item => (
                  <div
                    key={item.platform}
                    className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                  >
                    <span className="text-sm font-medium text-slate-700">
                      {formatPlatform(item.platform)}
                    </span>
                    <span className="text-sm font-semibold text-slate-900">{item.count}</span>
                  </div>
                ))
              )}
            </div>
          </article>
        </div>
      </section>
    </main>
  )
}

export default SelectionWorkspacePage

