import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { productSelectionApi } from '../../services/productSelectionApi'
import type {
  ProductSelectionAutomationRun,
  ProductSelectionAutomationRunResult,
  ProductSelectionOperationsRun,
  ProductSelectionOperationsRunResult,
  ProductSelectionWorkspaceResponse,
} from '../../types'

function formatPlatform(platform: string) {
  return platform === 'taobao' ? 'Taobao' : platform === 'xianyu' ? 'Xianyu' : platform
}

function formatPriceRange(low: number | null, mid: number | null, high: number | null) {
  const values = [low, mid, high].filter((value): value is number => value !== null)
  if (values.length === 0) return 'N/A'
  if (values.length === 1) return `RMB ${values[0].toFixed(0)}`
  return `RMB ${Math.min(...values).toFixed(0)} - RMB ${Math.max(...values).toFixed(0)}`
}

function getAutomationMetric(run: ProductSelectionAutomationRun, key: string) {
  const value = run.result_payload[key]
  return typeof value === 'number' ? value : null
}

function buildAutomationSummary(result: ProductSelectionAutomationRunResult) {
  return `Triggered ${result.triggered_queries} reruns, shortlisted ${result.candidate_count} candidates, and promoted ${result.tracked_count} tracked items.`
}

function getOperationsMetric(run: ProductSelectionOperationsRun, key: string) {
  const value = run.result_payload[key]
  return typeof value === 'number' ? value : null
}

function buildOperationsSummary(result: ProductSelectionOperationsRunResult) {
  return `Reviewed ${result.due_count} due tracking items and refreshed ${result.processed_count} follow-up reminders.`
}

export function SelectionWorkspacePage() {
  const [workspace, setWorkspace] = useState<ProductSelectionWorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [automationRunning, setAutomationRunning] = useState(false)
  const [automationSummary, setAutomationSummary] = useState<string | null>(null)
  const [operationsRunning, setOperationsRunning] = useState(false)
  const [operationsSummary, setOperationsSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadWorkspace() {
    setLoading(true)
    setError(null)
    try {
      const response = await productSelectionApi.getWorkspace()
      setWorkspace(response)
    } catch (err) {
      setWorkspace(null)
      setError(err instanceof Error ? err.message : 'Failed to load selection workspace')
    } finally {
      setLoading(false)
    }
  }

  async function handleRunAutomation() {
    setAutomationRunning(true)
    setError(null)

    try {
      const result = await productSelectionApi.createAutomationRun({
        requested_by: 'selection_workspace',
      })
      setAutomationSummary(buildAutomationSummary(result))
      await loadWorkspace()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run selection automation')
    } finally {
      setAutomationRunning(false)
    }
  }

  async function handleRunOperations() {
    setOperationsRunning(true)
    setError(null)

    try {
      const result = await productSelectionApi.createOperationsRun({
        requested_by: 'selection_workspace',
      })
      setOperationsSummary(buildOperationsSummary(result))
      await loadWorkspace()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run selection operations')
    } finally {
      setOperationsRunning(false)
    }
  }

  useEffect(() => {
    void loadWorkspace()
  }, [])

  if (loading && !workspace) {
    return <Loading text="Loading selection workspace..." />
  }

  if (error && !workspace) {
    return <ErrorMessage message={error} onRetry={() => void loadWorkspace()} />
  }

  if (!workspace) {
    return null
  }

  return (
    <main className="space-y-6" data-testid="selection-workspace-page">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
              Product Selection MVP
            </span>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Selection Workspace</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                Review recent research jobs, high-score opportunities, and the current follow-up
                queue for Taobao and Xianyu selection research.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void handleRunAutomation()}
              disabled={automationRunning}
            >
              {automationRunning ? 'Running Automation...' : 'Run Automation Cycle'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void handleRunOperations()}
              disabled={operationsRunning}
            >
              {operationsRunning ? 'Running Operations...' : 'Run Tracking Review'}
            </button>
            <Link to="/selection/opportunities" className="btn btn-primary">
              Open Opportunity Pool
            </Link>
            <Link to="/selection/tracking" className="btn btn-secondary">
              Open Tracking
            </Link>
          </div>
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void loadWorkspace()} /> : null}
      {automationSummary ? (
        <section className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-900">
          {automationSummary}
        </section>
      ) : null}
      {operationsSummary ? (
        <section className="rounded-2xl border border-sky-200 bg-sky-50 px-5 py-4 text-sm text-sky-900">
          {operationsSummary}
        </section>
      ) : null}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Queries</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.query_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Opportunities</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.opportunity_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Tracked</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.tracked_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Favorited</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.favorited_count}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">Due Follow-Ups</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">
            {workspace.overview.due_tracking_count}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Top Opportunities</h2>
              <p className="mt-1 text-sm text-slate-500">
                The highest-scoring items currently available in the selection pool.
              </p>
            </div>
            <Link to="/selection/opportunities" className="text-sm font-medium text-sky-700">
              View all
            </Link>
          </div>

          <div className="mt-4 space-y-4">
            {workspace.top_opportunities.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                No research results yet.
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
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                      Score {opportunity.opportunity_score.toFixed(1)}
                    </span>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                      Confidence {opportunity.confidence_score.toFixed(1)}
                    </span>
                  </div>
                  <h3 className="mt-3 text-lg font-semibold text-slate-900">{opportunity.title}</h3>
                  <div className="mt-2 text-sm text-slate-600">
                    {opportunity.category_path || 'Uncategorized'} |{' '}
                    {formatPriceRange(
                      opportunity.price_low,
                      opportunity.price_mid,
                      opportunity.price_high
                    )}
                  </div>
                </Link>
              ))
            )}
          </div>
        </article>

        <div className="space-y-6">
          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Automation Runs</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Recent automation cycles that rerun queries and promote high-score candidates.
                </p>
              </div>
              <button
                type="button"
                className="text-sm font-medium text-sky-700"
                onClick={() => void handleRunAutomation()}
                disabled={automationRunning}
              >
                {automationRunning ? 'Running...' : 'Run now'}
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {workspace.automation_runs.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  No automation run yet.
                </div>
              ) : (
                workspace.automation_runs.map(run => (
                  <div key={run.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                        {run.status}
                      </span>
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                        Queries {getAutomationMetric(run, 'triggered_queries') ?? 0}
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                        Tracked {getAutomationMetric(run, 'tracked_count') ?? 0}
                      </span>
                    </div>
                    <div className="mt-3 text-sm font-semibold text-slate-900">{run.id}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      Requested by {run.requested_by || 'unknown'} | Candidates{' '}
                      {getAutomationMetric(run, 'candidate_count') ?? 0}
                    </div>
                    {typeof run.result_payload.error === 'string' ? (
                      <div className="mt-2 text-sm text-rose-700">{run.result_payload.error}</div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Tracking Operations</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Recent review cycles that refresh due follow-ups for tracked opportunities.
                </p>
              </div>
              <button
                type="button"
                className="text-sm font-medium text-sky-700"
                onClick={() => void handleRunOperations()}
                disabled={operationsRunning}
              >
                {operationsRunning ? 'Running...' : 'Review now'}
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {workspace.operations_runs.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  No tracking review run yet.
                </div>
              ) : (
                workspace.operations_runs.map(run => (
                  <div key={run.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                        {run.status}
                      </span>
                      <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-800">
                        Due {getOperationsMetric(run, 'due_count') ?? 0}
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
                        Processed {getOperationsMetric(run, 'processed_count') ?? 0}
                      </span>
                    </div>
                    <div className="mt-3 text-sm font-semibold text-slate-900">{run.id}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      Requested by {run.requested_by || 'unknown'} | Reminders refreshed{' '}
                      {getOperationsMetric(run, 'processed_count') ?? 0}
                    </div>
                    {typeof run.result_payload.error === 'string' ? (
                      <div className="mt-2 text-sm text-rose-700">{run.result_payload.error}</div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Recent Queries</h2>
            <div className="mt-4 space-y-3">
              {workspace.recent_queries.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  No research job yet.
                </div>
              ) : (
                workspace.recent_queries.map(query => (
                  <div key={query.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-sm font-semibold text-slate-900">{query.query_text}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {query.query_type} | {query.platform_scope} | {query.status}
                    </div>
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Tracking Queue</h2>
            <div className="mt-4 space-y-3">
              {workspace.tracking_queue.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  No tracked item yet.
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
                      {item.status} | {formatPlatform(item.opportunity.platform)}
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
            <h2 className="text-xl font-semibold text-slate-900">Due Follow-Ups</h2>
            <div className="mt-4 space-y-3">
              {workspace.due_tracking_queue.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  No due follow-up item yet.
                </div>
              ) : (
                workspace.due_tracking_queue.map(item => (
                  <Link
                    key={`${item.opportunity_id}-due`}
                    to={`/selection/opportunities/${item.opportunity_id}`}
                    className="block rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:border-sky-200"
                  >
                    <div className="text-sm font-semibold text-slate-900">{item.opportunity.title}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {item.status} | {formatPlatform(item.opportunity.platform)}
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
            <h2 className="text-xl font-semibold text-slate-900">Platform Breakdown</h2>
            <div className="mt-4 space-y-3">
              {workspace.platform_breakdown.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  No platform data yet.
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
