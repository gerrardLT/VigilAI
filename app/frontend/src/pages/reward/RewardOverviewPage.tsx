import { Link } from 'react-router-dom'
import DomainHeader from '../../components/app/DomainHeader'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { useRewardOverview } from '../../hooks/useRewardOverview'
import { rewardPaths } from '../../routes/domainPaths'

const navLinks = [
  { path: rewardPaths.overview, label: '总览' },
  { path: rewardPaths.opportunities, label: '机会库' },
  { path: rewardPaths.operations, label: '运行面板' },
]

export default function RewardOverviewPage() {
  const { overview, loading, error, reload } = useRewardOverview()

  if (loading && !overview) {
    return <Loading text="加载奖励活动总览中..." />
  }

  if (error && !overview) {
    return <ErrorMessage message={error} onRetry={() => void reload()} />
  }

  const cards = [
    { label: '来源数', value: overview?.source_count ?? 0 },
    { label: '机会数', value: overview?.opportunity_count ?? 0 },
    { label: '召回候选', value: overview?.candidate_count ?? 0 },
    { label: '高价值', value: overview?.high_value_count ?? 0 },
    { label: '暂停来源', value: overview?.paused_source_count ?? 0 },
    { label: '待处理来源', value: overview?.needs_attention_source_count ?? 0 },
    { label: '今日抓取', value: overview?.today_crawled_count ?? 0 },
    { label: '今日深筛', value: overview?.today_deep_screened_count ?? 0 },
  ]

  return (
    <main className="space-y-6" data-testid="reward-overview-page">
      <DomainHeader brandLabel="奖励活动 Agent" brandTo={rewardPaths.overview} navLinks={navLinks} />

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">奖励活动发现系统</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">围绕全网奖励活动执行抓取、召回、调查补证和结构化沉淀。</p>
          </div>
          <div className="flex gap-3">
            <Link to={rewardPaths.opportunities} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
              打开机会库
            </Link>
            <Link to={rewardPaths.operations} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">
              打开运行面板
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map(card => (
          <article key={card.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-sm text-slate-500">{card.label}</div>
            <div className="mt-2 text-3xl font-semibold text-slate-900">{card.value}</div>
          </article>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">失败分类分布</h3>
          <div className="mt-4 space-y-3">
            {Object.entries(overview?.failure_category_counts ?? {}).length === 0 ? (
              <p className="text-sm text-slate-500">暂无失败分类统计。</p>
            ) : (
              Object.entries(overview?.failure_category_counts ?? {}).map(([label, count]) => (
                <div key={label} className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 text-sm">
                  <span className="text-slate-600">{label}</span>
                  <span className="font-medium text-slate-900">{count}</span>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">建议动作分布</h3>
          <div className="mt-4 space-y-3">
            {Object.entries(overview?.recommended_action_counts ?? {}).length === 0 ? (
              <p className="text-sm text-slate-500">暂无建议动作。</p>
            ) : (
              Object.entries(overview?.recommended_action_counts ?? {}).map(([label, count]) => (
                <div key={label} className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 text-sm">
                  <span className="text-slate-600">{label}</span>
                  <span className="font-medium text-slate-900">{count}</span>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">来源健康分布</h3>
          <div className="mt-4 space-y-3">
            {Object.entries(overview?.source_health_trend_summary ?? {}).length === 0 ? (
              <p className="text-sm text-slate-500">暂无来源健康统计。</p>
            ) : (
              Object.entries(overview?.source_health_trend_summary ?? {}).map(([label, count]) => (
                <div key={label} className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 text-sm">
                  <span className="text-slate-600">{label}</span>
                  <span className="font-medium text-slate-900">{count}</span>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">最近高价值机会</h3>
          <div className="mt-4 space-y-3">
            {(overview?.recent_high_value ?? []).length === 0 ? (
              <p className="text-sm text-slate-500">暂无高价值机会。</p>
            ) : (
              overview?.recent_high_value.map(item => (
                <Link
                  key={item.id}
                  to={rewardPaths.opportunityDetail(item.id)}
                  className="block rounded-lg border border-slate-200 px-4 py-3 hover:border-emerald-300 hover:bg-emerald-50"
                >
                  <div className="font-medium text-slate-900">{item.title}</div>
                  <div className="mt-1 text-xs text-slate-500">{item.source_platform}</div>
                </Link>
              ))
            )}
          </div>
        </article>
      </section>
    </main>
  )
}
