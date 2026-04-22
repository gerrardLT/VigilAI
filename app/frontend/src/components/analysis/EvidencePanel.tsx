import type { AgentAnalysisEvidence } from '../../types'

interface EvidencePanelProps {
  evidence: AgentAnalysisEvidence[]
}

export function EvidencePanel({ evidence }: EvidencePanelProps) {
  return (
    <section
      data-testid="agent-analysis-evidence-panel"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h3 className="text-base font-semibold text-slate-900">Evidence</h3>
      <p className="mt-1 text-sm text-slate-500">这里展示 research 或筛选阶段留下的证据摘要。</p>

      {evidence.length === 0 ? (
        <div className="mt-4 rounded-xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
          当前 draft 还没有外部证据。
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {evidence.map(item => (
            <article key={item.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="rounded-full bg-white px-2 py-1 font-medium text-slate-700">
                  {item.source_type}
                </span>
                {item.relevance_score !== undefined && item.relevance_score !== null && (
                  <span>relevance {item.relevance_score}</span>
                )}
              </div>
              <div className="mt-2 text-sm font-semibold text-slate-900">{item.title ?? item.url ?? 'Untitled evidence'}</div>
              {item.snippet && <p className="mt-2 text-sm leading-6 text-slate-600">{item.snippet}</p>}
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex text-sm font-medium text-sky-700 hover:text-sky-800"
                >
                  打开来源
                </a>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

export default EvidencePanel
