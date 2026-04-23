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

const DEADLINE_LEVEL_LABELS: Record<string, string> = {
  urgent: '紧急截止',
  soon: '即将截止',
  upcoming: '近期开放',
  later: '后续关注',
  normal: '常规',
  none: '无截止信息',
  expired: '已截止',
}

const SOURCE_STATUS_LABELS: Record<string, string> = {
  idle: '空闲',
  running: '运行中',
  success: '正常',
  error: '异常',
}

const TRACKING_STATUS_LABELS: Record<string, string> = {
  tracking: '跟进中',
  saved: '已保存',
  skipped: '已跳过',
  archived: '已归档',
  untracked: '未跟进',
}

const DIGEST_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  sent: '已发送',
}

const DIGEST_CHANNEL_LABELS: Record<string, string> = {
  manual: '手动发送',
}

const DISPLAY_TEXT_BY_TEXT: Record<string, string> = {
  'AI Fellowship': 'AI 驻留计划',
  'Grant Sprint': '资助冲刺',
  'Grant Program': '资助计划',
  'Quest Review': '任务复核',
  'Today Digest': '今日日报',
  'Top picks': '今日重点',
  '1 Minute Brief': '1 分钟简报',
  'Today Focus': '今日跟进焦点',
  'Worth tracking': '值得跟进',
  'Updated budget requirement': '预算要求已更新',
  'Need to submit by Friday': '需要在周五前提交',
  'Prepare proposal': '准备提案',
  'Submit budget': '提交预算',
  'Waiting for teammate input': '等待队友反馈',
  'Review partner feedback': '复核协作反馈',
  'Source One': '来源一',
  'Source Two': '来源二',
  'Source Three': '来源三',
  'Long time no progress': '长时间无进展',
  timeout: '超时',
  'Connection timeout': '连接超时',
  'Source refreshed': '来源已刷新',
  'All refreshed': '全部已刷新',
  'Unknown error': '未知错误',
  unknown: '未知',
  'Analysis Results': '分析结果总览',
  'VigilAI Workspace': '分析工作台总览',
  'AI Hackathon': 'AI 黑客松',
  'Daily Digest': '今日日报',
  'Hackathon Feed': '黑客松情报源',
  'Enterprise Feed': '企业情报源',
  'Ship MVP Fast': 'MVP 快速交付',
  'Enterprise RFP': '企业需求征集',
  'Build an AI agent.': '构建一个 AI Agent。',
  'Build an AI product.': '构建一个 AI 产品。',
  'Build an AI app.': '构建一个 AI 应用。',
  'Build an AI prototype.': '构建一个 AI 原型。',
  'High priority AI event.': '高优先级 AI 活动。',
  'High fit for builder-focused teams.': '非常适合以构建为核心的小团队。',
  'Solo-friendly build sprint.': '适合单人参与的快速构建冲刺。',
  'Fast payout path': '回报路径清晰且较快。',
  'Funding support for builders.': '为构建者提供资金支持。',
  'High priority': '优先级高',
  'Recommended first': '建议优先处理',
  'Worth saving': '值得先保存',
  'Good fit': '整体匹配度较高',
  'Longer description for the opportunity.': '这是一条更完整的机会说明。',
  'Fresh, urgent, and high trust.': '信息新、时效强、可信度高。',
  'Review brief first.': '先复核活动说明。',
  'Check eligibility': '先确认参与资格',
  'Need portfolio and intro.': '需要准备作品集和简介。',
  'Submit shortlist': '提交候选清单',
  'Draft shortlist': '起草候选清单',
  'Open Builders': '开放构建者',
  'Top picks for today': '今日重点推荐',
  'Fast deadline': '截止时间紧',
  'Do this first': '建议优先处理',
  'Requires a large team.': '需要较大团队协作。',
  'Looks big but not solo-friendly.': '体量较大，不适合单人推进。',
  'Blocked by team requirement': '因团队要求被拦截',
  'Likely blocked by hard gate.': '大概率会被硬门槛拦截。',
  'High score': '高评分',
  Urgent: '需尽快处理',
  'Low solo fit': '单人匹配度低',
  'Urgent and high trust': '截止紧、可信度高',
  'High ROI': '高回报效率',
  'Reward clarity passed': '奖励清晰度通过',
  'ROI score passed': '回报评分通过',
  'Solo only failed hard gate': '未通过仅限单人的硬门槛',
  'Timed out': '执行超时',
  'Recommended for AI builders': '推荐给 AI 构建者',
  '- AI Hackathon': '- AI 黑客松',
  solo_friendly: '适合单人',
}

const DISPLAY_TEXT_FRAGMENT_BY_TEXT: Record<string, string> = {
  'Summary ': '摘要 ',
  'Short description ': '简要描述 ',
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

export function getDeadlineLevelLabel(level: string | null | undefined) {
  if (!level) {
    return ''
  }
  return DEADLINE_LEVEL_LABELS[level] ?? level
}

export function getSourceStatusLabel(status: string | null | undefined) {
  if (!status) {
    return ''
  }
  return SOURCE_STATUS_LABELS[status] ?? status
}

export function getTrackingStatusLabel(status: string | null | undefined) {
  if (!status) {
    return ''
  }
  return TRACKING_STATUS_LABELS[status] ?? status
}

export function getDigestStatusLabel(status: string | null | undefined) {
  if (!status) {
    return ''
  }
  return DIGEST_STATUS_LABELS[status] ?? status
}

export function getDigestChannelLabel(channel: string | null | undefined) {
  if (!channel) {
    return ''
  }
  return DIGEST_CHANNEL_LABELS[channel] ?? channel
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

export function localizeAnalysisText(text: string | null | undefined) {
  if (!text) {
    return ''
  }
  if (Object.prototype.hasOwnProperty.call(DISPLAY_TEXT_BY_TEXT, text)) {
    return DISPLAY_TEXT_BY_TEXT[text]
  }

  return Object.entries(DISPLAY_TEXT_FRAGMENT_BY_TEXT).reduce((localizedText, [sourceText, targetText]) => {
    return localizedText.includes(sourceText)
      ? localizedText.split(sourceText).join(targetText)
      : localizedText
  }, text)
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
