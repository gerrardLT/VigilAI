import type { ActivityListItem } from '../types'
import { localizeAnalysisText } from './analysisI18n'

function toDateTimeLocalValue(value?: string | null) {
  if (!value) {
    return ''
  }

  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) {
    return value
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(0, 16)
  }

  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

export function buildDefaultTrackingNextAction(
  activity: Pick<ActivityListItem, 'analysis_recommended_action' | 'category'>
) {
  if (activity.analysis_recommended_action?.trim()) {
    return localizeAnalysisText(activity.analysis_recommended_action)
  }

  if (activity.category === 'grant') {
    return '先确认申报资格，再整理申报材料'
  }

  if (activity.category === 'bounty' || activity.category === 'airdrop') {
    return '先核对规则和完成条件，再安排执行'
  }

  if (activity.category === 'hackathon' || activity.category === 'coding_competition') {
    return '先确认参赛要求，再拆出报名和交付准备'
  }

  return '先确认资格和关键门槛，再决定是否投入'
}

export function buildDefaultTrackingRemindAt(activity: Pick<ActivityListItem, 'dates'>) {
  const deadline = activity.dates?.deadline
  if (!deadline) {
    return ''
  }

  const parsedDeadline = new Date(deadline)
  if (Number.isNaN(parsedDeadline.getTime())) {
    return ''
  }

  const reminder = new Date(parsedDeadline.getTime() - 24 * 60 * 60 * 1000)
  const now = new Date()
  if (reminder.getTime() <= now.getTime()) {
    const soonReminder = new Date(now.getTime() + 2 * 60 * 60 * 1000)
    return toDateTimeLocalValue(soonReminder.toISOString())
  }

  return toDateTimeLocalValue(reminder.toISOString())
}

export function buildDefaultTrackingSeed(
  activity: Pick<ActivityListItem, 'analysis_recommended_action' | 'category' | 'dates'>
) {
  return {
    next_action: buildDefaultTrackingNextAction(activity),
    remind_at: buildDefaultTrackingRemindAt(activity),
  }
}
