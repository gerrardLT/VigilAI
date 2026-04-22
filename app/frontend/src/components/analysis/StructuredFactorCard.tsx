interface StructuredFactorCardProps {
  structured: Record<string, unknown>
}

function formatStructuredValue(value: unknown) {
  if (value === null || value === undefined) {
    return 'N/A'
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

export function StructuredFactorCard({ structured }: StructuredFactorCardProps) {
  const entries = Object.entries(structured)

  return (
    <section
      data-testid="agent-analysis-structured-card"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h3 className="text-base font-semibold text-slate-900">Structured Factors</h3>
      <p className="mt-1 text-sm text-slate-500">把模型输出压成结构化字段，方便复核和后续批量筛选。</p>

      {entries.length === 0 ? (
        <div className="mt-4 rounded-xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
          暂无结构化字段。
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {entries.map(([key, value]) => (
            <div key={key} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">{key}</div>
              <div className="mt-2 text-sm font-medium text-slate-900">{formatStructuredValue(value)}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default StructuredFactorCard
