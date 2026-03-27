export interface AnalysisCondition {
  key: string
  label: string
  enabled: boolean
  operator: string
  value: string | number | boolean | null
  weight?: number | null
  hard_fail?: boolean
  is_hard_gate?: boolean
  strictness?: 'strict' | 'medium' | 'relaxed'
}

export interface AnalysisLayer {
  key: string
  label: string
  enabled: boolean
  mode: 'filter' | 'rank' | string
  conditions: AnalysisCondition[]
}

export interface AnalysisTemplate {
  id: string
  name: string
  slug: string
  description: string | null
  is_default: boolean
  tags: string[]
  layers: AnalysisLayer[]
  sort_fields: string[]
  created_at: string
  updated_at: string
}

export interface AnalysisTemplatePreview {
  template_id: string
  total: number
  passed: number
  watch: number
  rejected: number
}

export interface AnalysisLayerResult {
  key: string
  label: string
  decision: 'passed' | 'borderline' | 'failed' | string
  reasons: string[]
  score: number
}

export interface AnalysisTemplatePreviewResultItem {
  activity_id: string
  status: 'passed' | 'watch' | 'rejected' | string
  failed_layer: string | null
  summary_reasons: string[]
  layer_results: AnalysisLayerResult[]
}

export interface AnalysisTemplatePreviewResults extends AnalysisTemplatePreview {
  items: AnalysisTemplatePreviewResultItem[]
}

export interface AnalysisTemplateDraftPreviewRequest {
  id?: string
  name: string
  slug?: string
  description?: string | null
  tags?: string[]
  layers?: AnalysisLayer[]
  sort_fields?: string[]
  activity_ids?: string[]
}

export interface AnalysisResultsFilters {
  analysis_status?: string
  page?: number
  page_size?: number
}

export interface AnalysisFieldConfidence {
  [key: string]: string
}

export interface AnalysisFieldPayload {
  roi_level?: 'low' | 'medium' | 'high'
  solo_friendliness?: 'solo_friendly' | 'team_required' | 'unclear'
  reward_clarity?: 'low' | 'medium' | 'high'
  reward_clarity_score?: number
  effort_level?: 'low' | 'medium' | 'high'
  payout_speed?: string
  source_trust?: 'low' | 'medium' | 'high'
  trust_score?: number
  roi_score?: number
  _confidence?: AnalysisFieldConfidence
  [key: string]: unknown
}

export interface AnalysisTemplateCreateRequest {
  name: string
  slug?: string
  description?: string | null
  is_default?: boolean
  tags?: string[]
  layers?: AnalysisLayer[]
  sort_fields?: string[]
}

export interface AnalysisTemplateUpdateRequest {
  name?: string
  slug?: string
  description?: string | null
  tags?: string[]
  layers?: AnalysisLayer[]
  sort_fields?: string[]
}
