import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDigests } from '../hooks/useDigests'
import { Loading } from '../components/Loading'
import { ErrorMessage } from '../components/ErrorMessage'
import { Toast } from '../components/Toast'
import { formatDateTime } from '../utils/formatDate'
import type { DigestDetail } from '../types'

function getDigestHighlights(content: string) {
  return content
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => line.replace(/^[-*•]\s*/, ''))
    .slice(0, 3)
}

function buildDigestClipboardText(digest: DigestDetail) {
  const highlights = getDigestHighlights(digest.content)

  return [
    `${digest.title} (${digest.digest_date})`,
    digest.summary || '',
    highlights.length > 0 ? `重点：${highlights.join('；')}` : '',
    '',
    digest.content,
  ]
    .filter(Boolean)
    .join('\n')
}

export function DigestsPage() {
  const {
    digests,
    candidates,
    loading,
    error,
    refetch,
    getDigest,
    generateDigest,
    sendDigest,
    removeDigestCandidate,
  } = useDigests()
  const [selectedDigest, setSelectedDigest] = useState<DigestDetail | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [actionLoading, setActionLoading] = useState<'generate' | 'send' | 'copy' | string | null>(null)

  const digestToDisplay = useMemo(() => selectedDigest || digests[0] || null, [selectedDigest, digests])
  const digestDate = digestToDisplay?.digest_date || new Date().toISOString().slice(0, 10)
  const digestHighlights = useMemo(
    () => (digestToDisplay ? getDigestHighlights(digestToDisplay.content) : []),
    [digestToDisplay]
  )

  async function handleGenerate() {
    setActionLoading('generate')
    const digest = await generateDigest({ digest_date: new Date().toISOString().slice(0, 10) })
    setActionLoading(null)

    if (digest) {
      setSelectedDigest(digest)
      setToast({ type: 'success', message: '已生成今日日报' })
    } else {
      setToast({ type: 'error', message: '生成日报失败' })
    }
  }

  async function handleSelectDigest(digestId: string) {
    setActionLoading(digestId)
    const digest = await getDigest(digestId)
    setActionLoading(null)

    if (digest) {
      setSelectedDigest(digest)
    } else {
      setToast({ type: 'error', message: '加载日报详情失败' })
    }
  }

  async function handleSendDigest() {
    if (!digestToDisplay) {
      return
    }

    setActionLoading('send')
    const digest = await sendDigest(digestToDisplay.id, { send_channel: 'manual' })
    setActionLoading(null)

    if (digest) {
      setSelectedDigest(digest)
      setToast({ type: 'success', message: '日报已标记为已发送' })
    } else {
      setToast({ type: 'error', message: '发送日报失败' })
    }
  }

  async function handleCopyDigest() {
    if (!digestToDisplay) {
      return
    }

    const clipboard = window.navigator?.clipboard
    if (!clipboard?.writeText) {
      setToast({ type: 'error', message: '当前环境不支持复制摘要' })
      return
    }

    setActionLoading('copy')

    try {
      await clipboard.writeText(buildDigestClipboardText(digestToDisplay))
      setToast({ type: 'success', message: '日报摘要已复制' })
    } catch {
      setToast({ type: 'error', message: '复制摘要失败' })
    } finally {
      setActionLoading(null)
    }
  }

  async function handleRemoveCandidate(activityId: string) {
    setActionLoading(`candidate-${activityId}`)
    const success = await removeDigestCandidate(activityId, { digest_date: digestDate })
    setActionLoading(null)

    if (success) {
      setToast({ type: 'success', message: '已从日报候选池移除' })
    } else {
      setToast({ type: 'error', message: '移除日报候选失败' })
    }
  }

  if (loading && digests.length === 0) {
    return <Loading text="加载日报..." />
  }

  if (error && digests.length === 0) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  return (
    <div className="space-y-6" data-testid="digests-page">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">日报</h1>
          <p className="mt-1 text-sm text-gray-500">
            用系统聚合出的重点摘要，快速同步今天最值得处理的机会。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            data-testid="generate-digest-button"
            onClick={handleGenerate}
            disabled={actionLoading === 'generate'}
            className="btn btn-primary"
          >
            生成今日日报
          </button>
          <Link to="/workspace" className="btn btn-secondary">
            返回工作台
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[360px_1fr]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-amber-100 bg-amber-50/70 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-medium text-amber-900">今日日报候选</div>
                <div className="mt-1 text-xs text-amber-700">
                  先把值得写进日报的机会收进候选池，再生成正式摘要。
                </div>
              </div>
              <div className="rounded-full bg-white px-3 py-1 text-xs font-medium text-amber-800">
                {candidates.length} 条
              </div>
            </div>

            {candidates.length === 0 ? (
              <div className="rounded-xl border border-dashed border-amber-200 bg-white/70 p-4 text-sm text-amber-900/80">
                还没有候选机会，可以从详情页把重点机会加入今日日报。
              </div>
            ) : (
              <div className="space-y-3">
                {candidates.map(candidate => (
                  <div
                    key={candidate.id}
                    data-testid={`digest-candidate-${candidate.id}`}
                    className="rounded-xl border border-white/70 bg-white/90 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="font-medium text-gray-900">{candidate.title}</div>
                        <div className="text-xs text-gray-500">{candidate.source_name}</div>
                        <div className="text-sm text-gray-600">
                          {candidate.summary || candidate.description || '暂无摘要'}
                        </div>
                      </div>
                      <button
                        type="button"
                        data-testid={`digest-candidate-remove-${candidate.id}`}
                        onClick={() => {
                          void handleRemoveCandidate(candidate.id)
                        }}
                        disabled={actionLoading === `candidate-${candidate.id}`}
                        className="btn btn-secondary whitespace-nowrap"
                      >
                        移除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-4">
            <div className="mb-3 text-sm font-medium text-gray-500">历史日报</div>
            {digests.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 p-6 text-sm text-gray-500">
                暂无日报，先生成今天的摘要。
              </div>
            ) : (
              <div className="space-y-3">
                {digests.map(digest => (
                  <button
                    key={digest.id}
                    data-testid={`digest-row-${digest.id}`}
                    onClick={() => handleSelectDigest(digest.id)}
                    className={`w-full rounded-xl border p-4 text-left transition-all ${
                      digestToDisplay?.id === digest.id
                        ? 'border-primary-200 bg-primary-50'
                        : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-gray-900">{digest.title}</div>
                        <div className="mt-1 text-xs text-gray-500">{digest.digest_date}</div>
                      </div>
                      <div className="text-xs uppercase tracking-wide text-gray-500">{digest.status}</div>
                    </div>
                    {digest.summary && (
                      <p className="mt-3 text-sm text-gray-600 line-clamp-2">{digest.summary}</p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>

        <section className="rounded-2xl bg-white shadow-sm border border-gray-100 p-6">
          {digestToDisplay ? (
            <div className="space-y-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="text-sm text-gray-500">{digestToDisplay.digest_date}</div>
                  <h2 className="text-2xl font-semibold text-gray-900">{digestToDisplay.title}</h2>
                  {digestToDisplay.summary && (
                    <p className="mt-2 text-sm text-gray-600">{digestToDisplay.summary}</p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    data-testid="digest-copy-button"
                    onClick={() => {
                      void handleCopyDigest()
                    }}
                    disabled={actionLoading === 'copy'}
                    className="btn btn-secondary"
                  >
                    复制摘要
                  </button>
                  <button
                    onClick={handleSendDigest}
                    disabled={actionLoading === 'send'}
                    className="btn btn-secondary"
                  >
                    标记为已发送
                  </button>
                </div>
              </div>

              <div className="rounded-2xl border border-sky-100 bg-sky-50/80 p-5">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-sky-600">1 Minute Brief</div>
                    <div className="mt-2 text-base font-semibold text-slate-900">
                      {digestToDisplay.summary || '先看三条重点，再决定今天的处理顺序。'}
                    </div>
                  </div>
                  <Link to="/tracking" className="text-sm text-primary-700 hover:text-primary-800">
                    去跟进列表
                  </Link>
                </div>
                <ul className="mt-4 space-y-2 text-sm text-slate-700" data-testid="digest-brief-list">
                  {digestHighlights.length > 0 ? (
                    digestHighlights.map((highlight, index) => (
                      <li key={`${digestToDisplay.id}-${index}`} className="rounded-xl bg-white/80 px-3 py-2">
                        {highlight}
                      </li>
                    ))
                  ) : (
                    <li className="rounded-xl bg-white/80 px-3 py-2">当前日报还没有提炼出重点摘要。</li>
                  )}
                </ul>
                <div className="mt-4 text-xs text-slate-600">
                  {digestToDisplay.status === 'sent'
                    ? '这份日报已经发送，可以作为今天的归档记录。'
                    : '这份日报还未发送，适合复核后作为今天的共享摘要。'}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-gray-500">包含机会</div>
                  <div className="mt-2 text-2xl font-semibold text-gray-900">{digestToDisplay.item_ids.length}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-gray-500">状态</div>
                  <div className="mt-2 text-2xl font-semibold text-gray-900">{digestToDisplay.status}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-gray-500">更新时间</div>
                  <div className="mt-2 text-sm font-medium text-gray-900">
                    {formatDateTime(digestToDisplay.updated_at)}
                  </div>
                </div>
              </div>

              <div className="rounded-xl bg-slate-950 text-slate-100 p-5 whitespace-pre-wrap leading-7">
                {digestToDisplay.content}
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                <div>创建时间：{formatDateTime(digestToDisplay.created_at)}</div>
                <div>
                  发送时间：
                  {digestToDisplay.last_sent_at ? formatDateTime(digestToDisplay.last_sent_at) : ' 未发送'}
                </div>
                <div>渠道：{digestToDisplay.send_channel || 'manual'}</div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-200 p-10 text-center text-sm text-gray-500">
              选择一份日报查看详情，或者直接生成今天的摘要。
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default DigestsPage
