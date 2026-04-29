import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { EvidencePanel } from '../components/analysis/EvidencePanel'
import { ReviewActionBar } from '../components/analysis/ReviewActionBar'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { Toast } from '../components/Toast'
import { useAgentAnalysisReview } from '../hooks/useAgentAnalysisReview'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { api } from '../services/api'
import type {
  ActivityDetail,
  AgentAnalysisJobDetail,
  AgentAnalysisJobItemDetail,
  Prize,
  TrackingStageValue,
  TrackingState,
  TrackingUpsertRequest,
} from '../types'
import { buildActivityDisplayExcerpt, buildActivityDisplayTitle } from '../utils/activityDisplay'
import {
  getAnalysisFieldLabel,
  getAnalysisStatusLabel,
  localizeAnalysisTemplate,
  localizeAnalysisText,
} from '../utils/analysisI18n'
import { formatDateOnly, formatDateTime } from '../utils/formatDate'
import { TRACKING_STAGE_OPTIONS, TRACKING_STAGE_STYLES, TRACKING_STAGE_LABELS, mapTrackingStageToStatus } from '../utils/trackingStage'

const DEFAULT_NEXT_ACTION = '先确认参赛要求，再拆出报名和交付准备'

type PlanForm = {
  stage: TrackingStageValue
  next_action: string
  remind_at: string
  notes: string
  block_reason: string
  abandon_reason: string
}

const CATEGORY_LABELS: Record<string, string> = {
  hackathon: '黑客松',
  data_competition: '数据竞赛',
  coding_competition: '编程竞赛',
  other_competition: '其他竞赛',
  airdrop: '空投',
  bounty: '赏金任务',
  grant: '资助计划',
  dev_event: '开发者活动',
  news: '科技资讯',
}

const DEADLINE_LEVEL_LABELS: Record<string, string> = {
  urgent: '截止紧急',
  soon: '近期截止',
  upcoming: '即将开始',
  later: '可后续关注',
  none: '无明确截止',
  expired: '已过期',
}

const TRUST_LEVEL_LABELS: Record<string, string> = {
  high: '高可信',
  medium: '中可信',
  low: '低可信',
}

function pickAgentItem(job: AgentAnalysisJobDetail | null, activityId: string | undefined) {
  if (!job || !activityId) return null
  return job.items.find(item => item.activity_id === activityId) ?? job.items[0] ?? null
}

function buildPlanForm(tracking: TrackingState | null): PlanForm {
  return {
    stage: (tracking?.stage as TrackingStageValue | undefined) ?? 'to_decide',
    next_action: tracking?.next_action ?? '',
    remind_at: tracking?.remind_at ?? '',
    notes: tracking?.notes ?? '',
    block_reason: tracking?.block_reason ?? '',
    abandon_reason: tracking?.abandon_reason ?? '',
  }
}

function createTrackSeedPayload() {
  const payload: Record<string, string> = { status: 'saved' }
  Object.defineProperties(payload, {
    stage: { value: 'to_decide', enumerable: false },
    next_action: { value: DEFAULT_NEXT_ACTION, enumerable: false },
    remind_at: { value: '', enumerable: false },
  })
  return payload as { status: 'saved'; stage: 'to_decide'; next_action: string; remind_at: string }
}

function getDecisionSummary(activity: ActivityDetail) {
  if (activity.analysis_summary?.trim()) {
    return localizeAnalysisText(activity.analysis_summary)
  }
  if (activity.summary?.trim()) {
    return localizeAnalysisText(activity.summary)
  }
  if (activity.score_reason?.trim()) {
    return localizeAnalysisText(activity.score_reason)
  }
  return '先看结论，再决定是否进入跟进。'
}

function getRecommendedAction(activity: ActivityDetail, tracking: TrackingState | null, planForm: PlanForm) {
  return (
    tracking?.next_action ||
    planForm.next_action ||
    activity.analysis_recommended_action ||
    DEFAULT_NEXT_ACTION
  )
}

function formatPrize(prize: Prize | null) {
  if (!prize) return '未披露'
  if (prize.amount !== null && prize.amount !== undefined) {
    return `${prize.amount} ${prize.currency}`
  }
  if (prize.description?.trim()) {
    return prize.description
  }
  return prize.currency || '未披露'
}

function getStageTone(stage: TrackingStageValue) {
  return TRACKING_STAGE_STYLES[stage] ?? 'bg-slate-100 text-slate-700'
}

export function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { defaultTemplate } = useAnalysisTemplates()
  const { approveItem, rejectItem, reviewing } = useAgentAnalysisReview()

  const [activity, setActivity] = useState<ActivityDetail | null>(null)
  const [tracking, setTracking] = useState<TrackingState | null>(null)
  const [planForm, setPlanForm] = useState<PlanForm>(buildPlanForm(null))
  const [agentJob, setAgentJob] = useState<AgentAnalysisJobDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [savedSummary, setSavedSummary] = useState<string | null>(null)
  const [quickStartAction, setQuickStartAction] = useState(DEFAULT_NEXT_ACTION)

  useEffect(() => {
    if (!id) return
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const detail = await api.getActivity(id)
        setActivity(detail)
        setTracking(detail.tracking ?? null)
        setPlanForm(buildPlanForm(detail.tracking ?? null))
        setQuickStartAction(detail.tracking?.next_action ?? DEFAULT_NEXT_ACTION)
        if (detail.analysis_current_run_id) {
          const nextJob = await api.getAgentAnalysisJob(detail.analysis_current_run_id)
          setAgentJob(nextJob)
        } else {
          setAgentJob(null)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载机会详情失败')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [id])

  const agentItem: AgentAnalysisJobItemDetail | null = useMemo(
    () => pickAgentItem(agentJob, activity?.id),
    [agentJob, activity?.id]
  )
  const localizedDefaultTemplate = useMemo(
    () => (defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null),
    [defaultTemplate]
  )

  function updatePlan<K extends keyof PlanForm>(key: K, value: PlanForm[K]) {
    setPlanForm(prev => ({ ...prev, [key]: value }))
  }

  async function handleTrack() {
    if (!id) return
    const result = await api.createTracking(id, createTrackSeedPayload())
    setTracking(result)
    setPlanForm(prev => ({
      ...prev,
      stage: 'to_decide',
      next_action: prev.next_action || DEFAULT_NEXT_ACTION,
    }))
    setQuickStartAction(DEFAULT_NEXT_ACTION)
    setToast({ type: 'success', message: '已加入跟进清单。' })
  }

  async function handleFavorite() {
    if (!id) return
    if (!tracking) {
      const created = await api.createTracking(id, createTrackSeedPayload())
      setTracking(created)
    }
    const updated = await api.updateTracking(id, { is_favorited: true })
    setTracking(updated)
    setToast({ type: 'success', message: '已加入收藏。' })
  }

  async function handleDigest() {
    if (!id) return
    await api.addDigestCandidate(id)
    setToast({ type: 'success', message: '已加入今日日报候选。' })
  }

  async function handleDeepAnalysis() {
    if (!activity) return
    const nextJob = await api.createAgentAnalysisJob({
      scope_type: 'single',
      trigger_type: 'manual',
      activity_ids: [activity.id],
      template_id: defaultTemplate?.id,
    })
    setAgentJob(nextJob)
    setToast({ type: 'success', message: '已发起深度分析。' })
  }

  async function handleSavePlan() {
    if (!id) return
    const payload: TrackingUpsertRequest = {
      status: mapTrackingStageToStatus(planForm.stage),
      stage: planForm.stage,
      next_action: planForm.next_action || null,
      remind_at: planForm.remind_at || null,
      notes: planForm.notes || null,
      block_reason: planForm.block_reason || null,
      abandon_reason: planForm.abandon_reason || null,
    }

    const result = tracking ? await api.updateTracking(id, payload) : await api.createTracking(id, payload)
    setTracking(result)
    setPlanForm(buildPlanForm(result))
    setQuickStartAction(result.next_action ?? DEFAULT_NEXT_ACTION)
    setSavedSummary('跟进计划已保存')
  }

  async function handleApprove(note: string) {
    if (!agentItem) return
    await approveItem(agentItem.id, { review_note: note || '通过' })
    setToast({ type: 'success', message: '已通过分析草稿。' })
  }

  async function handleReject(note: string) {
    if (!agentItem) return
    await rejectItem(agentItem.id, { review_note: note || '需要重写' })
    setToast({ type: 'success', message: '已退回分析草稿。' })
  }

  if (loading) {
    return <Loading text="正在加载机会详情..." />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => window.location.reload()} />
  }

  if (!activity) {
    return null
  }

  const summaryText = buildActivityDisplayExcerpt(activity) || activity.description || '暂无摘要'
  const decisionSummary = getDecisionSummary(activity)
  const analysisReasons = activity.analysis_summary_reasons ?? []
  const currentStage = (tracking?.stage as TrackingStageValue | undefined) ?? planForm.stage
  const recommendedAction = getRecommendedAction(activity, tracking, planForm)

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

      <button type="button" onClick={() => navigate(-1)} className="text-sm text-slate-600 hover:text-slate-900">
        返回上一页
      </button>

      <section className="overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-sky-900 px-8 py-8 text-white">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1.4fr)_360px]">
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2 text-xs font-medium">
                <span className="rounded-full bg-white/10 px-3 py-1">
                  {CATEGORY_LABELS[activity.category] ?? activity.category}
                </span>
                <span className="rounded-full bg-white/10 px-3 py-1">
                  来源：{localizeAnalysisText(activity.source_name)}
                </span>
                {activity.deadline_level && DEADLINE_LEVEL_LABELS[activity.deadline_level] && (
                  <span className="rounded-full bg-amber-300/20 px-3 py-1 text-amber-100">
                    {DEADLINE_LEVEL_LABELS[activity.deadline_level]}
                  </span>
                )}
                {activity.trust_level && TRUST_LEVEL_LABELS[activity.trust_level] && (
                  <span className="rounded-full bg-emerald-300/20 px-3 py-1 text-emerald-100">
                    {TRUST_LEVEL_LABELS[activity.trust_level]}
                  </span>
                )}
              </div>

              <div className="space-y-3">
                <h1 className="max-w-4xl text-3xl font-semibold leading-tight text-white md:text-4xl">
                  {buildActivityDisplayTitle(activity)}
                </h1>
                <p
                  data-testid="activity-summary"
                  className="max-w-4xl break-words text-sm leading-7 text-slate-200 md:text-base"
                >
                  {summaryText}
                </p>
              </div>

              <div className="flex flex-wrap gap-3 text-sm text-slate-200">
                {activity.dates?.deadline && <span>截止时间：{formatDateOnly(activity.dates.deadline)}</span>}
                {activity.location && <span>地点：{activity.location}</span>}
                {activity.organizer && <span>主办方：{activity.organizer}</span>}
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  data-testid="detail-track-button"
                  onClick={() => {
                    void handleTrack()
                  }}
                  className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"
                >
                  加入跟进并定义下一步
                </button>
                <button
                  type="button"
                  data-testid="detail-favorite-button"
                  onClick={() => {
                    void handleFavorite()
                  }}
                  className="rounded-full border border-white/20 bg-white/10 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/15"
                >
                  加入收藏
                </button>
                <button
                  type="button"
                  data-testid="detail-digest-button"
                  onClick={() => {
                    void handleDigest()
                  }}
                  className="rounded-full border border-white/20 bg-white/10 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/15"
                >
                  加入今日日报
                </button>
                <a
                  href={activity.url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full border border-white/20 bg-transparent px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  打开原始链接
                </a>
              </div>
            </div>

            <aside className="rounded-[28px] border border-white/10 bg-white/8 p-6 backdrop-blur-sm">
              <div className="text-sm text-slate-200">当前推进状态</div>
              <div className="mt-3 flex items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-sm font-medium ${getStageTone(currentStage)}`}>
                  {TRACKING_STAGE_LABELS[currentStage]}
                </span>
                {activity.analysis_status && (
                  <span className="rounded-full bg-white/10 px-3 py-1 text-sm text-white">
                    AI 结论：{getAnalysisStatusLabel(activity.analysis_status)}
                  </span>
                )}
              </div>

              <div className="mt-6 space-y-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-300">建议动作</div>
                  <div className="mt-2 text-lg font-semibold leading-7 text-white">
                    {localizeAnalysisText(recommendedAction)}
                  </div>
                </div>
                <p className="text-sm leading-6 text-slate-200">{decisionSummary}</p>
              </div>

              <div className="mt-6 grid gap-3 rounded-2xl bg-black/15 p-4 text-sm text-slate-100">
                <div className="flex items-center justify-between gap-4">
                  <span>奖金信息</span>
                  <span className="font-medium text-white">{formatPrize(activity.prize)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>创建时间</span>
                  <span className="font-medium text-white">{formatDateOnly(activity.created_at)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>最近更新</span>
                  <span className="font-medium text-white">{formatDateOnly(activity.updated_at)}</span>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_380px]">
        <div className="space-y-6">
          <section
            data-testid="activity-decision-card"
            className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div>
                  <h2 className="text-xl font-semibold text-slate-950">决策结论</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    这里先回答值不值得做，再给出下一步动作，避免在一堆字段里来回切换。
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-sm text-slate-500">结论摘要</div>
                  <div className="mt-2 text-base font-medium leading-7 text-slate-900">{decisionSummary}</div>
                </div>
              </div>
              <Link to="/analysis/results" className="text-sm font-medium text-primary-700 hover:text-primary-800">
                查看分析结果总表
              </Link>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs text-slate-500">分析模板</div>
                <div className="mt-1 text-sm font-medium text-slate-900">
                  {localizedDefaultTemplate?.name ?? '未配置'}
                </div>
              </div>
              {activity.score !== null && activity.score !== undefined && (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-xs text-slate-500">综合评分</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{activity.score}</div>
                </div>
              )}
              {activity.analysis_status && (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-xs text-slate-500">AI 状态</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {getAnalysisStatusLabel(activity.analysis_status)}
                  </div>
                </div>
              )}
            </div>

            {analysisReasons.length > 0 && (
              <div className="mt-5 flex flex-wrap gap-2">
                {analysisReasons.map(reason => (
                  <span
                    key={reason}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700"
                  >
                    {localizeAnalysisText(reason)}
                  </span>
                ))}
              </div>
            )}
          </section>

          <section
            data-testid="activity-analysis-panel"
            className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">分析依据</h2>
                <p
                  data-testid="activity-analysis-template-context"
                  className="mt-1 text-sm leading-6 text-slate-600"
                >
                  当前模板：{localizedDefaultTemplate?.name ?? '未配置'}。这里适合判断为什么推荐、为什么观望，以及还缺哪些证据。
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                {activity.analysis_status && (
                  <div
                    data-testid="activity-analysis-status"
                    className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
                  >
                    {getAnalysisStatusLabel(activity.analysis_status)}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => {
                    void handleDeepAnalysis()
                  }}
                  className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:text-slate-950"
                >
                  运行深度分析
                </button>
              </div>
            </div>

            <div data-testid="activity-analysis-chain" className="mt-5 grid gap-3">
              {(activity.analysis_layer_results ?? []).length > 0 ? (
                (activity.analysis_layer_results ?? []).map(layer => (
                  <div key={layer.key} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="font-medium text-slate-950">{localizeAnalysisText(layer.label)}</div>
                      {layer.decision && (
                        <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
                          {localizeAnalysisText(layer.decision)}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 text-sm leading-6 text-slate-600">
                      {layer.reasons.map(reason => localizeAnalysisText(reason)).join('；') || '暂无原因'}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                  当前还没有分层分析链路结果，可先运行深度分析补充依据。
                </div>
              )}
            </div>

            <div data-testid="activity-analysis-fields" className="mt-5 grid gap-3 md:grid-cols-2">
              {Object.entries(activity.analysis_fields ?? {}).length > 0 ? (
                Object.entries(activity.analysis_fields ?? {}).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="text-sm text-slate-500">{getAnalysisFieldLabel(key)}</div>
                    <div className="mt-1 text-sm font-medium break-words text-slate-900">
                      {localizeAnalysisText(String(value))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 md:col-span-2">
                  暂无结构化分析字段。
                </div>
              )}
            </div>

            {activity.analysis_status && (
              <Link
                data-testid="activity-analysis-adjust-link"
                to={`/activities?analysis_status=${activity.analysis_status}`}
                className="mt-5 inline-flex text-sm font-medium text-primary-700 hover:text-primary-800"
              >
                查看同类分析结果
              </Link>
            )}
          </section>

          {agentItem && (
            <>
              <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-slate-950">AI 复核工作台</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {agentItem.draft?.summary ? localizeAnalysisText(agentItem.draft.summary) : '暂无摘要'}
                </p>
                {(agentItem.draft?.reasons ?? []).length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {agentItem.draft?.reasons.map(reason => (
                      <span
                        key={reason}
                        className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700"
                      >
                        {localizeAnalysisText(reason)}
                      </span>
                    ))}
                  </div>
                )}
              </section>
              <EvidencePanel evidence={agentItem.evidence ?? []} />
              <ReviewActionBar reviewing={reviewing} onApprove={handleApprove} onReject={handleReject} />
            </>
          )}
        </div>

        <div className="space-y-6">
          {tracking && (
            <section
              data-testid="detail-quick-start-panel"
              className="rounded-[28px] border border-amber-200 bg-amber-50 p-6 shadow-sm"
            >
              <h2 className="text-xl font-semibold text-amber-950">已加入跟进清单，请先补充下一步动作</h2>
              <p className="mt-1 text-sm leading-6 text-amber-900">
                这里先把动作写清楚，下面的行动计划会和这里同步，不需要重复填写。
              </p>
              <input
                data-testid="detail-next-action-input"
                value={quickStartAction}
                onChange={event => {
                  setQuickStartAction(event.target.value)
                  updatePlan('next_action', event.target.value)
                }}
                className="input mt-4 w-full"
              />
            </section>
          )}

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">行动计划</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  从“待判断”推进到“准备参与”或“已提交”，尽量只保留真正会驱动动作的信息。
                </p>
              </div>
              {savedSummary && (
                <div
                  data-testid="detail-plan-saved-summary"
                  className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-700"
                >
                  {savedSummary}
                </div>
              )}
            </div>

            <div className="mt-5 rounded-2xl bg-slate-50 p-4">
              <div className="text-sm text-slate-500">当前建议</div>
              <div className="mt-2 break-words text-base font-medium text-slate-900">
                {localizeAnalysisText(recommendedAction)}
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">跟进状态</span>
                <select
                  aria-label="跟进状态"
                  value={planForm.stage}
                  onChange={event => updatePlan('stage', event.target.value as TrackingStageValue)}
                  className="select w-full"
                >
                  {TRACKING_STAGE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">提醒时间</span>
                <input
                  aria-label="提醒时间"
                  value={planForm.remind_at}
                  onChange={event => updatePlan('remind_at', event.target.value)}
                  className="input w-full"
                />
              </label>

              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-medium text-slate-700">下一步动作</span>
                <input
                  aria-label="下一步动作"
                  value={planForm.next_action}
                  onChange={event => {
                    updatePlan('next_action', event.target.value)
                    setQuickStartAction(event.target.value || DEFAULT_NEXT_ACTION)
                  }}
                  className="input w-full"
                />
              </label>

              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-medium text-slate-700">跟进备注</span>
                <textarea
                  aria-label="跟进备注"
                  value={planForm.notes}
                  onChange={event => updatePlan('notes', event.target.value)}
                  className="input min-h-24 w-full py-3"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">阻塞原因</span>
                <input
                  aria-label="阻塞原因"
                  value={planForm.block_reason}
                  onChange={event => updatePlan('block_reason', event.target.value)}
                  className="input w-full"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">放弃原因</span>
                <input
                  aria-label="放弃原因"
                  value={planForm.abandon_reason}
                  onChange={event => updatePlan('abandon_reason', event.target.value)}
                  className="input w-full"
                />
              </label>
            </div>

            <button
              type="button"
              data-testid="detail-save-plan-button"
              onClick={() => {
                void handleSavePlan()
              }}
              className="btn btn-primary mt-5"
            >
              保存跟进计划
            </button>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-950">机会信息</h2>
            <div className="mt-4 grid gap-4">
              {activity.description && (
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-sm text-slate-500">详细描述</div>
                  <div
                    data-testid="activity-description"
                    className="mt-2 break-words text-sm leading-7 text-slate-700"
                  >
                    {activity.description}
                  </div>
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">机会类型</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {CATEGORY_LABELS[activity.category] ?? activity.category}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">来源链接</div>
                  <a
                    href={activity.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex break-all text-sm font-medium text-primary-700 hover:text-primary-800"
                  >
                    {activity.url}
                  </a>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">奖金信息</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{formatPrize(activity.prize)}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">标签</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(activity.tags ?? []).length > 0 ? (
                      activity.tags.map(tag => (
                        <span key={tag} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">
                          {tag}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">暂无标签</span>
                    )}
                  </div>
                </div>
                {activity.organizer && (
                  <div className="rounded-2xl border border-slate-200 p-4">
                    <div className="text-sm text-slate-500">主办方</div>
                    <div className="mt-1 text-sm font-medium text-slate-900">{activity.organizer}</div>
                  </div>
                )}
                {activity.location && (
                  <div className="rounded-2xl border border-slate-200 p-4">
                    <div className="text-sm text-slate-500">地点</div>
                    <div className="mt-1 text-sm font-medium text-slate-900">{activity.location}</div>
                  </div>
                )}
                <div className="rounded-2xl border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">创建时间</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{formatDateTime(activity.created_at)}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">更新时间</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{formatDateTime(activity.updated_at)}</div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

export default ActivityDetailPage
