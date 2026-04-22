interface DraftBatchToolbarProps {
  selectedCount: number
  busy?: boolean
  onApprove: () => void
  onReject?: () => void
  onDeepResearch?: () => void
}

export function DraftBatchToolbar({
  selectedCount,
  busy = false,
  onApprove,
  onReject,
  onDeepResearch,
}: DraftBatchToolbarProps) {
  const disabled = selectedCount === 0 || busy

  return (
    <section
      data-testid="agent-analysis-batch-toolbar"
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-900">Draft batch review</div>
          <div className="mt-1 text-sm text-slate-500">{selectedCount} items selected for agent review actions</div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="agent-analysis-batch-approve"
            onClick={onApprove}
            disabled={disabled}
            className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Batch approve
          </button>
          {onReject && (
            <button
              type="button"
              data-testid="agent-analysis-batch-reject"
              onClick={onReject}
              disabled={disabled}
              className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            >
              Batch reject
            </button>
          )}
          {onDeepResearch && (
            <button
              type="button"
              data-testid="agent-analysis-batch-deep-research"
              onClick={onDeepResearch}
              disabled={disabled}
              className="rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 transition hover:bg-sky-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            >
              Deep research
            </button>
          )}
        </div>
      </div>
    </section>
  )
}

export default DraftBatchToolbar
