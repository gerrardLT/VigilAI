import type { AgentAnalysisStep } from '../../types'

interface ExecutionTracePanelProps {
  steps: AgentAnalysisStep[]
}

const STEP_STATUS_STYLES: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
  running: 'bg-amber-100 text-amber-700',
}

export function ExecutionTracePanel({ steps }: ExecutionTracePanelProps) {
  return (
    <section
      data-testid="agent-analysis-trace-panel"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h3 className="text-base font-semibold text-slate-900">Execution Trace</h3>
      <p className="mt-1 text-sm text-slate-500">保留每一步的可审查输出，但不暴露隐藏推理。</p>

      {steps.length === 0 ? (
        <div className="mt-4 rounded-xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
          暂无执行轨迹。
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {steps.map(step => (
            <div key={step.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{step.step_type}</div>
                  <div className="text-xs text-slate-500">{step.model_name ?? 'mock/default model'}</div>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    STEP_STATUS_STYLES[step.step_status] ?? 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {step.step_status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default ExecutionTracePanel
