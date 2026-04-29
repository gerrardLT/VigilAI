import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { Toast } from '../../components/Toast'
import { productSelectionApi } from '../../services/productSelectionApi'
import type { ProductSelectionOpportunityDetail, ProductSelectionTrackingStatus } from '../../types'

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

function formatTrackingStatus(value: ProductSelectionTrackingStatus) {
  if (value === 'saved') return '已保存'
  if (value === 'tracking') return '跟进中'
  if (value === 'done') return '已完成'
  if (value === 'archived') return '已归档'
  return value
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
  return '暂无'
}

function formatSignalType(value: string) {
  if (value === 'price_band') return '价格带'
  if (value === 'seller_mix') return '卖家结构'
  if (value === 'sales_volume') return '销量信号'
  if (value === 'competition_snapshot') return '竞争快照'
  if (value === 'platform_crosscheck') return '跨平台比对'
  return value
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
      setError(err instanceof Error ? err.message : '加载机会详情失败')
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
      setToast({ type: 'success', message: '选品跟进已更新。' })
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : '跟进失败。' })
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
      setToast({ type: 'success', message: '收藏状态已更新。' })
    } catch (err) {
      setToast({ type: 'error', message: err instanceof Error ? err.message : '收藏更新失败。' })
    }
  }

  if (loading && !detail) {
    return <Loading text="正在加载选品详情..." />
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
              <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-800">
                {formatSourceMode(detail.source_mode)}
              </span>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                机会分 {detail.opportunity_score.toFixed(1)}
              </span>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                置信度 {detail.confidence_score.toFixed(1)}
              </span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">{detail.title}</h1>
              <p className="mt-2 text-sm text-slate-500">
                {detail.category_path || '未分类'} | {formatPriceRange(detail.price_low, detail.price_mid, detail.price_high)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-secondary" onClick={() => void handleFavorite()}>
              {detail.tracking?.is_favorited ? '取消收藏' : '收藏'}
            </button>
            <button type="button" className="btn btn-primary" onClick={() => void handleTrack()}>
              {detail.tracking ? '更新跟进' : '加入跟进'}
            </button>
          </div>
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void loadDetail()} /> : null}

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">理由说明</h2>
          <div className="mt-4 space-y-3">
            {detail.reason_blocks.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                暂无说明。
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
            <h3 className="text-lg font-semibold text-slate-900">信号</h3>
            <div className="mt-4 space-y-3">
              {detail.signals.map(signal => (
                <div key={signal.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-slate-900">
                      {formatSignalType(signal.signal_type)}
                    </div>
                    <div className="text-xs text-slate-500">
                      {formatPlatform(signal.platform)} | 样本数 {signal.sample_size}
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
            <h2 className="text-xl font-semibold text-slate-900">决策摘要</h2>
            <div className="mt-4 grid gap-3 text-sm text-slate-600">
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>卖家类型</span>
                <span className="font-medium text-slate-900">{formatSellerType(detail.seller_type)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>卖家名称</span>
                <span className="max-w-[60%] text-right font-medium text-slate-900">
                  {detail.seller_name || '暂无'}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>销量</span>
                <span className="font-medium text-slate-900">{detail.sales_volume ?? '暂无'}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>在售卖家数</span>
                <span className="font-medium text-slate-900">{detail.seller_count ?? '暂无'}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>来源模式</span>
                <span className="font-medium text-slate-900">{formatSourceMode(detail.source_mode)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>建议动作</span>
                <span className="max-w-[60%] text-right font-medium text-slate-900">
                  {detail.recommended_action || '暂无'}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>需求分</span>
                <span className="font-medium text-slate-900">{detail.demand_score.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>竞争分</span>
                <span className="font-medium text-slate-900">{detail.competition_score.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>价格匹配分</span>
                <span className="font-medium text-slate-900">{detail.price_fit_score.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                <span>跨平台信号</span>
                <span className="font-medium text-slate-900">
                  {detail.cross_platform_signal_score.toFixed(1)}
                </span>
              </div>
            </div>
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
              {detail.source_mode === 'fallback'
                ? '该机会当前依赖非实时回退数据，行动前请重新抓取真实市场页面。'
                : '该机会由实时市场提取结果支撑。'}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">来源诊断</h2>
            <div className="mt-4 space-y-3 text-sm text-slate-600">
              {detail.source_diagnostics?.fallback_reason ? (
                <div className="rounded-2xl bg-amber-50 px-4 py-3 text-amber-900">
                  回退原因：{formatFallbackReason(String(detail.source_diagnostics.fallback_reason))}
                </div>
              ) : null}
              {detail.source_diagnostics?.listing_url ? (
                <a
                  href={String(detail.source_diagnostics.listing_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-2xl bg-slate-50 px-4 py-3 text-sky-700 underline"
                >
                  打开来源商品页
                </a>
              ) : null}
              {detail.source_diagnostics?.listing_snippet ? (
                <div className="rounded-2xl bg-slate-50 px-4 py-3 text-slate-700">
                  {String(detail.source_diagnostics.listing_snippet)}
                </div>
              ) : null}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">跟进</h2>
            <div className="mt-4 space-y-3">
              {detail.tracking ? (
                <>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    状态：<span className="font-medium text-slate-900">{formatTrackingStatus(detail.tracking.status)}</span>
                  </div>
                  {detail.tracking.next_action ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      下一步：{detail.tracking.next_action}
                    </div>
                  ) : null}
                  {detail.tracking.notes ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                      备注：{detail.tracking.notes}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  尚未加入跟进。
                </div>
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">操作</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/selection/opportunities" className="btn btn-secondary">
                返回机会池
              </Link>
              <Link to={`/selection/compare?ids=${detail.id}`} className="btn btn-secondary">
                打开对比
              </Link>
            </div>
          </article>
        </div>
      </section>
    </main>
  )
}

export default SelectionOpportunityDetailPage
