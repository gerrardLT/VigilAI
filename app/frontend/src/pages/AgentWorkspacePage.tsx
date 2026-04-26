import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { useAgentSession } from '../hooks/useAgentSession'
import type { AgentArtifact, AgentDomainType } from '../types'

function getTurnTone(role: string) {
  if (role === 'assistant') {
    return 'border-sky-100 bg-sky-50/70'
  }
  return 'border-slate-200 bg-white'
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
  const [draft, setDraft] = useState('')
  const { session, turns, artifacts, loading, sending, error, sendTurn } = useAgentSession(domainType)
  const copy = DOMAIN_COPY[domainType]

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nextMessage = draft.trim()
    if (!nextMessage) {
      return
    }

    try {
      await sendTurn(nextMessage)
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
            <div>Session: {session?.id ?? 'Not created yet'}</div>
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
      </section>

      {error && <ErrorMessage message={error} />}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Conversation</h2>
              <p className="mt-1 text-sm text-slate-500">{copy.helper}</p>
            </div>
            {(loading || sending) && <span className="text-sm text-sky-700">Working...</span>}
          </div>

          <div className="space-y-3" aria-live="polite">
            {turns.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                {copy.emptyState}
              </div>
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
              <button type="submit" className="btn btn-primary" disabled={sending || !draft.trim()}>
                {sending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-6">
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

export default AgentWorkspacePage
