import { Link } from 'react-router-dom'
import type { Activity } from '../types'
import { CATEGORY_LABELS } from '../types'
import { CATEGORY_COLOR_MAP, CATEGORY_ICON_MAP } from '../utils/constants'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'
import { daysUntil, formatDateOnly, isExpired } from '../utils/formatDate'
import { getAnalysisStatusLabel, getTrustLevelLabel, localizeAnalysisText } from '../utils/analysisI18n'
import { deriveTrackingStage, TRACKING_STAGE_LABELS, TRACKING_STAGE_STYLES } from '../utils/trackingStage'

interface ActivityCardProps {
  activity: Activity
}

const ANALYSIS_STATUS_STYLES = {
  passed: 'bg-emerald-50 text-emerald-700',
  watch: 'bg-amber-50 text-amber-700',
  rejected: 'bg-rose-50 text-rose-700',
} as const

export function ActivityCard({ activity }: ActivityCardProps) {
  const deadline = activity.dates?.deadline
  const days = deadline ? daysUntil(deadline) : null
  const expired = deadline ? isExpired(deadline) : false
  const displayTitle = buildActivityDisplayTitle(activity)
  const previewText = buildActivityDisplayExcerpt(activity)
  const trackingStage = activity.is_tracking
    ? deriveTrackingStage({ status: 'tracking', next_action: null, notes: null, remind_at: null })
    : null

  return (
    <Link
      to={`/activities/${activity.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-[28px] border border-slate-200/85 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,250,252,0.98))] p-5 shadow-[0_16px_40px_-28px_rgba(15,23,42,0.35)] transition duration-300 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_22px_46px_-26px_rgba(15,23,42,0.42)]"
    >
      {activity.image_url && (
        <div className="relative -mx-5 -mt-5 mb-5 h-40 overflow-hidden border-b border-slate-200/70 bg-slate-100">
          <img
            src={activity.image_url}
            alt={displayTitle}
            loading="lazy"
            decoding="async"
            className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
            onError={event => {
              ;(event.target as HTMLImageElement).style.display = 'none'
            }}
          />
        </div>
      )}

      <div className="mb-4 flex items-center justify-between gap-3">
        <span
          className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-semibold ${
            CATEGORY_COLOR_MAP[activity.category] || 'bg-slate-100 text-slate-700'
          }`}
        >
          <span>{CATEGORY_ICON_MAP[activity.category]}</span>
          <span>{CATEGORY_LABELS[activity.category]}</span>
        </span>
        <span className="truncate text-xs font-medium text-slate-500">
          {localizeAnalysisText(activity.source_name)}
        </span>
      </div>

      <h3 className="mb-3 line-clamp-2 text-xl font-semibold leading-8 text-slate-950 transition-colors group-hover:text-slate-800">
        {displayTitle}
      </h3>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {activity.score !== undefined && activity.score !== null && (
          <span className="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white">
            评分 {activity.score.toFixed(1)}
          </span>
        )}
        {activity.trust_level && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
            可信度 {getTrustLevelLabel(activity.trust_level)}
          </span>
        )}
        {activity.analysis_status && (
          <span
            data-testid="activity-card-analysis-status"
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${ANALYSIS_STATUS_STYLES[activity.analysis_status]}`}
          >
            {getAnalysisStatusLabel(activity.analysis_status)}
          </span>
        )}
        {trackingStage && (
          <span
            data-testid="activity-card-tracking-stage"
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${TRACKING_STAGE_STYLES[trackingStage]}`}
          >
            {TRACKING_STAGE_LABELS[trackingStage]}
          </span>
        )}
      </div>

      {previewText && <p className="mb-4 line-clamp-2 text-sm leading-6 text-slate-600">{previewText}</p>}

      {activity.score_reason && (
        <div className="mb-4 rounded-2xl border border-amber-200/80 bg-amber-50/80 px-3 py-2 text-xs leading-5 text-amber-900">
          优先理由：{localizeAnalysisText(activity.score_reason)}
        </div>
      )}

      {(activity.analysis_summary_reasons ?? []).length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {activity.analysis_summary_reasons?.slice(0, 2).map(reason => (
            <span key={reason} className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600">
              {localizeAnalysisText(reason)}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto grid gap-3 border-t border-slate-200/80 pt-4 sm:grid-cols-2">
        {activity.prize?.amount ? (
          <div className="rounded-2xl bg-emerald-50 px-3 py-3 text-emerald-800">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-emerald-600">奖励</div>
            <span className="mt-1 block text-sm font-semibold">
              {activity.prize.currency} {activity.prize.amount.toLocaleString()}
            </span>
          </div>
        ) : (
          <div className="rounded-2xl bg-slate-100/80 px-3 py-3 text-slate-500">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em]">奖励</div>
            <span className="mt-1 block text-sm">待补充</span>
          </div>
        )}

        {deadline && (
          <div
            className={`rounded-2xl px-3 py-3 text-xs ${
              expired
                ? 'bg-rose-50 text-rose-700'
                : days !== null && days <= 7
                  ? 'bg-amber-50 text-amber-700'
                  : 'bg-slate-100/80 text-slate-600'
            }`}
          >
            <div className="text-[11px] font-medium uppercase tracking-[0.16em]">截止</div>
            {expired ? (
              <span className="mt-1 block text-sm font-semibold">已截止</span>
            ) : days !== null ? (
              <span className="mt-1 block text-sm font-semibold">
                {days === 0 ? '今天截止' : `${days} 天后截止`}
              </span>
            ) : (
              <span className="mt-1 block text-sm font-semibold">{formatDateOnly(deadline)}</span>
            )}
          </div>
        )}
      </div>
    </Link>
  )
}

export default ActivityCard
