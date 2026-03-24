import { Link } from 'react-router-dom'
import type { Activity } from '../types'
import { formatDateOnly, daysUntil, isExpired } from '../utils/formatDate'
import { CATEGORY_COLOR_MAP, CATEGORY_ICON_MAP } from '../utils/constants'
import { CATEGORY_LABELS } from '../types'

interface ActivityCardProps {
  activity: Activity
}

/**
 * 活动卡片组件
 * 显示活动的基本信息
 */
export function ActivityCard({ activity }: ActivityCardProps) {
  const deadline = activity.dates?.deadline
  const days = deadline ? daysUntil(deadline) : null
  const expired = deadline ? isExpired(deadline) : false
  const previewText = activity.summary || activity.description

  return (
    <Link
      to={`/activities/${activity.id}`}
      className="card hover:shadow-lg transition-shadow block overflow-hidden"
    >
      {/* 封面图片 */}
      {activity.image_url && (
        <div className="relative h-40 -mx-4 -mt-4 mb-4 bg-gray-100">
          <img
            src={activity.image_url}
            alt={activity.title}
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none'
            }}
          />
        </div>
      )}

      {/* 头部：类别和来源 */}
      <div className="flex items-center justify-between mb-3">
        <span
          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
            CATEGORY_COLOR_MAP[activity.category] || 'bg-gray-100 text-gray-800'
          }`}
        >
          <span>{CATEGORY_ICON_MAP[activity.category]}</span>
          <span>{CATEGORY_LABELS[activity.category]}</span>
        </span>
        <span className="text-xs text-gray-500">{activity.source_name}</span>
      </div>

      {/* 标题 */}
      <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
        {activity.title}
      </h3>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        {activity.score !== undefined && activity.score !== null && (
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
            Score {activity.score.toFixed(1)}
          </span>
        )}
        {activity.trust_level && (
          <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
            Trust {activity.trust_level}
          </span>
        )}
      </div>

      {/* 描述 */}
      {previewText && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {previewText}
        </p>
      )}

      {activity.score_reason && (
        <p className="text-xs text-primary-700 mb-3 line-clamp-2">{activity.score_reason}</p>
      )}

      {/* 底部信息 */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-100">
        {/* 奖金 */}
        {activity.prize?.amount ? (
          <div className="flex items-center gap-1 text-green-600">
            <span className="text-sm font-medium">
              {activity.prize.currency} {activity.prize.amount.toLocaleString()}
            </span>
          </div>
        ) : (
          <div />
        )}

        {/* 截止日期 */}
        {deadline && (
          <div
            className={`text-xs ${
              expired
                ? 'text-red-500'
                : days !== null && days <= 7
                ? 'text-orange-500'
                : 'text-gray-500'
            }`}
          >
            {expired ? (
              '已截止'
            ) : days !== null ? (
              days === 0 ? '今天截止' : `${days}天后截止`
            ) : (
              formatDateOnly(deadline)
            )}
          </div>
        )}
      </div>
    </Link>
  )
}

export default ActivityCard
