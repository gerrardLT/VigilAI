import type { AnalysisFieldPayload, AnalysisLayerResult } from './analysis'
import type { AgentAnalysisSnapshot } from './agentAnalysis'

export type {
  AnalysisCondition,
  AnalysisFieldPayload,
  AnalysisLayerResult,
  AnalysisLayer,
  AnalysisResultsFilters,
  AnalysisTemplate,
  AnalysisTemplateDraftPreviewRequest,
  AnalysisTemplatePreview,
  AnalysisTemplatePreviewResultItem,
  AnalysisTemplatePreviewResults,
  AnalysisTemplateCreateRequest,
  AnalysisTemplateUpdateRequest,
} from './analysis'

export type {
  AgentAnalysisActivitySummary,
  AgentAnalysisEvidence,
  AgentAnalysisJobCreateRequest,
  AgentAnalysisJobDetail,
  AgentAnalysisJobItem,
  AgentAnalysisJobItemDetail,
  AgentAnalysisJobListResponse,
  AgentAnalysisJobScopeType,
  AgentAnalysisJobSummary,
  AgentAnalysisJobTriggerType,
  AgentAnalysisReview,
  AgentAnalysisReviewRequest,
  AgentAnalysisReviewResult,
  AgentAnalysisSnapshot,
  AgentAnalysisSnapshotStatus,
  AgentAnalysisStep,
} from './agentAnalysis'

export type Category =
  | 'hackathon'
  | 'data_competition'
  | 'coding_competition'
  | 'other_competition'
  | 'airdrop'
  | 'bounty'
  | 'grant'
  | 'dev_event'
  | 'news'

export type Priority = 'high' | 'medium' | 'low'

export type SourceType =
  | 'rss'
  | 'web'
  | 'api'
  | 'firecrawl'
  | 'kaggle'
  | 'tech_media'
  | 'airdrop'
  | 'data_competition'
  | 'hackathon_aggregator'
  | 'bounty'
  | 'enterprise'
  | 'government'
  | 'design_competition'
  | 'coding_competition'
  | 'universal'

export type SourceStatus = 'idle' | 'running' | 'success' | 'error'
export type SourceFreshnessLevel = 'fresh' | 'aging' | 'stale' | 'critical' | 'never'
export type TrackingStatus = 'saved' | 'tracking' | 'done' | 'archived'
export type DigestStatus = 'draft' | 'sent'
export type DeadlineLevel = 'urgent' | 'soon' | 'upcoming' | 'later' | 'none' | 'expired'
export type TrustLevel = 'high' | 'medium' | 'low'

export interface Prize {
  amount: number | null
  currency: string
  description: string | null
}

export interface ActivityDates {
  start_date: string | null
  end_date: string | null
  deadline: string | null
}

export interface TimelineEvent {
  key: string
  label: string
  timestamp: string
}

export interface ActivityListItem {
  id: string
  title: string
  description: string | null
  full_content?: string | null
  source_id: string
  source_name: string
  url: string
  category: Category
  tags: string[]
  prize: Prize | null
  dates: ActivityDates | null
  location: string | null
  organizer: string | null
  image_url?: string | null
  summary?: string | null
  score?: number | null
  score_reason?: string | null
  deadline_level?: DeadlineLevel | null
  trust_level?: TrustLevel | null
  updated_fields?: string[]
  analysis_fields?: AnalysisFieldPayload
  analysis_status?: 'passed' | 'watch' | 'rejected' | null
  analysis_failed_layer?: string | null
  analysis_summary_reasons?: string[]
  analysis_summary?: string | null
  analysis_reasons?: string[]
  analysis_risk_flags?: string[]
  analysis_recommended_action?: string | null
  analysis_confidence?: number | null
  analysis_structured?: Record<string, unknown>
  analysis_approved_snapshot?: AgentAnalysisSnapshot | null
  analysis_latest_draft?: AgentAnalysisSnapshot | null
  analysis_template_id?: string | null
  analysis_current_run_id?: string | null
  analysis_updated_at?: string | null
  is_tracking?: boolean
  is_favorited?: boolean
  is_digest_candidate?: boolean
  status: string
  created_at: string
  updated_at: string
}

export type Activity = ActivityListItem

export interface TrackingState {
  activity_id: string
  is_favorited: boolean
  status: TrackingStatus
  notes: string | null
  next_action: string | null
  remind_at: string | null
  created_at: string
  updated_at: string
}

export interface TrackingItem extends TrackingState {
  activity: ActivityListItem
}

export interface ActivityDetail extends ActivityListItem {
  analysis_layer_results?: AnalysisLayerResult[]
  analysis_score_breakdown?: Record<string, number>
  timeline?: TimelineEvent[]
  related_items?: ActivityListItem[]
  tracking?: TrackingState | null
}

export interface AnalysisResultItem extends ActivityListItem {
  analysis_layer_results?: AnalysisLayerResult[]
  analysis_score_breakdown?: Record<string, number>
}

export interface AnalysisResultsResponse {
  total: number
  page: number
  page_size: number
  items: AnalysisResultItem[]
}

export interface Source {
  id: string
  name: string
  type: SourceType
  category?: Category
  status: SourceStatus
  last_run: string | null
  last_success: string | null
  activity_count: number
  error_message: string | null
  health_score?: number
  freshness_level?: SourceFreshnessLevel
  last_success_age_hours?: number | null
  needs_attention?: boolean
}

export interface ActivityListResponse {
  total: number
  page: number
  page_size: number
  total_pages?: number
  items: ActivityListItem[]
}

export interface StatsResponse {
  total_activities: number
  total_sources: number
  activities_by_category: Record<string, number>
  activities_by_source: Record<string, number>
  recent_activities: number
  last_update: string | null
}

export interface WorkspaceOverview extends StatsResponse {
  tracked_count: number
  favorited_count: number
}

export interface WorkspaceTrend {
  date: string
  count: number
}

export interface WorkspaceAnalysisOverview {
  total: number
  passed: number
  watch: number
  rejected: number
}

export interface DigestSummary {
  id: string
  digest_date: string
  title: string
  summary: string | null
  content: string
  item_ids: string[]
  status: DigestStatus
  created_at: string
  updated_at: string
  last_sent_at: string | null
  send_channel: string | null
}

export type DigestDetail = DigestSummary

export interface WorkspaceResponse {
  overview: WorkspaceOverview
  top_opportunities: ActivityListItem[]
  digest_preview: DigestSummary | null
  trends: WorkspaceTrend[]
  alert_sources: Source[]
  first_actions: ActivityListItem[]
  analysis_overview?: WorkspaceAnalysisOverview
  blocked_opportunities?: ActivityListItem[]
}

export interface RefreshResponse {
  success: boolean
  message: string
}

export interface SuccessResponse {
  success: boolean
}

export interface CategoryOption {
  value: string
  label: string
}

export interface ActivityFilters {
  category?: string
  source_id?: string
  status?: string
  search?: string
  analysis_status?: string
  deadline_level?: string
  trust_level?: string
  prize_range?: string
  solo_friendliness?: string
  reward_clarity?: string
  effort_level?: string
  remote_mode?: string
  tracking_state?: string
  is_tracking?: boolean
  is_favorited?: boolean
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface TrackingUpsertRequest {
  is_favorited?: boolean
  status?: TrackingStatus
  notes?: string | null
  next_action?: string | null
  remind_at?: string | null
}

export interface DigestGenerateRequest {
  digest_date?: string
}

export interface DigestSendRequest {
  send_channel?: string
}

export interface DigestCandidateRequest {
  digest_date?: string
}

export interface OpportunityAiFilterRequest {
  base_filters?: ActivityFilters
  query: string
}

export interface OpportunityAiFilterItem extends ActivityListItem {
  ai_match_reason: string
  ai_match_confidence: string
  uncertainties?: string[]
}

export interface OpportunityAiFilterResponse {
  query: string
  parsed_intent_summary: string
  reason_summary?: string
  candidate_count: number
  matched_count: number
  discarded_count: number
  items: OpportunityAiFilterItem[]
}

export const CATEGORY_LABELS: Record<Category, string> = {
  hackathon: '黑客松',
  data_competition: '数据竞赛',
  coding_competition: '编程竞赛',
  other_competition: '其他竞赛',
  airdrop: '空投',
  bounty: '赏金',
  grant: '资助',
  dev_event: '开发者活动',
  news: '科技新闻',
}

export const STATUS_COLORS: Record<SourceStatus, string> = {
  idle: 'bg-gray-400',
  running: 'bg-blue-500',
  success: 'bg-green-500',
  error: 'bg-red-500',
}

export const STATUS_LABELS: Record<SourceStatus, string> = {
  idle: '空闲',
  running: '运行中',
  success: '成功',
  error: '错误',
}
