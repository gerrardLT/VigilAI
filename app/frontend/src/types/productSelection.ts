export type ProductSelectionQueryType = 'keyword' | 'category' | 'listing_url'
export type ProductSelectionPlatformScope = 'taobao' | 'xianyu' | 'both'
export type ProductSelectionJobStatus = 'running' | 'completed' | 'failed'
export type ProductSelectionTrackingStatus = 'saved' | 'tracking' | 'done' | 'archived'
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

export interface ProductSelectionOpportunityDetail extends ProductSelectionOpportunity {
  signals: ProductSelectionSignal[]
  tracking: ProductSelectionTrackingState | null
  query: ProductSelectionResearchJob | null
}

export interface ProductSelectionResearchJobResponse {
  job: ProductSelectionResearchJob
  total: number
  items: ProductSelectionOpportunity[]
}

export interface ProductSelectionOpportunityListResponse {
  total: number
  page: number
  page_size: number
  items: ProductSelectionOpportunity[]
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
}

export interface ProductSelectionResearchJobCreateRequest {
  query_type: ProductSelectionQueryType
  query_text: string
  platform_scope: ProductSelectionPlatformScope
}

export interface ProductSelectionOpportunityFilters {
  query_id?: string
  platform?: string
  search?: string
  risk_tag?: string
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
