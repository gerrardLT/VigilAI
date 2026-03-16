import { Link } from 'react-router-dom'
import { useStats } from '../hooks/useStats'
import { Loading } from '../components/Loading'
import { ErrorMessage } from '../components/ErrorMessage'
import { formatDateTime } from '../utils/formatDate'
import { CATEGORY_COLOR_MAP, CATEGORY_ICON_MAP } from '../utils/constants'
import { CATEGORY_LABELS, type Category } from '../types'

/**
 * 仪表盘页面
 * 显示统计信息概览
 */
export function DashboardPage() {
  const { stats, loading, error, refetch, lastRefresh } = useStats()

  if (loading && !stats) {
    return <Loading text="加载统计数据..." />
  }

  if (error && !stats) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  if (!stats) {
    return null
  }

  // 按类别统计排序
  const categoryStats = Object.entries(stats.activities_by_category)
    .sort(([, a], [, b]) => b - a)

  // 按来源统计排序
  const sourceStats = Object.entries(stats.activities_by_source)
    .sort(([, a], [, b]) => b - a)

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">数据概览</h1>
          {lastRefresh && (
            <p className="text-sm text-gray-500 mt-1">
              上次刷新: {formatDateTime(lastRefresh.toISOString())}
            </p>
          )}
        </div>
        <button
          onClick={refetch}
          className="btn btn-secondary flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          刷新
        </button>
      </div>

      {/* 总览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to="/activities"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold text-gray-900">
                {stats.total_activities}
              </div>
              <div className="text-sm text-gray-500 mt-1">总活动数</div>
            </div>
            <div className="text-4xl">📋</div>
          </div>
        </Link>

        <Link
          to="/sources"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold text-gray-900">
                {stats.total_sources}
              </div>
              <div className="text-sm text-gray-500 mt-1">信息源数</div>
            </div>
            <div className="text-4xl">📡</div>
          </div>
        </Link>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold text-gray-900">
                {categoryStats.length}
              </div>
              <div className="text-sm text-gray-500 mt-1">活动类别</div>
            </div>
            <div className="text-4xl">🏷️</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold text-gray-900">
                {stats.last_update ? formatDateTime(stats.last_update).split(' ')[0] : '-'}
              </div>
              <div className="text-sm text-gray-500 mt-1">最后更新</div>
            </div>
            <div className="text-4xl">🕐</div>
          </div>
        </div>
      </div>

      {/* 详细统计 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 按类别统计 */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">按类别统计</h2>
          </div>
          <div className="p-4">
            {categoryStats.length === 0 ? (
              <p className="text-gray-500 text-center py-4">暂无数据</p>
            ) : (
              <div className="space-y-3">
                {categoryStats.map(([category, count]) => {
                  const percentage = stats.total_activities > 0
                    ? Math.round((count / stats.total_activities) * 100)
                    : 0
                  return (
                    <Link
                      key={category}
                      to={`/activities?category=${category}`}
                      className="block hover:bg-gray-50 rounded-lg p-2 -mx-2 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                              CATEGORY_COLOR_MAP[category as Category] || 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            <span>{CATEGORY_ICON_MAP[category as Category]}</span>
                            <span>{CATEGORY_LABELS[category as Category] || category}</span>
                          </span>
                        </div>
                        <span className="text-sm font-medium text-gray-900">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* 按来源统计 */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">按来源统计</h2>
          </div>
          <div className="p-4">
            {sourceStats.length === 0 ? (
              <p className="text-gray-500 text-center py-4">暂无数据</p>
            ) : (
              <div className="space-y-3">
                {sourceStats.map(([source, count]) => {
                  const percentage = stats.total_activities > 0
                    ? Math.round((count / stats.total_activities) * 100)
                    : 0
                  return (
                    <Link
                      key={source}
                      to={`/activities?source_id=${source}`}
                      className="block hover:bg-gray-50 rounded-lg p-2 -mx-2 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-gray-700">{source}</span>
                        <span className="text-sm font-medium text-gray-900">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
