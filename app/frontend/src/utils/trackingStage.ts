import type { TrackingStageValue, TrackingState, TrackingStatus } from '../types'

export type TrackingStage = TrackingStageValue

export const TRACKING_STAGE_LABELS: Record<TrackingStage, string> = {
  to_decide: '待判断',
  watching: '已关注',
  preparing: '准备参与',
  submitted: '已提交',
  dropped: '已放弃',
}

export const TRACKING_STAGE_STYLES: Record<TrackingStage, string> = {
  to_decide: 'bg-slate-100 text-slate-700',
  watching: 'bg-sky-100 text-sky-700',
  preparing: 'bg-amber-100 text-amber-700',
  submitted: 'bg-emerald-100 text-emerald-700',
  dropped: 'bg-gray-100 text-gray-600',
}

export const TRACKING_STAGE_OPTIONS: Array<{ value: TrackingStage; label: string }> = [
  { value: 'to_decide', label: '待判断' },
  { value: 'watching', label: '已关注' },
  { value: 'preparing', label: '准备参与' },
  { value: 'submitted', label: '已提交' },
  { value: 'dropped', label: '已放弃' },
]

export function isTrackingStage(value: string): value is TrackingStage {
  return value in TRACKING_STAGE_LABELS
}

type TrackingStageSource =
  | Pick<TrackingState, 'status' | 'stage' | 'next_action' | 'notes' | 'remind_at'>
  | null
  | undefined

export function deriveTrackingStage(source: TrackingStageSource): TrackingStage {
  if (!source) return 'to_decide'
  if (source.stage && source.stage in TRACKING_STAGE_LABELS) {
    return source.stage
  }

  if (source.status === 'done') return 'submitted'
  if (source.status === 'archived') return 'dropped'
  if (source.status === 'saved') return 'to_decide'

  const hasExecutionSignal = Boolean(
    source.next_action?.trim() || source.notes?.trim() || source.remind_at?.trim()
  )

  return hasExecutionSignal ? 'preparing' : 'watching'
}

export function mapTrackingStageToStatus(stage: TrackingStage): TrackingStatus {
  if (stage === 'submitted') return 'done'
  if (stage === 'dropped') return 'archived'
  if (stage === 'to_decide') return 'saved'
  return 'tracking'
}
