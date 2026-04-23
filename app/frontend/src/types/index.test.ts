import { describe, expect, expectTypeOf, it } from 'vitest'
import type {
  Activity,
  ActivityDetail,
  ActivityFilters,
  AnalysisTemplate,
  Category,
  DigestDetail,
  DigestStatus,
  OpportunityAiFilterResponse,
  SourceType,
  StatsResponse,
  TrackingItem,
  TrackingState,
  TrackingStatus,
  WorkspaceResponse,
} from './index'

const categories: Category[] = [
  'hackathon',
  'data_competition',
  'coding_competition',
  'other_competition',
  'airdrop',
  'bounty',
  'grant',
  'dev_event',
  'news',
]

const sourceTypes: SourceType[] = [
  'rss',
  'web',
  'api',
  'firecrawl',
  'kaggle',
  'tech_media',
  'airdrop',
  'data_competition',
  'hackathon_aggregator',
  'bounty',
  'enterprise',
  'government',
  'design_competition',
  'coding_competition',
  'universal',
]

const trackingState: TrackingState = {
  activity_id: 'activity-1',
  is_favorited: true,
  status: 'tracking' satisfies TrackingStatus,
  notes: 'Prepare submission draft',
  next_action: 'Submit before Friday',
  remind_at: '2026-03-24T09:00:00Z',
  created_at: '2026-03-23T08:00:00Z',
  updated_at: '2026-03-23T08:30:00Z',
}

const activity: Activity = {
  id: 'activity-1',
  title: 'Global AI Hackathon',
  description: 'Build an AI prototype in 48 hours.',
  full_content: 'Long-form content for the opportunity.',
  source_id: 'devpost',
  source_name: 'Devpost',
  url: 'https://example.com/opportunity',
  category: 'hackathon',
  tags: ['ai', 'global'],
  prize: {
    amount: 5000,
    currency: 'USD',
    description: 'Grand prize',
  },
  dates: {
    start_date: '2026-03-25T00:00:00Z',
    end_date: '2026-03-27T00:00:00Z',
    deadline: '2026-03-24T23:59:00Z',
  },
  location: 'Remote',
  organizer: 'Open Source Labs',
  image_url: 'https://example.com/cover.png',
  summary: 'High-signal hackathon with cash prize and near deadline.',
  score: 8.7,
  score_reason: 'Recent opportunity with prize and urgent deadline.',
  deadline_level: 'urgent',
  trust_level: 'high',
  updated_fields: ['summary', 'score'],
  analysis_fields: {
    roi_level: 'high',
    solo_friendliness: 'solo_friendly',
    _confidence: {
      roi_level: 'high',
    },
  },
  analysis_status: 'passed',
  analysis_failed_layer: null,
  analysis_summary_reasons: ['Reward clarity passed', 'ROI score passed'],
  is_tracking: true,
  is_favorited: true,
  status: 'upcoming',
  created_at: '2026-03-20T08:00:00Z',
  updated_at: '2026-03-23T08:00:00Z',
}

const template: AnalysisTemplate = {
  id: 'tpl-1',
  name: 'Quick money',
  slug: 'quick-money',
  description: 'Prefer fast and low-effort opportunities.',
  is_default: true,
  tags: ['money-first'],
  layers: [
    {
      key: 'hard_gate',
      label: 'Hard gate',
      enabled: true,
      mode: 'filter',
      conditions: [
        {
          key: 'reward_clarity',
          label: 'Reward clarity',
          enabled: true,
          operator: 'gte',
          value: 'medium',
          hard_fail: true,
        },
      ],
    },
  ],
  sort_fields: ['roi', 'payout_speed'],
  created_at: '2026-03-25T08:00:00Z',
  updated_at: '2026-03-25T08:00:00Z',
}

const activityDetail: ActivityDetail = {
  ...activity,
  timeline: [
    {
      key: 'created_at',
      label: 'Created',
      timestamp: '2026-03-20T08:00:00Z',
    },
  ],
  related_items: [
    {
      ...activity,
      id: 'activity-2',
      title: 'Regional AI Hackathon',
      is_tracking: false,
      is_favorited: false,
    },
  ],
  tracking: trackingState,
}

const trackingItem: TrackingItem = {
  ...trackingState,
  activity,
}

const digest: DigestDetail = {
  id: 'digest-1',
  digest_date: '2026-03-23',
  title: 'VigilAI Digest 2026-03-23',
  summary: 'Top opportunities for the day',
  content: '- Global AI Hackathon: High-signal hackathon with cash prize and near deadline.',
  item_ids: ['activity-1'],
  status: 'draft' satisfies DigestStatus,
  created_at: '2026-03-23T08:00:00Z',
  updated_at: '2026-03-23T08:05:00Z',
  last_sent_at: null,
  send_channel: null,
}

const stats: StatsResponse = {
  total_activities: 42,
  total_sources: 6,
  activities_by_category: { hackathon: 10 },
  activities_by_source: { devpost: 12 },
  recent_activities: 7,
  last_update: '2026-03-23T08:00:00Z',
}

const workspace: WorkspaceResponse = {
  overview: {
    ...stats,
    tracked_count: 4,
    favorited_count: 2,
  },
  top_opportunities: [activity],
  digest_preview: digest,
  trends: [{ date: '2026-03-23', count: 7 }],
  alert_sources: [
    {
      id: 'devpost',
      name: 'Devpost',
      type: 'web',
      category: 'hackathon',
      status: 'success',
      last_run: '2026-03-23T07:00:00Z',
      last_success: '2026-03-23T07:00:00Z',
      activity_count: 12,
      error_message: null,
    },
  ],
  first_actions: [activity],
}

const extendedFilters: ActivityFilters = {
  category: 'hackathon',
  prize_range: '500-2000',
  solo_friendliness: 'solo_friendly',
  reward_clarity: 'high',
  effort_level: 'low',
  remote_mode: 'remote',
}

const aiFilterResponse: OpportunityAiFilterResponse = {
  query: '只保留适合独立开发者的机会',
  parsed_intent_summary: '筛选适合单人开发的机会',
  candidate_count: 10,
  matched_count: 3,
  discarded_count: 7,
  items: [
    {
      ...activity,
      ai_match_reason: '适合单人开发，奖励明确',
      ai_match_confidence: 'high',
      uncertainties: [],
    },
  ],
}

describe('frontend V2 contract types', () => {
  it('covers the backend category taxonomy', () => {
    expect(categories).toEqual([
      'hackathon',
      'data_competition',
      'coding_competition',
      'other_competition',
      'airdrop',
      'bounty',
      'grant',
      'dev_event',
      'news',
    ])
  })

  it('covers the backend source type taxonomy', () => {
    expect(sourceTypes).toContain('firecrawl')
    expect(sourceTypes).toContain('hackathon_aggregator')
    expect(sourceTypes).toContain('universal')
  })

  it('accepts enriched activity fields used by V2', () => {
    expect(activity.summary).toContain('hackathon')
    expect(activity.updated_fields).toEqual(['summary', 'score'])
    expect(activity.is_tracking).toBe(true)
    expect(activity.analysis_fields?.roi_level).toBe('high')
    expect(activity.analysis_status).toBe('passed')
    expectTypeOf(activity.score).toMatchTypeOf<number | null | undefined>()
  })

  it('accepts analysis templates used by the AI filtering MVP', () => {
    expect(template.slug).toBe('quick-money')
    expect(template.layers[0].conditions[0].hard_fail).toBe(true)
  })

  it('accepts activity detail payloads with timeline, related items, and tracking state', () => {
    expect(activityDetail.timeline?.[0].label).toBe('Created')
    expect(activityDetail.related_items?.[0].id).toBe('activity-2')
    expect(activityDetail.tracking?.status).toBe('tracking')
  })

  it('accepts tracking items joined with activity payloads', () => {
    expect(trackingItem.activity.id).toBe('activity-1')
    expect(trackingItem.status).toBe('tracking')
  })

  it('accepts digest payloads and workspace aggregates', () => {
    expect(digest.item_ids).toEqual(['activity-1'])
    expect(workspace.overview.recent_activities).toBe(7)
    expect(workspace.digest_preview?.id).toBe('digest-1')
    expect(workspace.first_actions[0].id).toBe('activity-1')
  })

  it('accepts extended opportunity filters and AI filter responses', () => {
    expect(extendedFilters.prize_range).toBe('500-2000')
    expect(extendedFilters.remote_mode).toBe('remote')
    expect(aiFilterResponse.matched_count).toBe(3)
    expect(aiFilterResponse.items[0].ai_match_reason).toContain('适合单人开发')
  })
})
