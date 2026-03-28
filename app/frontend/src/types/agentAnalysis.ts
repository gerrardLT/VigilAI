export type AgentAnalysisJobScopeType = 'single' | 'batch'
export type AgentAnalysisJobTriggerType = 'manual' | 'scheduled'
export type AgentAnalysisSnapshotStatus = 'pass' | 'watch' | 'reject' | 'insufficient_evidence'

export interface AgentAnalysisSnapshot {
  status: AgentAnalysisSnapshotStatus
  summary: string
  reasons: string[]
  risk_flags: string[]
  recommended_action?: string | null
  confidence?: number | null
  structured: Record<string, unknown>
  evidence_summary?: string | null
  research_state?: string | null
  needs_manual_review?: boolean
  template_id?: string | null
  current_run_id?: string | null
  updated_at?: string | null
}

export interface AgentAnalysisActivitySummary {
  id: string
  title: string
  description?: string | null
  full_content?: string | null
  source_id?: string
  source_name?: string
  url?: string
  category?: string
  [key: string]: unknown
}

export interface AgentAnalysisStep {
  id: string
  job_item_id: string
  step_type: string
  step_status: string
  input_digest?: string | null
  output_payload: Record<string, unknown>
  latency_ms?: number | null
  cost_tokens_in?: number | null
  cost_tokens_out?: number | null
  model_name?: string | null
  created_at: string
}

export interface AgentAnalysisEvidence {
  id: string
  job_item_id: string
  source_type: string
  url?: string | null
  title?: string | null
  snippet?: string | null
  relevance_score?: number | null
  trust_score?: number | null
  supports_claim?: boolean | null
  created_at: string
}

export interface AgentAnalysisReview {
  id: string
  job_item_id: string
  activity_id: string
  review_action: string
  review_note?: string | null
  reviewed_by?: string | null
  created_at: string
}

export interface AgentAnalysisJobItem {
  id: string
  job_id: string
  activity_id: string
  status: string
  needs_research: boolean
  final_draft_status?: string | null
  screening_model?: string | null
  research_model?: string | null
  verdict_model?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at: string
  updated_at: string
}

export interface AgentAnalysisJobItemDetail extends AgentAnalysisJobItem {
  activity: AgentAnalysisActivitySummary | null
  draft: AgentAnalysisSnapshot | null
  steps: AgentAnalysisStep[]
  evidence: AgentAnalysisEvidence[]
  reviews: AgentAnalysisReview[]
}

export interface AgentAnalysisJobSummary {
  id: string
  trigger_type: AgentAnalysisJobTriggerType
  scope_type: AgentAnalysisJobScopeType
  template_id?: string | null
  route_policy: Record<string, unknown>
  budget_policy: Record<string, unknown>
  status: string
  requested_by?: string | null
  created_at: string
  finished_at?: string | null
  item_count: number
  completed_items: number
  failed_items: number
  needs_research_count: number
}

export interface AgentAnalysisJobDetail {
  id: string
  trigger_type: AgentAnalysisJobTriggerType
  scope_type: AgentAnalysisJobScopeType
  template_id?: string | null
  route_policy: Record<string, unknown>
  budget_policy: Record<string, unknown>
  status: string
  requested_by?: string | null
  created_at: string
  finished_at?: string | null
  item_count: number
  items: AgentAnalysisJobItemDetail[]
}

export interface AgentAnalysisJobListResponse {
  total: number
  items: AgentAnalysisJobSummary[]
}

export interface AgentAnalysisJobCreateRequest {
  scope_type: AgentAnalysisJobScopeType
  trigger_type: AgentAnalysisJobTriggerType
  activity_ids?: string[]
  template_id?: string | null
  requested_by?: string | null
}

export interface AgentAnalysisReviewRequest {
  review_note?: string | null
  reviewed_by?: string | null
  edited_snapshot?: Partial<AgentAnalysisSnapshot> | null
}

export interface AgentAnalysisReviewResult {
  review_action: string
  item_id: string
  activity_id: string
  review_note?: string | null
  snapshot: AgentAnalysisSnapshot | null
}
