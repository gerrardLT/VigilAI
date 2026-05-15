import { Link } from 'react-router-dom'
import DomainHeader from '../../components/app/DomainHeader'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { useRewardOpportunities } from '../../hooks/useRewardOpportunities'
import { rewardPaths } from '../../routes/domainPaths'

const navLinks = [
  { path: rewardPaths.overview, label: '总览' },
  { path: rewardPaths.opportunities, label: '机会库' },
  { path: rewardPaths.operations, label: '运行面板' },
]

export default function RewardOpportunitiesPage() {
  const { items, total, filters, setFilters, loading, error, reload } = useRewardOpportunities()

  if (loading && items.length === 0) {
    return <Loading text="加载奖励活动机会库中..." />
  }

  if (error && items.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void reload()} />
  }

  return (
    <main className="space-y-6" data-testid="reward-opportunities-page">
      <DomainHeader brandLabel="奖励活动 Agent" brandTo={rewardPaths.overview} navLinks={navLinks} />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">奖励活动机会库</h2>
            <p className="mt-1 text-sm text-slate-600">结构化机会池共 {total} 条。</p>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="text-sm text-slate-600">
            分类
            <select
              value={filters.classification}
              onChange={event => setFilters(current => ({ ...current, classification: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">全部</option>
              <option value="高价值">高价值</option>
              <option value="可跟">可跟</option>
              <option value="待补证据">待补证据</option>
              <option value="低价值">低价值</option>
              <option value="拒绝">拒绝</option>
            </select>
          </label>
          <label className="text-sm text-slate-600">
            证据状态
            <select
              value={filters.evidence_status}
              onChange={event => setFilters(current => ({ ...current, evidence_status: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">全部</option>
              <option value="complete">证据完整</option>
              <option value="missing">证据缺失</option>
            </select>
          </label>
          <label className="text-sm text-slate-600">
            来源平台
            <input
              value={filters.source_platform}
              onChange={event => setFilters(current => ({ ...current, source_platform: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="例如：twitter、web、github"
            />
          </label>
          <label className="text-sm text-slate-600">
            排序方式
            <select
              value={filters.sort_by}
              onChange={event => setFilters(current => ({ ...current, sort_by: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="created_at">最新入库</option>
              <option value="published_at">发布时间</option>
              <option value="last_evaluated_at">最近评估</option>
            </select>
          </label>
        </div>
      </section>

      <section className="space-y-4">
        {items.length === 0 ? (
          <article className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
            暂无奖励活动机会。
          </article>
        ) : (
          items.map(item => (
            <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
                      {item.ai_stage_2_label}
                    </span>
                    <span className="text-xs text-slate-500">置信度 {Math.round(item.ai_confidence * 100)}%</span>
                  </div>
                  <h3 className="text-xl font-semibold text-slate-900">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.ai_summary || item.raw_text_excerpt || '暂无摘要。'}</p>
                  <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                    <span>{item.source_platform}</span>
                    <span>{item.reward_value_text || '奖励待补充'}</span>
                    <span>{item.action_required || '动作待补充'}</span>
                  </div>
                </div>
                <Link
                  to={rewardPaths.opportunityDetail(item.id)}
                  className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:border-emerald-400 hover:text-emerald-700"
                >
                  查看详情
                </Link>
              </div>
            </article>
          ))
        )}
      </section>
    </main>
  )
}
