import { Link, useParams } from 'react-router-dom'
import DomainHeader from '../../components/app/DomainHeader'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { useRewardOpportunityDetail } from '../../hooks/useRewardOpportunityDetail'
import { rewardPaths } from '../../routes/domainPaths'

const navLinks = [
  { path: rewardPaths.overview, label: '总览' },
  { path: rewardPaths.opportunities, label: '机会库' },
  { path: rewardPaths.operations, label: '运行面板' },
]

export default function RewardOpportunityDetailPage() {
  const { id = '' } = useParams()
  const { item, loading, error, reload } = useRewardOpportunityDetail(id)

  if (loading && !item) {
    return <Loading text="加载奖励活动详情中..." />
  }

  if (error && !item) {
    return <ErrorMessage message={error} onRetry={() => void reload()} />
  }

  if (!item) {
    return null
  }

  return (
    <main className="space-y-6" data-testid="reward-opportunity-detail-page">
      <DomainHeader brandLabel="奖励活动 Agent" brandTo={rewardPaths.overview} navLinks={navLinks} />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <Link to={rewardPaths.opportunities} className="text-sm font-medium text-emerald-700">
          返回机会库
        </Link>
        <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">{item.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{item.ai_summary || item.raw_text_excerpt || '暂无摘要。'}</p>
          </div>
          <div className="rounded-xl bg-slate-50 px-4 py-3 text-right">
            <div className="text-xs text-slate-500">分类结果</div>
            <div className="mt-1 text-lg font-semibold text-slate-900">{item.ai_stage_2_label}</div>
            <div className="text-xs text-slate-500">置信度 {Math.round(item.ai_confidence * 100)}%</div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">结构化判断</h3>
          <dl className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase text-slate-500">奖励</dt>
              <dd className="mt-1 text-sm text-slate-900">{item.reward_value_text || item.reward_type || '未知'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">动作</dt>
              <dd className="mt-1 text-sm text-slate-900">{item.action_required || '缺失'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">时间</dt>
              <dd className="mt-1 text-sm text-slate-900">{item.deadline_text || '缺失'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">资格</dt>
              <dd className="mt-1 text-sm text-slate-900">{item.eligibility || '缺失'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">召回原因</dt>
              <dd className="mt-1 text-sm text-slate-900">{item.ai_stage_1_recall_reason || '未知'}</dd>
            </div>
          </dl>

          <div className="mt-6">
            <h4 className="text-sm font-semibold text-slate-900">证据</h4>
            <div className="mt-3 space-y-3">
              {(item.evidence ?? []).length === 0 ? (
                <p className="text-sm text-slate-500">暂无已落库证据。</p>
              ) : (
                item.evidence?.map(evidence => (
                  <div key={evidence.id} className="rounded-lg bg-slate-50 px-4 py-3">
                    <div className="text-xs uppercase text-slate-500">{evidence.evidence_type}</div>
                    <div className="mt-1 text-sm text-slate-900">{evidence.snippet}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </article>

        <article className="space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">风险标记</h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {(item.ai_risk_flags ?? []).length === 0 ? (
                <span className="text-sm text-slate-500">暂无风险标记。</span>
              ) : (
                item.ai_risk_flags?.map(flag => (
                  <span key={flag} className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                    {flag}
                  </span>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">缺失证据</h3>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              {(item.ai_missing_evidence ?? []).length === 0 ? (
                <li className="text-slate-500">无缺失证据。</li>
              ) : (
                item.ai_missing_evidence?.map(value => <li key={value}>{value}</li>)
              )}
            </ul>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">来源链接</h3>
            <a
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 block break-all text-sm text-emerald-700"
            >
              {item.source_url}
            </a>
            {(item.external_links ?? []).length > 0 ? (
              <div className="mt-4 space-y-2">
                {item.external_links?.slice(0, 6).map(link => (
                  <a key={link} href={link} target="_blank" rel="noreferrer" className="block break-all text-sm text-slate-600">
                    {link}
                  </a>
                ))}
              </div>
            ) : null}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">调查轨迹</h3>
            <div className="mt-4 space-y-3">
              {(item.investigation?.actions ?? []).length === 0 ? (
                <p className="text-sm text-slate-500">暂无后续调查动作。</p>
              ) : (
                item.investigation?.actions.map(action => (
                  <div key={action.id} className="rounded-lg bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-slate-900">{action.action_type}</span>
                      <span className="text-xs text-slate-500">{action.status}</span>
                    </div>
                    {action.target_url ? (
                      <a href={action.target_url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-xs text-emerald-700">
                        {action.target_url}
                      </a>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">补充文档</h3>
            <div className="mt-4 space-y-3">
              {(item.follow_up_documents ?? []).length === 0 ? (
                <p className="text-sm text-slate-500">暂无补充文档。</p>
              ) : (
                item.follow_up_documents?.map(document => (
                  <div key={document.id} className="rounded-lg bg-slate-50 px-4 py-3">
                    <div className="text-sm font-medium text-slate-900">{document.title}</div>
                    <a href={document.source_url} target="_blank" rel="noreferrer" className="mt-1 block break-all text-xs text-emerald-700">
                      {document.source_url}
                    </a>
                    {document.summary ? <div className="mt-2 text-sm text-slate-600">{document.summary}</div> : null}
                  </div>
                ))
              )}
            </div>
          </section>
        </article>
      </section>
    </main>
  )
}
