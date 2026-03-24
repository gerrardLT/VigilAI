import { useState } from 'react'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { SourceCard } from '../components/SourceCard'
import { Toast } from '../components/Toast'
import { useSources } from '../hooks/useSources'
import { api } from '../services/api'

export function SourcesPage() {
  const { sources, loading, error, refetch } = useSources()
  const [refreshing, setRefreshing] = useState<string | null>(null)
  const [refreshingAll, setRefreshingAll] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const handleRefreshSource = async (sourceId: string) => {
    setRefreshing(sourceId)
    try {
      const result = await api.refreshSource(sourceId)
      setToast({ type: 'success', message: result.message })
      await refetch()
    } catch (err) {
      const message = err instanceof Error ? err.message : '刷新失败'
      setToast({ type: 'error', message })
    } finally {
      setRefreshing(null)
    }
  }

  const handleRefreshAll = async () => {
    setRefreshingAll(true)
    try {
      const result = await api.refreshAllSources()
      setToast({ type: 'success', message: result.message })
      await refetch()
    } catch (err) {
      const message = err instanceof Error ? err.message : '刷新失败'
      setToast({ type: 'error', message })
    } finally {
      setRefreshingAll(false)
    }
  }

  if (loading) {
    return <Loading text="加载来源健康..." />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  const totalSources = sources.length
  const attentionSources = sources.filter(source => source.needs_attention)
  const healthySources = sources.filter(source => !source.needs_attention).length
  const totalActivities = sources.reduce((sum, source) => sum + source.activity_count, 0)
  const avgHealthScore =
    sources.length > 0
      ? Math.round(
          sources.reduce((sum, source) => sum + (source.health_score ?? 0), 0) / sources.length
        )
      : 0

  return (
    <div className="space-y-6">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">来源健康</h1>
          <p className="mt-2 text-sm text-gray-600">
            监控来源可用性、刷新时效和异常来源。
          </p>
        </div>

        <button
          type="button"
          data-testid="refresh-all-sources"
          onClick={handleRefreshAll}
          disabled={refreshingAll}
          className="btn btn-primary flex items-center gap-2"
        >
          {refreshingAll ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              <span>刷新中...</span>
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>刷新全部</span>
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="rounded-2xl bg-white p-5 shadow">
          <div className="text-2xl font-bold text-gray-900">{totalSources}</div>
          <div className="mt-1 text-sm text-gray-500">总来源数</div>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow">
          <div className="text-2xl font-bold text-emerald-600">{healthySources}</div>
          <div className="mt-1 text-sm text-gray-500">状态健康</div>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow">
          <div className="text-2xl font-bold text-rose-600">{attentionSources.length}</div>
          <div className="mt-1 text-sm text-gray-500">需要关注</div>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow">
          <div className="text-2xl font-bold text-sky-600">{avgHealthScore}</div>
          <div className="mt-1 text-sm text-gray-500">平均健康分</div>
        </div>
      </div>

      {attentionSources.length > 0 && (
        <section className="rounded-2xl border border-rose-100 bg-rose-50/70 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">需要关注的来源</h2>
              <p className="mt-1 text-sm text-gray-600">优先处理报错、长期未成功或刷新陈旧的来源。</p>
            </div>
            <div className="rounded-full bg-white px-3 py-1 text-sm font-medium text-rose-700 shadow-sm">
              {attentionSources.length} 个告警
            </div>
          </div>

          <div className="space-y-3">
            {attentionSources.map(source => (
              <div
                key={source.id}
                className="flex flex-col gap-3 rounded-xl border border-rose-100 bg-white p-4 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <div className="font-medium text-gray-900">{source.name}</div>
                  <div className="mt-1 text-sm text-gray-600">
                    健康分 {source.health_score ?? 0}
                    {source.error_message ? `，异常：${source.error_message}` : `，时效：${source.freshness_level || 'unknown'}`}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => void handleRefreshSource(source.id)}
                  disabled={refreshing === source.id}
                  className="btn btn-secondary"
                >
                  {refreshing === source.id ? '刷新中...' : '立即检查'}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {sources.length === 0 ? (
        <div className="py-12 text-center">
          <div className="mb-4 text-5xl text-gray-400">◌</div>
          <p className="text-gray-500">暂无信息源</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sources.map(source => (
            <SourceCard
              key={source.id}
              source={source}
              onRefresh={() => void handleRefreshSource(source.id)}
              refreshing={refreshing === source.id}
            />
          ))}
        </div>
      )}

      <div className="text-sm text-gray-500">
        当前覆盖活动总量: {totalActivities}
      </div>
    </div>
  )
}

export default SourcesPage
