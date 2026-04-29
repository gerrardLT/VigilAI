export const TRACKING_UPDATED_EVENT = 'vigilai:tracking-updated'

export interface TrackingUpdatedDetail {
  source?: 'workspace' | 'activity_detail' | 'tracking'
  action?: 'track' | 'favorite' | 'plan_saved' | 'status_changed' | 'batch_updated' | 'deleted'
  activityId?: string
  stage?: string | null
  nextAction?: string | null
  remindAt?: string | null
}

export function notifyTrackingUpdated(detail?: TrackingUpdatedDetail) {
  if (typeof window === 'undefined') {
    return
  }

  window.dispatchEvent(new CustomEvent<TrackingUpdatedDetail>(TRACKING_UPDATED_EVENT, { detail }))
}
