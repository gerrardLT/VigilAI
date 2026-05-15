export interface RewardOpportunityOverview {
  source_count: number
  opportunity_count: number
  candidate_count: number
  high_value_count: number
  today_crawled_count: number
  today_candidate_count: number
  today_deep_screened_count: number
  classification_distribution: Record<string, number>
  source_health?: Record<string, number>
  paused_source_count?: number
  needs_attention_source_count?: number
  failure_category_counts?: Record<string, number>
  recommended_action_counts?: Record<string, number>
  source_health_trend_summary?: Record<string, number>
  recent_high_value: Array<{
    id: string
    title: string
    source_platform: string
    source_url: string
    ai_stage_2_label: string
    ai_confidence: number
    created_at: string
  }>
  recent_failed_jobs?: RewardCrawlJobItem[]
}

export interface RewardOpportunityEvidenceItem {
  id: string
  opportunity_id: string
  evidence_type: string
  snippet: string
  source_url: string
  metadata?: Record<string, unknown>
  created_at: string
}

export interface RewardOpportunityItem {
  id: string
  title: string
  normalized_title?: string | null
  source_platform: string
  source_type?: string | null
  source_url: string
  canonical_url?: string | null
  published_at?: string | null
  discovered_at?: string | null
  raw_text_excerpt?: string | null
  opportunity_type?: string | null
  reward_type?: string | null
  reward_value_text?: string | null
  action_required?: string | null
  eligibility?: string | null
  deadline_text?: string | null
  deadline_at?: string | null
  ai_stage_1_recall_reason?: string | null
  ai_stage_2_label: string
  ai_confidence: number
  ai_summary?: string | null
  ai_reasoning_brief?: string | null
  ai_missing_evidence?: string[]
  ai_risk_flags?: string[]
  ai_structured_evidence?: Record<string, unknown>
  status?: string
  dedupe_key?: string | null
  content_hash?: string | null
  last_evaluated_at?: string | null
  recheck_after?: string | null
  external_links?: string[]
  evidence?: RewardOpportunityEvidenceItem[]
  investigation?: {
    id: string
    candidate_id: string
    status: string
    current_round: number
    created_at: string
    actions: Array<{
      id: string
      run_id: string
      action_type: string
      target_url?: string | null
      status: string
      payload?: Record<string, unknown>
      created_at: string
    }>
  } | null
  follow_up_documents?: Array<{
    id: string
    source_url: string
    title: string
    summary?: string | null
    metadata?: Record<string, unknown>
    created_at: string
  }>
  created_at: string
}

export interface RewardOpportunityListResponse {
  items: RewardOpportunityItem[]
  total: number
}

export interface RewardSourceSyncResult {
  source_feed_id: string
  job_id: string
  document_count: number
  candidate_count: number
  opportunity_count: number
  error?: string | null
}

export interface RewardSourceFeedItem {
  id: string
  name: string
  source_type: string
  source_platform?: string | null
  entry_url?: string | null
  status: string
  config?: Record<string, unknown>
  last_crawled_at?: string | null
  last_success_at?: string | null
  last_error_message?: string | null
  health_score?: number
  health_level?: 'healthy' | 'watch' | 'risky' | 'cold'
  cold_start_status?: 'cold_start_failed' | 'cold_start_pending' | null
  is_paused?: boolean
  recent_failure_reasons?: string[]
  recent_failure_categories?: string[]
  current_failure_category?: string | null
  failure_advice?: string | null
  recommended_action?: string | null
  pause_mode?: string | null
  needs_attention?: boolean
  consecutive_failures?: number
  recent_job_stats?: {
    total_runs: number
    success_runs: number
    failed_runs: number
    avg_documents: number
  }
  created_at: string
  updated_at: string
  schedule?: RewardSourceSchedule
  blacklisted?: boolean
  blacklist_reason?: string | null
  merge_group_key?: string | null
  preferred_entry_url?: string | null
  needs_authentication?: boolean
  health_trend?: RewardHealthTrendPoint[]
  merged_sources?: Array<{
    id: string
    name: string
    entry_url?: string | null
    preferred?: boolean
  }>
  audit_summary?: RewardSourceAuditItem[]
  import_preview?: {
    source_feed_id: string
    job_id: string
    document_count: number
    candidate_count: number
    opportunity_count: number
    error?: string | null
  }
}

export interface RewardHealthTrendPoint {
  job_id: string
  created_at: string
  status: string
  document_count: number
  candidate_count: number
  opportunity_count: number
}

export interface RewardSourceSchedule {
  auto_sync_enabled: boolean
  sync_interval_minutes: number
}

export interface RewardSourceAuditItem {
  id: string
  source_feed_id: string
  action_type: string
  payload?: Record<string, unknown>
  created_at: string
}

export interface RewardDiscoveryIgnoreItem {
  id: string
  dedupe_key: string
  entry_url: string
  reason?: string | null
  created_at: string
  updated_at: string
}

export interface RewardSourceDiscoveryItem {
  name: string
  entry_url: string
  source_platform: string
  source_type: string
  discovery_queries: string[]
  reasons: string[]
  score: number
  dedupe_key?: string
  matched_urls?: string[]
}

export interface RewardCrawlJobItem {
  id: string
  source_feed_id: string
  status: string
  mode: string
  target_url?: string | null
  document_count: number
  candidate_count: number
  opportunity_count: number
  error_message?: string | null
  failure_category?: string | null
  failure_advice?: string | null
  recommended_action?: string | null
  created_at: string
  completed_at?: string | null
}

export interface RewardSourcePauseResponse {
  id: string
  is_paused: boolean
  status: string
  updated_at: string
}

export interface RewardOpportunityOperationsResponse {
  sources: RewardSourceFeedItem[]
  recent_jobs: RewardCrawlJobItem[]
  failed_jobs?: RewardCrawlJobItem[]
  failure_category_counts?: Record<string, number>
  recommended_action_counts?: Record<string, number>
}

export interface RewardSourceDiscoveryResponse {
  items: RewardSourceDiscoveryItem[]
  ignored_items?: RewardDiscoveryIgnoreItem[]
  total: number
  query_templates?: string[]
  settings_updated_at?: string | null
}

export interface RewardSourceDetailResponse extends RewardSourceFeedItem {
  recent_jobs?: RewardCrawlJobItem[]
  recent_failed_jobs?: RewardCrawlJobItem[]
  audit?: RewardSourceAuditItem[]
  ignored_candidates?: RewardDiscoveryIgnoreItem[]
}

export interface RewardScoutSettingsResponse {
  id: string
  query_templates: string[]
  updated_at?: string | null
}

export interface RewardOpportunitySyncResponse {
  source_count: number
  document_count: number
  candidate_count: number
  opportunity_count: number
  job_ids: string[]
  failures: Array<{
    source_feed_id: string
    job_id: string
    error: string
  }>
}
