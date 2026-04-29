export type ProductSelectionQueryType = 'keyword' | 'category' | 'listing_url'
export type ProductSelectionPlatformScope = 'taobao' | 'xianyu' | 'both'
export type ProductSelectionJobStatus = 'running' | 'completed' | 'failed'
export type ProductSelectionTrackingStatus = 'saved' | 'tracking' | 'done' | 'archived'
export type ProductSelectionSourceMode = 'live' | 'fallback' | 'mixed' | 'failed'
export type ProductSelectionSortBy =
  | 'opportunity_score'
  | 'confidence_score'
  | 'created_at'
  | 'updated_at'
  | 'price_mid'

export interface ProductSelectionResearchJob {
  id: string
  query_type: ProductSelectionQueryType
  query_text: string
  platform_scope: ProductSelectionPlatformScope
  status: ProductSelectionJobStatus
  created_at: string
  updated_at: string
}

export interface ProductSelectionPriceBand {
  low: number | null
  mid: number | null
  high: number | null
}

export interface ProductSelectionOpportunity {
  id: string
  query_id: string
  platform: string
  platform_item_id: string
  title: string
  image_url: string | null
  category_path: string | null
  price_low: number | null
  price_mid: number | null
  price_high: number | null
  sales_volume: number | null
  seller_count: number | null
  seller_type: string | null
  seller_name: string | null
  demand_score: number
  competition_score: number
  price_fit_score: number
  risk_score: number
  cross_platform_signal_score: number
  opportunity_score: number
  confidence_score: number
  risk_tags: string[]
  reason_blocks: string[]
  recommended_action: string | null
  source_urls: string[]
  source_mode: ProductSelectionSourceMode
  source_diagnostics: Record<string, unknown>
  snapshot_at: string
  created_at: string
  updated_at: string
  is_tracking: boolean
  is_favorited: boolean
}

export interface ProductSelectionSignal {
  id: string
  opportunity_id: string
  platform: string
  signal_type: string
  value_json: Record<string, unknown>
  sample_size: number
  freshness: string | null
  reliability: number | null
  created_at: string
}

export interface ProductSelectionTrackingState {
  opportunity_id: string
  is_favorited: boolean
  status: ProductSelectionTrackingStatus
  notes: string | null
  next_action: string | null
  remind_at: string | null
  created_at: string
  updated_at: string
}

export interface ProductSelectionTrackingItem extends ProductSelectionTrackingState {
  opportunity: ProductSelectionOpportunity
}

export interface ProductSelectionTrackingFilters {
  status?: ProductSelectionTrackingStatus
  source_mode?: Exclude<ProductSelectionSourceMode, 'mixed'> | ''
  fallback_reason?: string
}

export interface ProductSelectionOpportunityDetail extends ProductSelectionOpportunity {
  signals: ProductSelectionSignal[]
  tracking: ProductSelectionTrackingState | null
  query: ProductSelectionResearchJob | null
  source_summary?: ProductSelectionSourceSummary
}

export interface ProductSelectionSourceSummary {
  overall_mode: ProductSelectionSourceMode
  mode_counts: {
    live: number
    fallback: number
  }
  fallback_used: boolean
  fallback_reasons: string[]
  adapter_runs: Array<{
    platform: string
    mode: ProductSelectionSourceMode
    diagnostics: Record<string, unknown>
    item_count: number
  }>
  extraction_stats_summary: {
    http_candidates_seen: number
    platform_candidates_seen: number
    accepted_candidates: number
    accepted_with_price: number
    accepted_without_price: number
    rejected_non_listing_url: number
    rejected_noise_title: number
    rejected_query_miss: number
    rejected_duplicate_url: number
  }
  seller_mix: {
    enterprise: number
    personal: number
    unknown: number
    with_sales_volume: number
    with_seller_count: number
  }
}

export interface ProductSelectionResearchJobResponse {
  job: ProductSelectionResearchJob
  total: number
  items: ProductSelectionOpportunity[]
  source_summary: ProductSelectionSourceSummary
}

export interface ProductSelectionOpportunityListResponse {
  total: number
  page: number
  page_size: number
  items: ProductSelectionOpportunity[]
  source_summary: ProductSelectionSourceSummary
}

export interface ProductSelectionWorkspaceOverview {
  query_count: number
  opportunity_count: number
  tracked_count: number
  favorited_count: number
}

export interface ProductSelectionWorkspacePlatformBreakdown {
  platform: string
  count: number
}

export interface ProductSelectionWorkspaceResponse {
  overview: ProductSelectionWorkspaceOverview
  recent_queries: ProductSelectionResearchJob[]
  top_opportunities: ProductSelectionOpportunity[]
  tracking_queue: ProductSelectionTrackingItem[]
  platform_breakdown: ProductSelectionWorkspacePlatformBreakdown[]
  source_summary: ProductSelectionSourceSummary
  top_opportunities_source_summary: ProductSelectionSourceSummary
  tracking_queue_source_summary: ProductSelectionSourceSummary
}

export interface ProductSelectionResearchJobCreateRequest {
  query_type: ProductSelectionQueryType
  query_text: string
  platform_scope: ProductSelectionPlatformScope
  rendered_snapshot_html?: string
  rendered_snapshot_path?: string
  detail_snapshot_htmls?: string[]
  detail_snapshot_manifest_path?: string
}

export interface ProductSelectionOpportunityFilters {
  query_id?: string
  platform?: string
  search?: string
  risk_tag?: string
  source_mode?: Exclude<ProductSelectionSourceMode, 'mixed'> | ''
  fallback_reason?: string
  sort_by?: ProductSelectionSortBy
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface ProductSelectionTrackingUpsertRequest {
  is_favorited?: boolean
  status?: ProductSelectionTrackingStatus
  notes?: string | null
  next_action?: string | null
  remind_at?: string | null
}
