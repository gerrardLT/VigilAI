import { useState } from 'react'

interface ReviewActionBarProps {
  reviewing?: boolean
  onApprove: (note: string) => void | Promise<void>
  onReject: (note: string) => void | Promise<void>
}

export function ReviewActionBar({
  reviewing = false,
  onApprove,
  onReject,
}: ReviewActionBarProps) {
  const [note, setNote] = useState('')

  return (
    <section
      data-testid="agent-analysis-review-bar"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Review & Writeback</h3>
          <p className="mt-1 text-sm text-slate-500">确认 draft 后才会写回 activity 真值；拒绝不会污染主数据。</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void onApprove(note)}
            disabled={reviewing}
            className="btn btn-primary"
          >
            {reviewing ? 'Submitting...' : 'Approve Draft'}
          </button>
          <button
            type="button"
            onClick={() => void onReject(note)}
            disabled={reviewing}
            className="btn btn-secondary"
          >
            Reject Draft
          </button>
        </div>
      </div>

      <label className="mt-4 block space-y-2">
        <span className="text-sm font-medium text-slate-700">Review Note</span>
        <textarea
          aria-label="Agent analysis review note"
          value={note}
          onChange={event => setNote(event.target.value)}
          rows={3}
          className="input min-h-24 w-full py-3"
          placeholder="记录你为什么批准、拒绝，或者需要补什么证据。"
        />
      </label>
    </section>
  )
}

export default ReviewActionBar
