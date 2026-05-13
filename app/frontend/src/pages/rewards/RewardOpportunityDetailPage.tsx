import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { rewardOpportunityApi } from '../../services/rewardOpportunityApi'
import type { RewardOpportunityItem } from '../../types'

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`
}

export function RewardOpportunityDetailPage() {
  const { id = '' } = useParams()
  const [item, setItem] = useState<RewardOpportunityItem | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function loadDetail() {
      setLoading(true)
      setError(null)
      try {
        const response = await rewardOpportunityApi.getOpportunity(id)
        if (active) {
          setItem(response)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : '加载奖励机会详情失败')
          setItem(null)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }
    void loadDetail()
    return () => {
      active = false
    }
  }, [id])

  if (loading && !item) {
    return <Loading text="正在加载奖励机会详情..." />
  }

  if (error && !item) {
    return <ErrorMessage message={error} />
  }

  if (!item) {
    return null
  }

  return (
    <main className="space-y-6" data-testid="reward-opportunity-detail-page">
      <Link to="/rewards/opportunities" className="inline-flex text-sm font-medium text-primary-700">
        返回奖励池
      </Link>

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">{item.title}</h1>
            <p className="mt-2 text-sm text-slate-500">{item.source_platform}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
            <div className="text-slate-500">置信度</div>
            <div className="mt-1 font-semibold text-slate-900">{formatConfidence(item.ai_confidence)}</div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">AI 结论</h2>
          <dl className="mt-4 space-y-4 text-sm">
            <div>
              <dt className="text-slate-500">阶段标签</dt>
              <dd className="mt-1 text-slate-900">{item.ai_stage_2_label}</dd>
            </div>
            <div>
              <dt className="text-slate-500">奖励类型</dt>
              <dd className="mt-1 text-slate-900">{item.reward_type || '暂无'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">奖励值</dt>
              <dd className="mt-1 text-slate-900">{item.reward_value_text || '暂无'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">所需动作</dt>
              <dd className="mt-1 text-slate-900">{item.action_required || '暂无'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">摘要</dt>
              <dd className="mt-1 whitespace-pre-wrap text-slate-900">{item.ai_summary || '暂无'}</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">来源</h2>
          <a
            href={item.source_url}
            target="_blank"
            rel="noreferrer"
            className="mt-4 block break-all text-sm text-primary-700 hover:text-primary-800"
          >
            {item.source_url}
          </a>
        </article>
      </section>
    </main>
  )
}

export default RewardOpportunityDetailPage
