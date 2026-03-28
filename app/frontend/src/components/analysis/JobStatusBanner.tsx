import { formatDateTime } from '../../utils/formatDate'

interface JobStatusBannerJob {
  id: string
  status: string
  scope_type: string
  trigger_type: string
  created_at: string
  finished_at?: string | null
  item_count: number
  completed_items?: number
  failed_items?: number
  needs_research_count?: number
}

interface JobStatusBannerProps {
  job: JobStatusBannerJob | null
  title?: string
}

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  running: 'bg-sky-100 text-sky-700',
  pending: 'bg-amber-100 text-amber-700',
  failed: 'bg-rose-100 text-rose-700',
}

export function JobStatusBanner({ job, title = 'Latest agent-analysis batch' }: JobStatusBannerProps) {
  if (!job) {
    return null
  }

  return (
    <section
      data-testid="agent-analysis-job-banner"
      className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-900">{job.id}</h2>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                STATUS_STYLES[job.status] ?? 'bg-slate-200 text-slate-700'
              }`}
            >
              {job.status}
            </span>
            <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
              {job.scope_type} / {job.trigger_type}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-600">
            Created {formatDateTime(job.created_at)}
            {job.finished_at ? ` · Finished ${formatDateTime(job.finished_at)}` : ''}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-white px-3 py-2">
            <div className="text-xs text-slate-500">Items</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{job.item_count}</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2">
            <div className="text-xs text-slate-500">Completed</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{job.completed_items ?? '--'}</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2">
            <div className="text-xs text-slate-500">Failed</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{job.failed_items ?? '--'}</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2">
            <div className="text-xs text-slate-500">Research</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{job.needs_research_count ?? '--'}</div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default JobStatusBanner
