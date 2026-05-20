import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { OnboardingGuide } from '../components/OnboardingGuide'
import { VirtualList } from '../components/VirtualList'
import { useAgentSession } from '../hooks/useAgentSession'
import { useStreamingTurn } from '../hooks/useStreamingTurn'
import type {
  AgentArtifact,
  AgentDomainType,
  AgentMemoryScope,
  AgentPolicyMode,
  AgentReflection,
  AgentSessionState,
} from '../types'

function getTurnTone(role: string) {
  if (role === 'assistant') {
    return 'border-sky-100 bg-sky-50/70'
  }
  return 'border-slate-200 bg-white'
}

function formatToolName(toolName: string) {
  return toolName.split('_').join(' ')
}

function formatScore(value: number) {
  return value.toFixed(2)
}

const DOMAIN_OPTIONS: Array<{
  value: AgentDomainType
  label: string
  summary: string
}> = [
  {
    value: 'opportunity',
    label: 'Opportunity',
    summary: 'Search, explain, and plan follow-up for grants, bounties, and similar opportunities.',
  },
  {
    value: 'product_selection',
    label: 'Product Selection',
    summary: 'Research Taobao and Xianyu product ideas, shortlist candidates, and compare platforms.',
  },
]

const DOMAIN_COPY: Record<
  string,
  {
    badge: string
    description: string
    inputLabel: string
    placeholder: string
    emptyState: string
    helper: string
  }
> = {
  opportunity: {
    badge: 'Opportunity Toolset',
    description:
      'Run the shared agent shell against the opportunity domain for search, explanation, and next-action support.',
    inputLabel: 'Opportunity Prompt',
    placeholder: 'Example: Find solo-friendly grants with clear rewards this month',
    emptyState: 'No conversation yet. Send a message to start an agent session.',
    helper: 'This mode uses the opportunity toolset behind /api/agent/*.',
  },
  product_selection: {
    badge: 'Selection Toolset',
    description:
      'Run the same shared session shell against the product-selection domain for shortlist and comparison workflows.',
    inputLabel: 'Selection Prompt',
    placeholder: 'Example: Compare Taobao and Xianyu pet water fountain opportunities',
    emptyState: 'No conversation yet. Switch domains at any time to start a fresh session.',
    helper: 'This mode uses the product-selection toolset behind /api/agent/*.',
  },
}

type SelectionArtifactPayload = {
  job?: { id?: string }
  shortlist?: Array<{ id?: string }>
  compare_rows?: Array<{ id?: string }>
}

function getArtifactLinks(
  domainType: AgentDomainType,
  artifact: AgentArtifact
): Array<{ label: string; to: string }> {
  if (domainType !== 'product_selection') {
    return []
  }

  const payload = artifact.payload as SelectionArtifactPayload
  const links: Array<{ label: string; to: string }> = []
  const jobId = payload.job?.id
  const compareIds = (payload.compare_rows || [])
    .map(item => item.id)
    .filter((value): value is string => Boolean(value))
    .slice(0, 5)

  if (jobId) {
    links.push({
      label: 'Open shortlist',
      to: `/selection/opportunities?query_id=${encodeURIComponent(jobId)}`,
    })
  } else if ((payload.shortlist || []).length > 0) {
    links.push({ label: 'Open selection pool', to: '/selection/opportunities' })
  }

  if (compareIds.length >= 2) {
    const query = compareIds.map(id => `ids=${encodeURIComponent(id)}`).join('&')
    links.push({
      label: 'Open compare view',
      to: `/selection/compare?${query}`,
    })
  }

  return links
}

export function AgentWorkspacePage() {
  const [domainType, setDomainType] = useState<AgentDomainType>('opportunity')
  const [policyMode, setPolicyMode] = useState<AgentPolicyMode>('standard')
  const [memoryScope, setMemoryScope] = useState<AgentMemoryScope>('domain')
  const [draft, setDraft] = useState('')
  const { session, turns, artifacts, context, loading, sending, error, sendTurn, refreshContext } =
    useAgentSession(domainType, { policyMode, memoryScope })
  const stream = useStreamingTurn()
  const copy = DOMAIN_COPY[domainType]
  const sessionState = context?.state ?? null
  const latestInsights = context?.insights.slice(0, 4) ?? []
  const latestThinkingSteps = context?.thinking_steps.slice(0, 4) ?? []
  const executionPlans = context?.execution_plans.slice(0, 3) ?? []
  const recalledMemories = context?.recalled_memories.slice(0, 3) ?? []
  const recalledReflections = context?.recalled_reflections.slice(0, 2) ?? []
  const memories = context?.memories.slice(0, 4) ?? []
  const reflections = context?.reflections.slice(0, 3) ?? []

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nextMessage = draft.trim()
    if (!nextMessage) {
      return
    }

    try {
      if (session?.id) {
        await stream.sendMessage(session.id, nextMessage)
      } else {
        await sendTurn(nextMessage)
      }
      setDraft('')
    } catch {
      // Error state is already managed by the hook.
    }
  }

  return (
    <main data-testid="agent-workspace-page" className="mx-auto max-w-6xl space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700">
              {copy.badge}
            </span>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Agent Workspace</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{copy.description}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <div>Domain: {domainType}</div>
            <div>Policy: {session?.policy_mode ?? policyMode}</div>
            <div>Memory Scope: {session?.memory_scope ?? memoryScope}</div>
            <div>Session: {session?.id ?? 'Not created yet'}</div>
            <div>Last tools: {sessionState?.last_tool_names.join(', ') || 'None yet'}</div>
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {DOMAIN_OPTIONS.map(option => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                setDomainType(option.value)
                setDraft('')
              }}
              aria-pressed={domainType === option.value}
              className={`rounded-2xl border px-4 py-4 text-left transition ${
                domainType === option.value
                  ? 'border-sky-300 bg-sky-50 shadow-sm'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="text-sm font-semibold text-slate-900">{option.label}</div>
              <div className="mt-1 text-sm leading-6 text-slate-600">{option.summary}</div>
            </button>
          ))}
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Policy Mode</span>
            <select
              aria-label="Policy Mode"
              value={policyMode}
              onChange={event => setPolicyMode(event.target.value as AgentPolicyMode)}
              className="input w-full py-3"
            >
              <option value="standard">Standard</option>
              <option value="strict">Strict</option>
            </select>
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Memory Scope</span>
            <select
              aria-label="Memory Scope"
              value={memoryScope}
              onChange={event => setMemoryScope(event.target.value as AgentMemoryScope)}
              className="input w-full py-3"
            >
              <option value="session_only">Session Only</option>
              <option value="domain">Domain</option>
              <option value="global">Global</option>
            </select>
          </label>
        </div>
      </section>

      {error && <ErrorMessage message={error} />}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Conversation</h2>
              <p className="mt-1 text-sm text-slate-500">{copy.helper}</p>
            </div>
            <div className="flex items-center gap-3">
              {session ? (
                <button type="button" className="btn btn-secondary" onClick={() => void refreshContext()}>
                  Refresh Context
                </button>
              ) : null}
              {(loading || sending) && <span className="text-sm text-sky-700">Working...</span>}
            </div>
          </div>

          <div className="space-y-3" aria-live="polite">
            {turns.length === 0 ? (
              <OnboardingGuide
                domainType={domainType}
                onSelectPrompt={(prompt) => setDraft(prompt)}
              />
            ) : turns.length > 50 ? (
              <VirtualList
                items={turns}
                estimateSize={100}
                className="h-[600px] overflow-auto"
                renderItem={(turn) => (
                  <article className={`rounded-2xl border px-4 py-4 ${getTurnTone(turn.role)}`}>
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {turn.role === 'assistant' ? 'Assistant' : 'User'}
                    </div>
                    <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">
                      {turn.content}
                    </p>
                  </article>
                )}
              />
            ) : (
              turns.map(turn => (
                <article
                  key={turn.id}
                  className={`rounded-2xl border px-4 py-4 ${getTurnTone(turn.role)}`}
                >
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {turn.role === 'assistant' ? 'Assistant' : 'User'}
                  </div>
                  <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">
                    {turn.content}
                  </p>
                </article>
              ))
            )}

            {stream.streaming && (
              <div className="rounded-2xl border border-sky-100 bg-sky-50/70 px-4 py-4">
                {Object.entries(stream.toolStatus).map(([tool, status]) => (
                  <div key={tool} className="text-xs text-sky-600">
                    {status === 'running' ? '🔧' : '✓'} {tool}
                  </div>
                ))}
                {stream.fullText && <p className="mt-2 text-sm text-slate-700">{stream.fullText}</p>}
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-3">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">{copy.inputLabel}</span>
              <textarea
                aria-label={copy.inputLabel}
                value={draft}
                onChange={event => setDraft(event.target.value)}
                rows={4}
                placeholder={copy.placeholder}
                className="input min-h-28 w-full py-3"
              />
            </label>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-slate-500">Switching domains starts a fresh shared agent session.</p>
              <button type="submit" className="btn btn-primary" disabled={sending || stream.streaming || !draft.trim()}>
                {stream.streaming ? 'Streaming...' : sending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Session Intelligence</h2>
            <p className="mt-1 text-sm text-slate-500">
              Current focus, next action, and working memory synthesized from recent turns.
            </p>

            {sessionState ? (
              <div className="mt-4 space-y-4">
                <SessionStateSummary state={sessionState} />
              </div>
            ) : (
              <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                No session context yet. Send a message to generate state, insights, and memory.
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Recalled Context</h2>
            <p className="mt-1 text-sm text-slate-500">
              Cross-session memory and reflection signals loaded before the assistant replies.
            </p>

            <div className="mt-4 space-y-3">
              {recalledMemories.length === 0 && recalledReflections.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  No recalled context yet.
                </div>
              ) : (
                <>
                  {recalledMemories.map(memory => (
                    <article key={memory.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Memory · {memory.memory_type}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-700">{memory.content}</p>
                    </article>
                  ))}
                  {recalledReflections.map(reflection => (
                    <ReflectionCard key={reflection.id} reflection={reflection} variant="recalled" />
                  ))}
                </>
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Execution Plans</h2>
            <p className="mt-1 text-sm text-slate-500">
              Persisted tool orchestration decisions, including policy mode, rationale, and blocked steps.
            </p>

            <div className="mt-4 space-y-3">
              {executionPlans.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  No execution plans yet.
                </div>
              ) : (
                executionPlans.map(plan => (
                  <article key={plan.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {plan.mode}
                      </span>
                      <span className="text-xs text-slate-500">
                        Runnable {plan.runnable_tools.length} | Blocked {plan.blocked_tools.length}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{plan.summary}</p>
                    <div className="mt-3 space-y-2">
                      {plan.requested_steps.map(step => (
                        <div
                          key={`${plan.id}-${step.tool_name}-${step.priority}`}
                          className="rounded-xl border border-slate-200 bg-white px-3 py-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              {step.tool_name}
                            </span>
                            <span className="text-xs text-slate-500">
                              {step.intent} | {step.policy_decision}
                            </span>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-slate-700">{step.rationale}</p>
                        </div>
                      ))}
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Insights and Thinking</h2>
            <p className="mt-1 text-sm text-slate-500">
              Latest extracted insights and reasoning steps recorded for this session.
            </p>

            <div className="mt-4 space-y-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Insights</div>
                {latestInsights.length === 0 ? (
                  <div className="mt-2 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-500">
                    No insight items yet.
                  </div>
                ) : (
                  <div className="mt-2 space-y-3">
                    {latestInsights.map(insight => (
                      <article key={insight.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {insight.insight_type}
                          </span>
                          <span className="text-xs text-slate-500">
                            Importance {formatScore(insight.importance)}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-slate-700">{insight.content}</p>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Thinking</div>
                {latestThinkingSteps.length === 0 ? (
                  <div className="mt-2 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-500">
                    No reasoning steps yet.
                  </div>
                ) : (
                  <div className="mt-2 space-y-3">
                    {latestThinkingSteps.map(step => (
                      <article key={step.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {step.phase}
                          </span>
                          <span className="text-xs text-slate-500">
                            {step.tool_name ? formatToolName(step.tool_name) : 'No tool call'}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-slate-700">{step.summary}</p>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Memory and Reflection Log</h2>
            <p className="mt-1 text-sm text-slate-500">
              Persistent learning signals stored for this session after each completed turn.
            </p>

            <div className="mt-4 space-y-3">
              {memories.length === 0 && reflections.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  No long-term memory or reflection records yet.
                </div>
              ) : (
                <>
                  {memories.map(memory => (
                    <article key={memory.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {memory.memory_type}
                        </span>
                        <span className="text-xs text-slate-500">
                          Importance {formatScore(memory.importance)}
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-700">{memory.content}</p>
                    </article>
                  ))}
                  {reflections.map(reflection => (
                    <ReflectionCard key={reflection.id} reflection={reflection} variant="saved" />
                  ))}
                </>
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Artifacts</h2>
            <p className="mt-1 text-sm text-slate-500">
              Shared agent sessions persist intermediate outputs as reusable artifacts.
            </p>

            <div className="mt-4 space-y-3">
              {artifacts.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  No artifacts yet.
                </div>
              ) : (
                artifacts.map(artifact => {
                  const links = getArtifactLinks(domainType, artifact)
                  return (
                    <article key={artifact.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {artifact.artifact_type}
                      </div>
                      {artifact.title && (
                        <h3 className="mt-2 text-sm font-semibold text-slate-900">{artifact.title}</h3>
                      )}
                      {artifact.content && (
                        <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">
                          {artifact.content}
                        </p>
                      )}
                      {links.length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {links.map(link => (
                            <Link key={`${artifact.id}-${link.to}`} to={link.to} className="btn btn-secondary">
                              {link.label}
                            </Link>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  )
                })
              )}
            </div>
          </section>
        </aside>
      </div>
    </main>
  )
}

function SessionStateSummary({ state }: { state: AgentSessionState }) {
  return (
    <>
      {state.summary ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</div>
          <p className="mt-2 text-sm leading-6 text-slate-700">{state.summary}</p>
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <StateField label="Goal" value={state.goal} />
        <StateField label="Current Focus" value={state.current_focus} />
        <StateField label="Next Question" value={state.next_question} />
        <StateField label="Next Action" value={state.next_action} />
      </div>

      <StateListField label="Constraints" items={state.constraints} />
      <StateListField label="Preferences" items={state.preferences} />
      <StateListField label="Working Memory" items={state.working_memory} />
    </>
  )
}

function StateField({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{value || 'Not set'}</p>
    </div>
  )
}

function StateListField({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      {items.length === 0 ? (
        <p className="mt-2 text-sm leading-6 text-slate-500">No items yet.</p>
      ) : (
        <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
          {items.map(item => (
            <li key={`${label}-${item}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ReflectionCard({
  reflection,
  variant,
}: {
  reflection: AgentReflection
  variant: 'recalled' | 'saved'
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {variant === 'recalled' ? 'Reflection Recall' : reflection.reflection_type}
        </span>
        <span className="text-xs text-slate-500">Score {formatScore(reflection.score)}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{reflection.summary}</p>
      {reflection.action_item ? (
        <p className="mt-2 text-sm leading-6 text-slate-600">Action: {reflection.action_item}</p>
      ) : null}
    </article>
  )
}

export default AgentWorkspacePage
