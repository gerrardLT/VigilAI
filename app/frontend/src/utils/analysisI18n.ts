import type { AnalysisCondition, AnalysisLayer, AnalysisTemplate } from '../types'

const TEMPLATE_NAME_BY_SLUG: Record<string, string> = {
  'quick-money': '快钱优先',
  'low-effort-high-roi': '低投入高回报',
  'safe-trust': '稳妥可信',
  'steady-trust': '稳健可信',
  'safe-and-trusted': '稳妥可信',
}

const TEMPLATE_NAME_BY_TEXT: Record<string, string> = {
  'Quick money': '快钱优先',
  'Low effort, high ROI': '低投入高回报',
  'Safe trust': '稳妥可信',
  'Steady trust': '稳健可信',
  'Safe and trusted': '稳妥可信',
}

const TEMPLATE_DESCRIPTION_BY_TEXT: Record<string, string> = {
  'Fast ROI first': '优先高回报、快决策的机会',
  'Prefer trusted sources': '优先可信来源和信息更完整的机会',
  'Focus on solo-friendly, clear-reward opportunities': '优先单人友好、奖励明确的机会',
  'Prefer trustworthy and well-documented opportunities': '优先可信度高、资料更完整的机会',
  'Prioritize short-cycle opportunities with low effort and explicit rewards.':
    '优先低投入、短周期、奖励明确的机会。',
  'Favor personal opportunities with low setup costs and strong payout-to-effort ratio.':
    '优先启动成本低、回报效率高的个人机会。',
  'Prefer clearer, better-backed opportunities even if payout is slightly slower.':
    '即使回款稍慢，也优先规则更清晰、背书更强的机会。',
}

const LAYER_LABEL_BY_KEY: Record<string, string> = {
  hard_gate: '硬门槛',
  'hard-gates': '硬门槛',
  trust_gate: '可信门槛',
  roi: '回报效率',
  trust: '可信度',
  priority: '优先级',
}

const LAYER_LABEL_BY_TEXT: Record<string, string> = {
  'Hard gate': '硬门槛',
  'Hard gates': '硬门槛',
  'Trust gate': '可信门槛',
  ROI: '回报效率',
  Trust: '可信度',
  Priority: '优先级',
}

const CONDITION_LABEL_BY_KEY: Record<string, string> = {
  reward_clarity: '奖励清晰度',
  solo_friendliness: '单人友好度',
  effort_level: '投入成本',
  payout_speed: '回款速度',
  source_trust: '来源可信度',
  roi_level: '回报效率',
  trust_risk_level: '风险等级',
}

const CONDITION_LABEL_BY_TEXT: Record<string, string> = {
  'Reward must be explicit': '奖励必须明确',
  'Reward clarity': '奖励清晰度',
  'Must be solo-friendly': '必须适合单人',
  'Solo only': '仅限单人',
  'Estimated effort': '预计投入',
  'Payout speed': '回款速度',
  'Source trust': '来源可信度',
  'ROI level': '回报效率',
  'Low risk only': '仅低风险',
}

const ANALYSIS_STATUS_LABELS = {
  passed: '通过',
  watch: '待观察',
  rejected: '淘汰',
} as const

const TRUST_LEVEL_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

const OPERATOR_LABELS: Record<string, string> = {
  eq: '等于',
  neq: '不等于',
  gte: '大于等于',
  lte: '小于等于',
  gt: '大于',
  lt: '小于',
  in: '属于',
  contains: '包含',
}

const MODE_LABELS: Record<string, string> = {
  filter: '筛选',
  rank: '排序',
}

const STRICTNESS_LABELS: Record<string, string> = {
  strict: '严格',
  medium: '中等',
  relaxed: '宽松',
}

const TAG_LABELS: Record<string, string> = {
  roi: '高回报',
  solo: '单人友好',
  trust: '可信度',
  safe: '稳妥',
  trusted: '有背书',
  'money-first': '先看回报',
  'fast-return': '快回款',
  'low-effort': '低投入',
}

function localizeTemplateNameFromParts(name: string, slug?: string | null) {
  return (slug && TEMPLATE_NAME_BY_SLUG[slug]) || TEMPLATE_NAME_BY_TEXT[name] || name
}

function localizeTemplateDescription(description: string | null | undefined) {
  if (!description) {
    return description ?? null
  }
  return TEMPLATE_DESCRIPTION_BY_TEXT[description] || description
}

export function getAnalysisStatusLabel(
  status: string | null | undefined,
  overrides?: Partial<Record<keyof typeof ANALYSIS_STATUS_LABELS, string>>
) {
  if (!status) {
    return ''
  }
  const labels = { ...ANALYSIS_STATUS_LABELS, ...overrides }
  return labels[status as keyof typeof labels] ?? status
}

export function getTrustLevelLabel(level: string | null | undefined) {
  if (!level) {
    return ''
  }
  return TRUST_LEVEL_LABELS[level] ?? level
}

export function getAnalysisOperatorLabel(operator: string | null | undefined) {
  if (!operator) {
    return ''
  }
  return OPERATOR_LABELS[operator] ?? operator
}

export function getAnalysisModeLabel(mode: string | null | undefined) {
  if (!mode) {
    return ''
  }
  return MODE_LABELS[mode] ?? mode
}

export function getAnalysisStrictnessLabel(strictness: string | null | undefined) {
  if (!strictness) {
    return ''
  }
  return STRICTNESS_LABELS[strictness] ?? strictness
}

export function getAnalysisFieldLabel(key: string | null | undefined) {
  if (!key) {
    return ''
  }
  return CONDITION_LABEL_BY_KEY[key] || LAYER_LABEL_BY_KEY[key] || key
}

export function getAnalysisTagLabel(tag: string | null | undefined) {
  if (!tag) {
    return ''
  }
  return TAG_LABELS[tag] ?? tag
}

export function localizeAnalysisCondition(condition: AnalysisCondition): AnalysisCondition {
  return {
    ...condition,
    label:
      CONDITION_LABEL_BY_TEXT[condition.label] ||
      CONDITION_LABEL_BY_KEY[condition.key] ||
      condition.label,
  }
}

export function localizeAnalysisLayer(layer: AnalysisLayer): AnalysisLayer {
  return {
    ...layer,
    label: LAYER_LABEL_BY_TEXT[layer.label] || LAYER_LABEL_BY_KEY[layer.key] || layer.label,
    conditions: (layer.conditions ?? []).map(localizeAnalysisCondition),
  }
}

export function localizeAnalysisTemplate(template: AnalysisTemplate): AnalysisTemplate {
  return {
    ...template,
    name: localizeTemplateNameFromParts(template.name, template.slug),
    description: localizeTemplateDescription(template.description),
    tags: [...(template.tags ?? [])],
    sort_fields: [...(template.sort_fields ?? [])],
    layers: (template.layers ?? []).map(localizeAnalysisLayer),
  }
}
