import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { JobStatusBanner } from '../components/analysis/JobStatusBanner'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { useAgentAnalysisJobs } from '../hooks/useAgentAnalysisJobs'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { useWorkspace } from '../hooks/useWorkspace'
import { api } from '../services/api'
import type { AnalysisResultItem, AgentAnalysisJobSummary } from '../types'

const STATUS_STYLES = {
  passed: 'bg-emerald-100 text-emerald-700',
  watch: 'bg-amber-100 text-amber-700',
  rejected: 'bg-rose-100 text-rose-700',
} as const

const STATUS_LABELS = {
  passed: '通过',
  watch: '观察',
  rejected: '拦截',
} as const

const FILTER_OPTIONS = [
  { value: '', label: '全部', testId: 'analysis-results-filter-all' },
  { value: 'passed', label: '通过', testId: 'analysis-results-filter-passed' },
  { value: 'watch', label: '观察', testId: 'analysis-results-filter-watch' },
  { value: 'rejected', label: '拦截', testId: 'analysis-results-filter-rejected' },
] as const

function pickLatestBatchJob(jobs: AgentAnalysisJobSummary[]): AgentAnalysisJobSummary | null {
  return jobs.find(job => job.scope_type === 'batch') ?? null
}

export function AnalysisResultsPage() {
  const { defaultTemplate } = useAnalysisTemplates()
  const { workspace, loading: workspaceLoading, error: workspaceError, refetch: refetchWorkspace } = useWorkspace()
  const {
    jobs: agentJobs,
    activeJob: activeAgentJob,
    loading: agentJobsLoading,
    error: agentJobsError,
    refetch: refetchAgentJobs,
    loadJob: loadAgentJob,
  } = useAgentAnalysisJobs()
  const [results, setResults] = useState<AnalysisResultItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analysisStatusFilter, setAnalysisStatusFilter] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const latestBatchJobSummary = useMemo(() => pickLatestBatchJob(agentJobs), [agentJobs])

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
          const message = err instanceof Error ? err.message : '加载分析结果失败'
          setError(message)
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

  useEffect(() => {
    if (!latestBatchJobSummary || selectedJobId) {
      return
    }

    setSelectedJobId(latestBatchJobSummary.id)
  }, [latestBatchJobSummary, selectedJobId])

  useEffect(() => {
    if (!selectedJobId) {
      return
    }

    if (activeAgentJob?.id === selectedJobId) {
      return
    }

    void loadAgentJob(selectedJobId)
  }, [activeAgentJob?.id, loadAgentJob, selectedJobId])

  if (workspaceLoading && !workspace) {
    return <Loading text="正在加载分析结果..." />
  }

  if (workspaceError && !workspace) {
    return <ErrorMessage message={workspaceError} onRetry={refetchWorkspace} />
  }

  const analysisOverview = workspace?.analysis_overview ?? {
    total: 0,
    passed: 0,
    watch: 0,
    rejected: 0,
  }
  const displayedJob =
    activeAgentJob && activeAgentJob.scope_type === 'batch' ? activeAgentJob : null
  const bannerJob = displayedJob ?? latestBatchJobSummary

  return (
    <div className="space-y-6" data-testid="analysis-results-page">
      <section className="rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-slate-900 to-sky-900 p-8 text-white shadow-xl">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="text-sm uppercase tracking-[0.2em] text-sky-200">Analysis Results</div>
            <h1 className="text-3xl font-bold">AI 分析结果</h1>
            <p className="max-w-3xl text-sm leading-7 text-slate-100">
              这里集中展示当前模板放行了什么、保留观察了什么、又拦截了什么，方便你直接判断规则是不是该收紧或放宽。
            </p>
            <div
              data-testid="analysis-results-active-template"
              className="inline-flex w-fit items-center rounded-full border border-sky-300/40 bg-white/10 px-4 py-2 text-sm text-sky-100"
            >
              当前模板：{defaultTemplate?.name ?? '未设置默认模板'}
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
              <div className="text-xs uppercase tracking-wide text-amber-100">观察</div>
              <div className="mt-2 text-2xl font-semibold">{analysisOverview.watch}</div>
            </div>
            <div className="rounded-xl bg-rose-500/15 p-3">
              <div className="text-xs uppercase tracking-wide text-rose-100">拦截</div>
              <div className="mt-2 text-2xl font-semibold">{analysisOverview.rejected}</div>
            </div>
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
          <div className="flex flex-wrap gap-2">
            <Link to="/analysis/templates" className="btn btn-secondary">
              优化模板
            </Link>
            <button
              type="button"
              onClick={() => {
                setReloadKey(value => value + 1)
                void refetchAgentJobs()
              }}
              className="btn btn-secondary"
            >
              刷新结果
            </button>
          </div>
        </div>
      </section>

      {bannerJob && (
        <JobStatusBanner
          job={bannerJob}
          title="Latest batch operations console"
        />
      )}

      <section
        data-testid="analysis-results-job-list"
        className="grid gap-4 xl:grid-cols-[320px_1fr]"
      >
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Batch jobs</h2>
              <p className="mt-1 text-sm text-slate-500">Review recent agent-analysis runs and inspect failed items.</p>
            </div>
            {agentJobsLoading && <span className="text-xs text-slate-400">Loading...</span>}
          </div>

          <div className="mt-4 space-y-3">
            {agentJobs.map(job => {
              const active = selectedJobId === job.id
              return (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => setSelectedJobId(job.id)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                    active
                      ? 'border-sky-300 bg-sky-50'
                      : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold text-slate-900">{job.id}</span>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
                      {job.status}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-slate-500">
                    {job.item_count} items · {job.completed_items} completed · {job.failed_items} failed
                  </div>
                </button>
              )
            })}

            {agentJobs.length === 0 && (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                No batch jobs yet.
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Selected job detail</h2>
              <p className="mt-1 text-sm text-slate-500">Focus the review queue on batch outcomes that still need attention.</p>
            </div>
            {displayedJob && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                {displayedJob.items.length} items
              </span>
            )}
          </div>

          {agentJobsError && (
            <div className="mt-4">
              <ErrorMessage message={agentJobsError} onRetry={refetchAgentJobs} />
            </div>
          )}

          {displayedJob ? (
            <div className="mt-4 space-y-3">
              {displayedJob.items.map(item => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">
                        Activity: {item.activity?.title ?? item.activity_id}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {item.id} · {item.status} · draft {item.draft?.status ?? item.final_draft_status ?? 'n/a'}
                      </div>
                    </div>
                    {item.needs_research && (
                      <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                        Needs research
                      </span>
                    )}
                  </div>

                  <p className="mt-3 text-sm text-slate-600">
                    {item.draft?.summary ?? 'No draft summary available for this job item.'}
                  </p>

                  {(item.draft?.reasons ?? []).length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.draft?.reasons.map(reason => (
                        <span
                          key={`${item.id}-${reason}`}
                          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600"
                        >
                          Reason: {reason}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-sm text-slate-500">
              Pick a batch job to inspect its item-level draft results.
            </div>
          )}
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
            const summaryReasons = item.analysis_summary_reasons ?? []
            return (
              <Link
                key={item.id}
                to={`/activities/${item.id}`}
                className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-200 hover:shadow-md"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-semibold text-slate-900">{item.title}</h2>
                      {item.analysis_status && (
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                            STATUS_STYLES[item.analysis_status] ?? 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {STATUS_LABELS[item.analysis_status] ?? item.analysis_status}
                        </span>
                      )}
                      {item.analysis_failed_layer && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          失败层：{item.analysis_failed_layer}
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-6 text-slate-600">{item.summary || item.description || '暂无摘要'}</p>
                    {summaryReasons.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {summaryReasons.map(reason => (
                          <span
                            key={`${item.id}-${reason}`}
                            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
                          >
                            {reason}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="min-w-[180px] rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                    <div className="flex items-center justify-between gap-3">
                      <span>来源</span>
                      <span className="font-medium text-slate-900">{item.source_name}</span>
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-3">
                      <span>评分</span>
                      <span className="font-medium text-slate-900">
                        {item.score !== undefined && item.score !== null ? item.score.toFixed(1) : '--'}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-3">
                      <span>原因数</span>
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
