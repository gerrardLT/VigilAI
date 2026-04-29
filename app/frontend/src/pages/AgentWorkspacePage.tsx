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
    label: '机会研判',
    summary: '搜索、解释并规划 grant、bounty 等机会的后续动作。',
  },
  {
    value: 'product_selection',
    label: '商品选品',
    summary: '研究淘宝和闲鱼的商品机会，生成候选清单并进行平台对比。',
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
    badge: '机会工具集',
    description: '在机会域中使用共享智能助手，完成搜索、解释与下一步行动建议。',
    inputLabel: '机会输入',
    placeholder: '例如：帮我找本月适合个人参与、奖励明确的 grant',
    emptyState: '还没有对话，发送一条消息开始本次智能会话。',
    helper: '当前模式会调用 `/api/agent/*` 背后的机会工具。',
  },
  product_selection: {
    badge: '选品工具集',
    description: '在商品选品域中使用同一套共享会话，完成候选清单与对比分析。',
    inputLabel: '选品输入',
    placeholder: '例如：对比淘宝和闲鱼上的宠物饮水机机会',
    emptyState: '还没有对话，你可以随时切换领域开始新的会话。',
    helper: '当前模式会调用 `/api/agent/*` 背后的选品工具。',
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
      label: '打开候选清单',
      to: `/selection/opportunities?query_id=${encodeURIComponent(jobId)}`,
    })
  } else if ((payload.shortlist || []).length > 0) {
    links.push({ label: '打开选品池', to: '/selection/opportunities' })
  }

  if (compareIds.length >= 2) {
    const query = compareIds.map(id => `ids=${encodeURIComponent(id)}`).join('&')
    links.push({
      label: '打开对比视图',
      to: `/selection/compare?${query}`,
    })
  }

  return links
}

export function AgentWorkspacePage() {
  const [domainType, setDomainType] = useState<AgentDomainType>('opportunity')
  const [draft, setDraft] = useState('')
  const { session, sessions, turns, artifacts, loading, sending, error, restoreSession, sendTurn } =
    useAgentSession(domainType)
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
              <h1 className="text-3xl font-bold text-slate-900">智能助手工作台</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{copy.description}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <div>当前领域：{domainType === 'opportunity' ? '机会研判' : '商品选品'}</div>
            <div>会话：{session?.id ?? '尚未创建'}</div>
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
              <h2 className="text-lg font-semibold text-slate-900">对话</h2>
              <p className="mt-1 text-sm text-slate-500">{copy.helper}</p>
            </div>
            {(loading || sending) && <span className="text-sm text-sky-700">处理中...</span>}
          </div>

          <div className="space-y-3" aria-live="polite">
            {turns.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                {copy.emptyState}
              </div>
            ) : (
              turns.map(turn => (
                <article key={turn.id} className={`rounded-2xl border px-4 py-4 ${getTurnTone(turn.role)}`}>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {turn.role === 'assistant' ? '助手' : '用户'}
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
              <p className="text-xs text-slate-500">切换领域会开启一段新的共享智能会话。</p>
              <button type="submit" className="btn btn-primary" disabled={sending || !draft.trim()}>
                {sending ? '发送中...' : '发送'}
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">历史会话</h2>
            <p className="mt-1 text-sm text-slate-500">恢复当前领域下最近的会话记录。</p>

            <div className="mt-4 space-y-3">
              {sessions.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  还没有已保存的会话。
                </div>
              ) : (
                sessions.map(item => {
                  const isActive = item.id === session?.id
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => void restoreSession(item.id)}
                      className={`block w-full rounded-2xl border px-4 py-4 text-left transition ${
                        isActive
                          ? 'border-sky-300 bg-sky-50 shadow-sm'
                          : 'border-slate-200 bg-slate-50 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-semibold text-slate-900">
                            {item.title || '未命名会话'}
                          </div>
                          <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                            {item.last_turn_preview || '还没有对话内容。'}
                          </div>
                        </div>
                        <div className="shrink-0 text-right text-xs text-slate-500">
                          <div>{item.turn_count} 条消息</div>
                          <div>{new Date(item.updated_at).toLocaleDateString()}</div>
                        </div>
                      </div>
                    </button>
                  )
                })
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">产出物</h2>
            <p className="mt-1 text-sm text-slate-500">
              共享智能会话会把中间结果沉淀为可复用的产出物。
            </p>

            <div className="mt-4 space-y-3">
              {artifacts.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  还没有产出物。
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
