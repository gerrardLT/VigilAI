import { Link } from 'react-router-dom'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { useRewardOpportunities } from '../../hooks/useRewardOpportunities'

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`
}

export function RewardOpportunitiesPage() {
  const { items, loading, error, reload } = useRewardOpportunities()

  if (loading && items.length === 0) {
    return <Loading text="正在加载奖励机会..." />
  }

  if (error && items.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void reload()} />
  }

  return (
    <main className="space-y-6" data-testid="reward-opportunities-page">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-slate-900">奖励机会池</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          聚合浏览邀请奖励、注册奖励、任务奖励等候选项，并优先查看高置信度条目。
        </p>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead>
              <tr className="text-left text-sm text-slate-500">
                <th className="pb-3">标题</th>
                <th className="pb-3">平台</th>
                <th className="pb-3">标签</th>
                <th className="pb-3">置信度</th>
                <th className="pb-3">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-slate-500">
                    还没有奖励机会。
                  </td>
                </tr>
              ) : (
                items.map(item => (
                  <tr key={item.id} className="text-sm text-slate-700">
                    <td className="py-4 pr-4 font-medium text-slate-900">{item.title}</td>
                    <td className="py-4 pr-4">{item.source_platform}</td>
                    <td className="py-4 pr-4">{item.ai_stage_2_label}</td>
                    <td className="py-4 pr-4">{formatConfidence(item.ai_confidence)}</td>
                    <td className="py-4">
                      <Link to={`/rewards/opportunities/${item.id}`} className="text-primary-700 hover:text-primary-800">
                        查看详情
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}

export default RewardOpportunitiesPage
