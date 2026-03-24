import type { Source } from '../types'
import { formatRelativeTime } from '../utils/formatDate'
import { STATUS_COLOR_MAP, STATUS_TEXT_MAP } from '../utils/constants'

interface SourceCardProps {
  source: Source
  refreshing: boolean
  onRefresh: () => void
}

/**
 * 信息源卡片组件
 * 显示信息源状态和操作按钮
 */
export function SourceCard({ source, refreshing, onRefresh }: SourceCardProps) {
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        {/* 左侧信息 */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            {/* 状态指示器 */}
            <span
              className={`w-2 h-2 rounded-full ${STATUS_COLOR_MAP[source.status]}`}
              title={STATUS_TEXT_MAP[source.status]}
            />
            <h3 className="font-semibold text-gray-900">{source.name}</h3>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              {source.type.toUpperCase()}
            </span>
          </div>

          <div className="space-y-1 text-sm text-gray-600">
            <div className="flex items-center gap-4">
              <span>状态: {STATUS_TEXT_MAP[source.status]}</span>
              <span>活动数: {source.activity_count}</span>
            </div>
            
            {source.last_run && (
              <div>
                最后运行: {formatRelativeTime(source.last_run)}
              </div>
            )}

            {source.error_message && (
              <div className="text-red-600 text-xs mt-2 p-2 bg-red-50 rounded">
                错误: {source.error_message}
              </div>
            )}
          </div>
        </div>

        {/* 右侧操作 */}
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="btn btn-secondary flex items-center gap-1"
        >
          {refreshing ? (
            <>
              <span className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
              <span>刷新中</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>刷新</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}

export default SourceCard
