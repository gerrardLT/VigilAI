import type { AgentAnalysisSnapshot } from '../../types'

const SNAPSHOT_STATUS_STYLES: Record<string, string> = {
  pass: 'bg-emerald-100 text-emerald-700',
  watch: 'bg-amber-100 text-amber-700',
  reject: 'bg-rose-100 text-rose-700',
  insufficient_evidence: 'bg-slate-100 text-slate-700',
}

const SNAPSHOT_STATUS_LABELS: Record<string, string> = {
  pass: '通过',
  watch: '待观察',
  reject: '拦截',
  insufficient_evidence: '证据不足',
}

interface AgentVerdictCardProps {
  snapshot: AgentAnalysisSnapshot | null
  onRun: () => void
  running?: boolean
}

export function AgentVerdictCard({ snapshot, onRun, running = false }: AgentVerdictCardProps) {
  const status = snapshot?.status ?? 'insufficient_evidence'
  const reasons = snapshot?.reasons ?? []

  return (
    <section
      data-testid="agent-analysis-verdict-card"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">AI 判断结果</h3>
          <p className="mt-1 text-sm text-slate-500">
            运行深度分析后，这里会展示可复核的草稿结论、证据和执行轨迹。
          </p>
        </div>
        <button type="button" onClick={onRun} disabled={running} className="btn btn-primary">
          {running ? '分析中...' : '深度分析'}
        </button>
      </div>

      <div className="mt-4">
        <span
          className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${
            SNAPSHOT_STATUS_STYLES[status] ?? SNAPSHOT_STATUS_STYLES.insufficient_evidence
          }`}
        >
          {SNAPSHOT_STATUS_LABELS[status] ?? status}
        </span>
      </div>

      <div className="mt-4 text-sm leading-6 text-slate-700">
        {snapshot?.summary ?? '还没有 AI 分析草稿。点击“深度分析”开始一次可审查的深入分析。'}
      </div>

      {reasons.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {reasons.map(reason => (
            <span
              key={reason}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
            >
              {reason}
            </span>
          ))}
        </div>
      )}

      {snapshot?.risk_flags && snapshot.risk_flags.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">风险标记</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {snapshot.risk_flags.map(flag => (
              <span
                key={flag}
                className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs text-rose-700"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

export default AgentVerdictCard
