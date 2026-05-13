import { Link } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { useRewardOpportunities } from '../../hooks/useRewardOpportunities'

export function RewardWorkspacePage() {
  const { overview, items, operations, loading, error, reload } = useRewardOpportunities()

  if (loading && !overview) {
    return <Loading text="正在加载奖励工作台..." />
  }

  if (error && !overview) {
    return <ErrorMessage message={error} onRetry={() => void reload()} />
  }

  return (
    <main className="space-y-6" data-testid="reward-workspace-page">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
              Reward Agent
            </span>
            <h1 className="mt-3 text-3xl font-bold text-slate-900">奖励工作台</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              统一查看奖励线索来源、候选机会数量，以及最近待跟进的高价值条目。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/rewards/opportunities" className="btn btn-primary">
              打开奖励池
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        {[
          { label: '来源数', value: overview?.source_count ?? 0 },
          { label: '机会数', value: overview?.opportunity_count ?? 0 },
          { label: '候选数', value: overview?.candidate_count ?? 0 },
          { label: '高价值', value: overview?.high_value_count ?? 0 },
        ].map(card => (
          <article key={card.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-sm text-slate-500">{card.label}</div>
            <div className="mt-3 text-3xl font-semibold text-slate-900">{card.value}</div>
          </article>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-slate-900">最近机会</h2>
            <Link to="/rewards/opportunities" className="text-sm font-medium text-primary-700">
              查看全部
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {items.length === 0 ? (
              <p className="text-sm text-slate-500">还没有奖励机会。</p>
            ) : (
              items.slice(0, 5).map(item => (
                <Link
                  key={item.id}
                  to={`/rewards/opportunities/${item.id}`}
                  className="block rounded-2xl border border-slate-200 px-4 py-4 hover:border-primary-300 hover:bg-primary-50"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="mt-1 text-sm text-slate-500">{item.source_platform}</div>
                    </div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                      {item.ai_stage_2_label}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">运行概况</h2>
          <dl className="mt-4 space-y-4 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-500">来源任务</dt>
              <dd className="font-medium text-slate-900">{operations?.sources.length ?? 0}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-500">最近作业</dt>
              <dd className="font-medium text-slate-900">{operations?.recent_jobs.length ?? 0}</dd>
            </div>
          </dl>
        </article>
      </section>
    </main>
  )
}

export default RewardWorkspacePage
