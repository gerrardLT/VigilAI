import type { OpportunityAiFilterResponse } from '../types'

interface OpportunityAiFilterPanelProps {
  value: string
  loading: boolean
  error: string | null
  summary: OpportunityAiFilterResponse | null
  onChange: (value: string) => void
  onSubmit: () => void
  onClear: () => void
}

export function OpportunityAiFilterPanel({
  value,
  loading,
  error,
  summary,
  onChange,
  onSubmit,
  onClear,
}: OpportunityAiFilterPanelProps) {
  return (
    <section className="space-y-4 rounded-2xl border border-sky-100 bg-sky-50/70 p-4">
      <div className="space-y-1">
        <div className="text-xs font-medium uppercase tracking-[0.24em] text-sky-700">AI 精筛</div>
        <h2 className="text-lg font-semibold text-slate-900">用一句中文描述你真正想找的机会</h2>
        <p className="text-sm text-slate-600">系统会在当前候选机会中进一步筛选，只保留符合条件的结果。</p>
      </div>

      <textarea
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder="例如：只保留适合独立开发者、奖金明确、两周内截止的线上机会"
        className="min-h-[104px] w-full rounded-2xl border border-sky-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400"
      />

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onSubmit}
          disabled={loading || !value.trim()}
          className="rounded-full bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {loading ? 'AI 精筛中...' : '开始 AI 精筛'}
        </button>
        <button
          type="button"
          onClick={onClear}
          className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
        >
          清除 AI 条件
        </button>
      </div>

      {summary && (
        <div className="grid gap-3 rounded-2xl border border-sky-100 bg-white p-4 md:grid-cols-[2fr_1fr_1fr_1fr]">
          <div>
            <div className="text-xs text-slate-500">识别意图</div>
            <div className="mt-1 text-sm font-medium text-slate-900">{summary.parsed_intent_summary}</div>
            {summary.reason_summary ? (
              <div className="mt-2 text-xs text-slate-500">{summary.reason_summary}</div>
            ) : null}
          </div>
          <div>
            <div className="text-xs text-slate-500">候选总数</div>
            <div className="mt-1 text-lg font-semibold text-slate-900">{summary.candidate_count}</div>
          </div>
          <div>
            <div className="text-xs text-emerald-600">保留</div>
            <div className="mt-1 text-lg font-semibold text-emerald-700">保留 {summary.matched_count} 个</div>
          </div>
          <div>
            <div className="text-xs text-rose-600">未保留</div>
            <div className="mt-1 text-lg font-semibold text-rose-700">{summary.discarded_count} 个</div>
          </div>
        </div>
      )}

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
    </section>
  )
}

export default OpportunityAiFilterPanel
