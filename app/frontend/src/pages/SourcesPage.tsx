import { useState } from 'react'
import { useSources } from '../hooks/useSources'
import { api } from '../services/api'
import { SourceCard } from '../components/SourceCard'
import { Loading } from '../components/Loading'
import { ErrorMessage } from '../components/ErrorMessage'
import { Toast } from '../components/Toast'

/**
 * 信息源管理页面
 */
export function SourcesPage() {
  const { sources, loading, error, refetch } = useSources()
  const [refreshing, setRefreshing] = useState<string | null>(null)
  const [refreshingAll, setRefreshingAll] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // 刷新单个信息源
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

  // 刷新所有信息源
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
    return <Loading text="加载信息源..." />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  // 统计信息
  const totalSources = sources.length
  const activeSources = sources.filter(s => s.status === 'success' || s.status === 'running').length
  const errorSources = sources.filter(s => s.status === 'error').length
  const totalActivities = sources.reduce((sum, s) => sum + s.activity_count, 0)

  return (
    <div className="space-y-6">
      {/* Toast通知 */}
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      {/* 页面标题和操作 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">信息源管理</h1>
          <p className="text-sm text-gray-500 mt-1">
            共 {totalSources} 个信息源，{activeSources} 个正常，{errorSources} 个异常
          </p>
        </div>
        <button
          onClick={handleRefreshAll}
          disabled={refreshingAll}
          className="btn btn-primary flex items-center gap-2"
        >
          {refreshingAll ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              刷新中...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              刷新全部
            </>
          )}
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-gray-900">{totalSources}</div>
          <div className="text-sm text-gray-500">总信息源</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">{activeSources}</div>
          <div className="text-sm text-gray-500">正常运行</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-red-600">{errorSources}</div>
          <div className="text-sm text-gray-500">异常</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-blue-600">{totalActivities}</div>
          <div className="text-sm text-gray-500">总活动数</div>
        </div>
      </div>

      {/* 信息源列表 */}
      {sources.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-5xl mb-4">📡</div>
          <p className="text-gray-500">暂无信息源</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map(source => (
            <SourceCard
              key={source.id}
              source={source}
              onRefresh={() => handleRefreshSource(source.id)}
              refreshing={refreshing === source.id}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default SourcesPage
