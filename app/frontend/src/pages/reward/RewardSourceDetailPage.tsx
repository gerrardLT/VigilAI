import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DomainHeader from '../../components/app/DomainHeader'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { rewardOpportunityApi } from '../../services/rewardOpportunityApi'
import { rewardPaths } from '../../routes/domainPaths'
import type { RewardSourceDetailResponse } from '../../types'

const navLinks = [
  { path: rewardPaths.overview, label: '总览' },
  { path: rewardPaths.opportunities, label: '机会库' },
  { path: rewardPaths.operations, label: '运行面板' },
]

export default function RewardSourceDetailPage() {
  const { id = '' } = useParams()
  const [detail, setDetail] = useState<RewardSourceDetailResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: '',
    source_type: '',
    source_platform: '',
    entry_url: '',
    merge_group_key: '',
    preferred_entry_url: '',
    auto_sync_enabled: true,
    sync_interval_minutes: 30,
  })

  async function loadDetail() {
    setLoading(true)
    setError(null)
    try {
      const response = await rewardOpportunityApi.getSourceDetail(id)
      setDetail(response)
      setForm({
        name: response.name,
        source_type: response.source_type,
        source_platform: response.source_platform || '',
        entry_url: response.entry_url || '',
        merge_group_key: response.merge_group_key || '',
        preferred_entry_url: response.preferred_entry_url || '',
        auto_sync_enabled: response.schedule?.auto_sync_enabled ?? true,
        sync_interval_minutes: response.schedule?.sync_interval_minutes ?? 30,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载来源详情失败')
      setDetail(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDetail()
  }, [id])

  async function saveBase() {
    setSaving(true)
    setError(null)
    try {
      await rewardOpportunityApi.updateSource(id, {
        name: form.name,
        source_type: form.source_type,
        source_platform: form.source_platform || null,
        entry_url: form.entry_url || null,
        merge_group_key: form.merge_group_key || null,
        preferred_entry_url: form.preferred_entry_url || null,
      })
      await rewardOpportunityApi.updateSourceSchedule(id, {
        auto_sync_enabled: form.auto_sync_enabled,
        sync_interval_minutes: form.sync_interval_minutes,
      })
      await loadDetail()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存来源详情失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !detail) {
    return <Loading text="加载来源详情中..." />
  }

  if (error && !detail) {
    return <ErrorMessage message={error} onRetry={() => void loadDetail()} />
  }

  if (!detail) {
    return <ErrorMessage message="来源不存在" onRetry={() => void loadDetail()} />
  }

  return (
    <main className="space-y-6" data-testid="reward-source-detail-page">
      <DomainHeader brandLabel="奖励活动 Agent" brandTo={rewardPaths.overview} navLinks={navLinks} />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">{detail.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{detail.entry_url || '未配置入口 URL'}</p>
          </div>
          <Link to={rewardPaths.operations} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">
            返回运行面板
          </Link>
        </div>
      </section>

      {error ? <ErrorMessage message={error} onRetry={() => void loadDetail()} /> : null}

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">基础信息</h3>
          <div className="mt-4 grid gap-4">
            <input value={form.name} onChange={event => setForm(current => ({ ...current, name: event.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={form.source_type} onChange={event => setForm(current => ({ ...current, source_type: event.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={form.source_platform} onChange={event => setForm(current => ({ ...current, source_platform: event.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={form.entry_url} onChange={event => setForm(current => ({ ...current, entry_url: event.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={form.merge_group_key} onChange={event => setForm(current => ({ ...current, merge_group_key: event.target.value }))} placeholder="merge group key" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={form.preferred_entry_url} onChange={event => setForm(current => ({ ...current, preferred_entry_url: event.target.value }))} placeholder="preferred entry url" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">调度配置</h3>
          <div className="mt-4 grid gap-4">
            <label className="flex items-center gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.auto_sync_enabled}
                onChange={event => setForm(current => ({ ...current, auto_sync_enabled: event.target.checked }))}
              />
              启用自动同步
            </label>
            <input
              type="number"
              min={5}
              value={form.sync_interval_minutes}
              onChange={event => setForm(current => ({ ...current, sync_interval_minutes: Number(event.target.value) || 30 }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="text-xs text-slate-500">
              当前状态：{detail.status} / {detail.is_paused ? '已停用' : '运行中'} / {detail.schedule?.auto_sync_enabled ? `每 ${detail.schedule.sync_interval_minutes} 分钟` : '自动同步关闭'}
            </div>
            <button
              type="button"
              onClick={() => void saveBase()}
              disabled={saving}
              className="inline-flex w-fit rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {saving ? '保存中...' : '保存来源配置'}
            </button>
          </div>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">健康趋势</h3>
          <div className="mt-4 space-y-2">
            {(detail.health_trend ?? []).length === 0 ? (
              <p className="text-sm text-slate-500">暂无任务趋势。</p>
            ) : (
              detail.health_trend?.map(point => (
                <div key={point.job_id} className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 text-sm">
                  <span className="text-slate-600">{point.created_at}</span>
                  <span className="text-slate-900">
                    {point.status} / 文档 {point.document_count} / 候选 {point.candidate_count} / 机会 {point.opportunity_count}
                  </span>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">合并入口</h3>
          <div className="mt-4 space-y-2">
            {(detail.merged_sources ?? []).map(item => (
              <div key={item.id} className="rounded-lg bg-slate-50 px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{item.name}</div>
                <div className="text-slate-600">{item.entry_url}</div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">最近任务</h3>
          <div className="mt-4 space-y-2">
            {(detail.recent_jobs ?? []).map(job => (
              <div key={job.id} className="rounded-lg bg-slate-50 px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{job.id}</div>
                <div className="text-slate-600">{job.status}</div>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">审计记录</h3>
          <div className="mt-4 space-y-2">
            {(detail.audit ?? []).map(item => (
              <div key={item.id} className="rounded-lg bg-slate-50 px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{item.action_type}</div>
                <div className="text-slate-600">{item.created_at}</div>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  )
}
