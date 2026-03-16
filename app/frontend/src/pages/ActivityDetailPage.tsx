import { useParams, useNavigate, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from '../services/api'
import type { Activity } from '../types'
import { Loading } from '../components/Loading'
import { ErrorMessage } from '../components/ErrorMessage'
import { formatDateTime, formatDateOnly, daysUntil, isExpired } from '../utils/formatDate'
import { CATEGORY_COLOR_MAP, CATEGORY_ICON_MAP } from '../utils/constants'
import { CATEGORY_LABELS } from '../types'

/**
 * 活动详情页面
 */
export function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activity, setActivity] = useState<Activity | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return

    const fetchActivity = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getActivity(id)
        setActivity(data)
      } catch (err) {
        const message = err instanceof Error ? err.message : '获取活动详情失败'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    fetchActivity()
  }, [id])

  if (loading) {
    return <Loading text="加载活动详情..." />
  }

  if (error) {
    return (
      <ErrorMessage
        message={error}
        onRetry={() => window.location.reload()}
      />
    )
  }

  if (!activity) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-5xl mb-4">🔍</div>
        <p className="text-gray-500">活动不存在</p>
        <Link to="/activities" className="mt-4 text-primary-600 hover:underline">
          返回活动列表
        </Link>
      </div>
    )
  }

  const deadline = activity.dates?.deadline
  const days = deadline ? daysUntil(deadline) : null
  const expired = deadline ? isExpired(deadline) : false

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* 返回按钮 */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        返回
      </button>

      {/* 主卡片 */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* 封面图片 */}
        {activity.image_url && (
          <div className="relative h-64 bg-gray-100">
            <img
              src={activity.image_url}
              alt={activity.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).parentElement!.style.display = 'none'
              }}
            />
          </div>
        )}

        {/* 头部 */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-3 mb-4">
            <span
              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                CATEGORY_COLOR_MAP[activity.category] || 'bg-gray-100 text-gray-800'
              }`}
            >
              <span>{CATEGORY_ICON_MAP[activity.category]}</span>
              <span>{CATEGORY_LABELS[activity.category]}</span>
            </span>
            <span className="text-sm text-gray-500">来自 {activity.source_name}</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{activity.title}</h1>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-6">
          {/* 描述 */}
          {activity.description && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">活动描述</h2>
              <p className="text-gray-600 whitespace-pre-wrap">{activity.description}</p>
            </div>
          )}

          {/* 信息网格 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 奖金信息 */}
            {activity.prize && (
              <div className="bg-green-50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-green-800 mb-2">奖金</h3>
                <div className="text-2xl font-bold text-green-600">
                  {activity.prize.currency} {activity.prize.amount?.toLocaleString() || '待定'}
                </div>
                {activity.prize.description && (
                  <p className="text-sm text-green-700 mt-1">{activity.prize.description}</p>
                )}
              </div>
            )}

            {/* 时间信息 */}
            {activity.dates && (
              <div className="bg-blue-50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-blue-800 mb-2">时间</h3>
                <div className="space-y-2 text-sm">
                  {activity.dates.start_date && (
                    <div className="flex justify-between">
                      <span className="text-blue-600">开始时间</span>
                      <span className="text-blue-800">{formatDateOnly(activity.dates.start_date)}</span>
                    </div>
                  )}
                  {activity.dates.end_date && (
                    <div className="flex justify-between">
                      <span className="text-blue-600">结束时间</span>
                      <span className="text-blue-800">{formatDateOnly(activity.dates.end_date)}</span>
                    </div>
                  )}
                  {deadline && (
                    <div className="flex justify-between">
                      <span className="text-blue-600">截止日期</span>
                      <span className={expired ? 'text-red-600' : 'text-blue-800'}>
                        {formatDateOnly(deadline)}
                        {!expired && days !== null && (
                          <span className="ml-2 text-xs">
                            ({days === 0 ? '今天' : `${days}天后`})
                          </span>
                        )}
                        {expired && <span className="ml-2 text-xs">(已截止)</span>}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 其他信息 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            {activity.organizer && (
              <div className="flex items-center gap-2">
                <span className="text-gray-500">主办方:</span>
                <span className="text-gray-900">{activity.organizer}</span>
              </div>
            )}
            {activity.location && (
              <div className="flex items-center gap-2">
                <span className="text-gray-500">地点:</span>
                <span className="text-gray-900">{activity.location}</span>
              </div>
            )}
            {activity.tags && activity.tags.length > 0 && (
              <div className="flex items-center gap-2 col-span-full">
                <span className="text-gray-500">标签:</span>
                <div className="flex flex-wrap gap-1">
                  {activity.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 元信息 */}
          <div className="pt-4 border-t border-gray-100 text-xs text-gray-400 space-y-1">
            <div>创建时间: {formatDateTime(activity.created_at)}</div>
            <div>更新时间: {formatDateTime(activity.updated_at)}</div>
          </div>
        </div>

        {/* 底部操作 */}
        <div className="p-6 bg-gray-50 border-t border-gray-100">
          <a
            href={activity.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary inline-flex items-center gap-2"
          >
            查看原始链接
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>
    </div>
  )
}

export default ActivityDetailPage
