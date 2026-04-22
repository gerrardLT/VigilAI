import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { useWorkspace } from '../hooks/useWorkspace'
import { api } from '../services/api'
import type { AnalysisResultItem } from '../types'
import {
  getAnalysisFieldLabel,
  getAnalysisStatusLabel,
  localizeAnalysisTemplate,
  localizeAnalysisText,
} from '../utils/analysisI18n'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'

const STATUS_STYLES = {
  passed: 'bg-emerald-100 text-emerald-700',
  watch: 'bg-amber-100 text-amber-700',
  rejected: 'bg-rose-100 text-rose-700',
} as const

const FILTER_OPTIONS = [
  { value: '', label: '全部', testId: 'analysis-results-filter-all' },
  { value: 'passed', label: '通过', testId: 'analysis-results-filter-passed' },
  { value: 'watch', label: '待观察', testId: 'analysis-results-filter-watch' },
  { value: 'rejected', label: '淘汰', testId: 'analysis-results-filter-rejected' },
] as const

function buildTemplateDiagnosis(args: {
  total: number
  passed: number
  watch: number
  rejected: number
  templateName?: string | null
}) {
  const { total, passed, watch, rejected, templateName } = args
  const name = templateName || '当前模板'

  if (total <= 0) {
    return {
      title: '当前还没有模板判断样本',
      description: `${name} 还没有完成足够的判断样本，先跑一轮结果再看诊断。`,
      suggestion: '先去运行模板分析',
      tone: 'slate' as const,
    }
  }

  if (rejected / total >= 0.85 && passed === 0 && watch <= 1) {
    return {
      title: '当前模板偏严格',
      description: '几乎所有机会都被拦掉了',
      detail: '说明规则可能过早阻断了潜在机会。',
      suggestion: '优先放宽一条硬门槛',
      tone: 'rose' as const,
    }
  }

  if (passed / total >= 0.7 && rejected <= 1 && total >= 4) {
    return {
      title: '当前模板偏宽松',
      description: '放行比例偏高，建议补一条更明确的过滤条件。',
      detail: '避免噪音机会进入视野。',
      suggestion: '补一条最关键的过滤条件',
      tone: 'amber' as const,
    }
  }

  return {
    title: '当前模板基本平衡',
    description: '通过、观察、拦截的结构比较均衡。',
    detail: '可以继续围绕高频原因做小步微调。',
    suggestion: '继续观察最近的拦截位置和理由条数',
    tone: 'emerald' as const,
  }
}

function getToneClasses(tone: 'emerald' | 'rose' | 'amber' | 'slate') {
  if (tone === 'emerald') return 'border-emerald-200 bg-emerald-50/70 text-emerald-950'
  if (tone === 'rose') return 'border-rose-200 bg-rose-50/80 text-rose-950'
  if (tone === 'amber') return 'border-amber-200 bg-amber-50/80 text-amber-950'
  return 'border-slate-200 bg-slate-50 text-slate-900'
}

function getResultSummary(item: AnalysisResultItem) {
  return buildActivityDisplayExcerpt(item) || localizeAnalysisText(item.score_reason) || '暂无摘要'
}

export function AnalysisResultsPage() {
  const { defaultTemplate } = useAnalysisTemplates()
  const localizedDefaultTemplate = defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null
  const { workspace, loading: workspaceLoading, error: workspaceError, refetch: refetchWorkspace } = useWorkspace()
  const [results, setResults] = useState<AnalysisResultItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analysisStatusFilter, setAnalysisStatusFilter] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function fetchResults() {
      setLoading(true)
      setError(null)

      try {
        const response = await api.getAnalysisResults({
          analysis_status: analysisStatusFilter || undefined,
          page: 1,
          page_size: 20,
        })

        if (!cancelled) {
          setResults(response.items)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载分析结果失败')
          setResults([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void fetchResults()

    return () => {
      cancelled = true
    }
  }, [analysisStatusFilter, reloadKey])

  if (workspaceLoading && !workspace) {
    return <Loading text="正在加载分析结果..." />
  }

  if (workspaceError && !workspace) {
    return <ErrorMessage message={workspaceError} onRetry={refetchWorkspace} />
  }

  const analysisOverview = workspace?.analysis_overview ?? { total: 0, passed: 0, watch: 0, rejected: 0 }
  const diagnosis = buildTemplateDiagnosis({
    ...analysisOverview,
    templateName: localizedDefaultTemplate?.name,
  })

  return (
    <div className="space-y-6" data-testid="analysis-results-page">
      <section className="rounded-[28px] border border-slate-200 bg-gradient-to-r from-slate-950 via-slate-900 to-sky-900 p-8 text-white shadow-xl">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="text-sm uppercase tracking-[0.2em] text-sky-200">AI 智能代理决策记录</div>
            <h1 className="text-3xl font-semibold tracking-tight">AI 分析结果</h1>
            <p className="max-w-3xl text-sm leading-7 text-slate-100">
              这里集中展示当前模板放行了什么、保留观察了什么、又拦截了什么，方便你直接判断规则是该收紧还是放宽。
            </p>
            <div
              data-testid="analysis-results-active-template"
              className="inline-flex w-fit items-center rounded-full border border-sky-300/40 bg-white/10 px-4 py-2 text-sm text-sky-100"
            >
              当前模板：{localizedDefaultTemplate?.name ?? '未设置默认模板'}
            </div>
          </div>

          <div
            data-testid="analysis-results-overview"
            className="grid grid-cols-2 gap-3 rounded-2xl border border-white/10 bg-white/10 p-4 md:grid-cols-4"
          >
            <div className="rounded-xl bg-black/10 p-3">
              <div className="text-xs uppercase tracking-wide text-sky-100">总样本</div>
              <div className="mt-2 text-2xl font-semibold">{analysisOverview.total}</div>
            </div>
            <div className="rounded-xl bg-emerald-500/15 p-3">
              <div className="text-xs uppercase tracking-wide text-emerald-100">通过</div>
              <div className="mt-2 text-2xl font-semibold">{analysisOverview.passed}</div>
            </div>
            <div className="rounded-xl bg-amber-500/15 p-3">
              <div className="text-xs uppercase tracking-wide text-amber-100">待观察</div>
              <div className="mt-2 text-2xl font-semibold">{analysisOverview.watch}</div>
            </div>
            <div className="rounded-xl bg-rose-500/15 p-3">
              <div className="text-xs uppercase tracking-wide text-rose-100">拦截</div>
              <div className="mt-2 text-2xl font-semibold">{analysisOverview.rejected}</div>
            </div>
          </div>
        </div>
      </section>

      <section
        data-testid="analysis-results-diagnosis"
        className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="text-sm font-medium text-slate-500">模板诊断</div>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">{diagnosis.title}</h2>
            <div className={`mt-4 rounded-2xl border p-4 ${getToneClasses(diagnosis.tone)}`}>
              <p className="text-sm leading-6">{diagnosis.description}</p>
              {'detail' in diagnosis && diagnosis.detail ? <p className="mt-2 text-sm leading-6">{diagnosis.detail}</p> : null}
              <p className="mt-3 text-sm font-medium">{diagnosis.suggestion}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Link to="/analysis/templates" className="btn btn-secondary">
              去优化模板
            </Link>
            <Link to="/activities?analysis_status=rejected" className="btn btn-secondary">
              查看被拦截机会
            </Link>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {FILTER_OPTIONS.map(option => {
              const active = analysisStatusFilter === option.value
              return (
                <button
                  key={option.testId}
                  type="button"
                  aria-pressed={active}
                  data-testid={option.testId}
                  onClick={() => setAnalysisStatusFilter(option.value)}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                    active ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {option.label}
                </button>
              )
            })}
          </div>

          <button type="button" onClick={() => setReloadKey(value => value + 1)} className="btn btn-secondary">
            刷新结果
          </button>
        </div>
      </section>

      {error ? (
        <ErrorMessage message={error} onRetry={() => setReloadKey(value => value + 1)} />
      ) : loading ? (
        <Loading text="正在刷新结果..." />
      ) : results.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center">
          <div className="text-lg font-semibold text-slate-900">暂时还没有分析结果</div>
          <p className="mt-2 text-sm text-slate-500">可以先运行当前模板，或者切换筛选条件查看其他状态。</p>
        </div>
      ) : (
        <section className="space-y-4">
          {results.map(item => {
            const summaryReasons = (item.analysis_summary_reasons ?? []).map(reason => localizeAnalysisText(reason))
            const failedLayerLabel = item.analysis_failed_layer ? getAnalysisFieldLabel(item.analysis_failed_layer) : ''

            return (
              <Link
                key={item.id}
                to={`/activities/${item.id}`}
                className="block rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-200 hover:shadow-md"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-semibold text-slate-900">{buildActivityDisplayTitle(item)}</h2>
                      {item.analysis_status && (
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                            STATUS_STYLES[item.analysis_status] ?? 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {getAnalysisStatusLabel(item.analysis_status)}
                        </span>
                      )}
                      {item.analysis_failed_layer && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          拦截位置：{failedLayerLabel}
                        </span>
                      )}
                    </div>

                    <p className="text-sm leading-6 text-slate-600">{getResultSummary(item)}</p>

                    {summaryReasons.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {summaryReasons.map(reason => (
                          <span key={`${item.id}-${reason}`} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600">
                            {reason}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="grid min-w-[180px] gap-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                    <div className="flex items-center justify-between gap-3">
                      <span>来源</span>
                      <span className="font-medium text-slate-900">{localizeAnalysisText(item.source_name)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span>评分</span>
                      <span className="font-medium text-slate-900">
                        {item.score !== undefined && item.score !== null ? item.score.toFixed(1) : '--'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span>{item.analysis_status === 'rejected' ? '理由条数' : '理由数'}</span>
                      <span className="font-medium text-slate-900">{summaryReasons.length}</span>
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </section>
      )}
    </div>
  )
}

export default AnalysisResultsPage
