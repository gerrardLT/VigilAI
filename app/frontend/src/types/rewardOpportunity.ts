export interface RewardOpportunityOverview {
  source_count: number
  opportunity_count: number
  candidate_count: number
  high_value_count: number
}

export interface RewardOpportunityItem {
  id: string
  title: string
  source_platform: string
  source_url: string
  ai_stage_2_label: string
  ai_confidence: number
  reward_type?: string | null
  reward_value_text?: string | null
  action_required?: string | null
  ai_summary?: string | null
  created_at: string
}

export interface RewardOpportunityListResponse {
  items: RewardOpportunityItem[]
  total: number
}

export interface RewardOpportunityOperationsResponse {
  sources: Array<Record<string, unknown>>
  recent_jobs: Array<Record<string, unknown>>
}
