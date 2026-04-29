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
          <h3 className="text-base font-semibold text-slate-900">复核与写回</h3>
          <p className="mt-1 text-sm text-slate-500">
            通过后会把结论写回机会主记录；拒绝则保留原数据，只退回当前草稿。
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void onApprove(note)}
            disabled={reviewing}
            className="btn btn-primary"
          >
            {reviewing ? '提交中...' : '通过草稿'}
          </button>
          <button
            type="button"
            onClick={() => void onReject(note)}
            disabled={reviewing}
            className="btn btn-secondary"
          >
            退回草稿
          </button>
        </div>
      </div>

      <label className="mt-4 block space-y-2">
        <span className="text-sm font-medium text-slate-700">复核备注</span>
        <textarea
          aria-label="AI 分析复核备注"
          value={note}
          onChange={event => setNote(event.target.value)}
          rows={3}
          className="input min-h-24 w-full py-3"
          placeholder="记录为什么通过、为什么退回，或还缺哪些证据。"
        />
      </label>
    </section>
  )
}

export default ReviewActionBar
