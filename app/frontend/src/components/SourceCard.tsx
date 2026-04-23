import type { Source } from '../types'
import { localizeAnalysisText } from '../utils/analysisI18n'
import { formatRelativeTime } from '../utils/formatDate'
import { STATUS_COLOR_MAP, STATUS_TEXT_MAP } from '../utils/constants'

interface SourceCardProps {
  source: Source
  refreshing: boolean
  onRefresh: () => void
}

const FRESHNESS_STYLES = {
  fresh: 'bg-emerald-50 text-emerald-700',
  aging: 'bg-amber-50 text-amber-700',
  stale: 'bg-orange-50 text-orange-700',
  critical: 'bg-rose-50 text-rose-700',
  never: 'bg-slate-100 text-slate-600',
} as const

const FRESHNESS_LABELS = {
  fresh: '新鲜',
  aging: '需要观察',
  stale: '已陈旧',
  critical: '需要处理',
  never: '尚未成功',
} as const

export function SourceCard({ source, refreshing, onRefresh }: SourceCardProps) {
  const freshnessLevel = source.freshness_level || 'never'
  const healthScore = source.health_score ?? 0
  const displayName = localizeAnalysisText(source.name)
  const displayErrorMessage = localizeAnalysisText(source.error_message)

  return (
    <div className="card space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${STATUS_COLOR_MAP[source.status]}`}
              title={STATUS_TEXT_MAP[source.status]}
            />
            <h3 className="font-semibold text-gray-900">{displayName}</h3>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
              {source.type.toUpperCase()}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-700">
              健康分 {healthScore}
            </span>
            <span className={`rounded-full px-2 py-1 font-medium ${FRESHNESS_STYLES[freshnessLevel]}`}>
              {FRESHNESS_LABELS[freshnessLevel]}
            </span>
            {source.needs_attention && (
              <span className="rounded-full bg-rose-100 px-2 py-1 font-medium text-rose-700">
                需关注
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="btn btn-secondary flex items-center gap-1"
        >
          {refreshing ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
              <span>刷新中</span>
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>刷新</span>
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-gray-500">当前状态</div>
          <div className="mt-1 font-medium text-gray-900">{STATUS_TEXT_MAP[source.status]}</div>
        </div>
        <div>
          <div className="text-gray-500">活动数</div>
          <div className="mt-1 font-medium text-gray-900">{source.activity_count}</div>
        </div>
        <div>
          <div className="text-gray-500">最后运行</div>
          <div className="mt-1 font-medium text-gray-900">
            {source.last_run ? formatRelativeTime(source.last_run) : '暂无记录'}
          </div>
        </div>
        <div>
          <div className="text-gray-500">上次成功</div>
          <div className="mt-1 font-medium text-gray-900">
            {source.last_success ? formatRelativeTime(source.last_success) : '尚未成功'}
          </div>
        </div>
      </div>

      {source.last_success_age_hours !== undefined && (
        <div className="text-xs text-gray-500">
          成功时延: {source.last_success_age_hours === null ? '未知' : `${source.last_success_age_hours} 小时前`}
        </div>
      )}

      {source.error_message && (
        <div className="rounded-xl bg-rose-50 p-3 text-xs text-rose-700">
          异常原因: {displayErrorMessage}
        </div>
      )}
    </div>
  )
}

export default SourceCard
