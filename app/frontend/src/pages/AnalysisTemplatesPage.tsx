import { useState } from 'react'
import { ErrorMessage } from '../components/ErrorMessage'
import { Loading } from '../components/Loading'
import { useAnalysisTemplates } from '../hooks/useAnalysisTemplates'
import { api } from '../services/api'
import type {
  AnalysisCondition,
  AnalysisLayer,
  AnalysisTemplate,
  AnalysisTemplatePreview,
} from '../types'
import {
  getAnalysisTagLabel,
  getAnalysisModeLabel,
  getAnalysisOperatorLabel,
  getAnalysisStrictnessLabel,
  localizeAnalysisTemplate,
} from '../utils/analysisI18n'

interface TemplateEditorState {
  description: string
  tags: string
  sortFields: string
  preferenceProfile: 'money_first' | 'trusted_sources' | 'solo_friendly'
  riskTolerance: 'assertive' | 'balanced' | 'cautious'
  researchMode: 'minimal' | 'layered' | 'deep_dive'
  layers: AnalysisLayer[]
}

type TemplatePreferenceProfile = TemplateEditorState['preferenceProfile']
type TemplateRiskTolerance = TemplateEditorState['riskTolerance']
type TemplateResearchMode = TemplateEditorState['researchMode']
type AnalysisTemplateWithPreferences = AnalysisTemplate & {
  preference_profile?: TemplatePreferenceProfile | null
  risk_tolerance?: TemplateRiskTolerance | null
  research_mode?: TemplateResearchMode | null
}

interface DeleteImpactState {
  templateId: string
  message: string
  replacementTemplate: AnalysisTemplate | null
  preview: AnalysisTemplatePreview | null
  error: string | null
}

function toCsv(values: string[]) {
  return values.join(', ')
}

function parseCsv(value: string) {
  return value
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function cloneConditions(conditions: AnalysisCondition[]) {
  return conditions.map(condition => ({ ...condition }))
}

function cloneLayers(layers: AnalysisLayer[]) {
  return layers.map(layer => ({
    ...layer,
    conditions: cloneConditions(layer.conditions ?? []),
  }))
}

function stringifyConditionValue(value: AnalysisCondition['value']) {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}

function parseConditionValue(value: string): string | number | boolean | null {
  const normalized = value.trim()
  if (!normalized) {
    return null
  }
  if (normalized === 'true') return true
  if (normalized === 'false') return false
  if (normalized === 'null') return null
  if (/^-?\d+(\.\d+)?$/.test(normalized)) return Number(normalized)
  return normalized
}

const PREFERENCE_PROFILE_LABELS: Record<TemplatePreferenceProfile, string> = {
  money_first: 'Money first',
  trusted_sources: 'Trusted sources',
  solo_friendly: 'Solo friendly',
}

const RISK_TOLERANCE_LABELS: Record<TemplateRiskTolerance, string> = {
  assertive: 'Assertive',
  balanced: 'Balanced',
  cautious: 'Cautious',
}

const RESEARCH_MODE_LABELS: Record<TemplateResearchMode, string> = {
  minimal: 'Minimal',
  layered: 'Layered',
  deep_dive: 'Deep dive',
}

function deriveTemplatePreferences(template: AnalysisTemplate): Pick<
  TemplateEditorState,
  'preferenceProfile' | 'riskTolerance' | 'researchMode'
> {
  const typedTemplate = template as AnalysisTemplateWithPreferences
  const slug = template.slug.toLowerCase()
  const tags = new Set(template.tags)

  const preferenceProfile =
    typedTemplate.preference_profile ??
    (slug.includes('safe') || slug.includes('trust') || tags.has('trust')
      ? 'trusted_sources'
      : tags.has('solo')
        ? 'solo_friendly'
        : 'money_first')

  const riskTolerance =
    typedTemplate.risk_tolerance ??
    (slug.includes('safe') || tags.has('safe') || tags.has('trusted')
      ? 'cautious'
      : slug.includes('quick') || tags.has('roi')
        ? 'assertive'
        : 'balanced')

  const researchMode =
    typedTemplate.research_mode ??
    (slug.includes('safe') || slug.includes('trust') || tags.has('trust') ? 'layered' : 'minimal')

  return {
    preferenceProfile,
    riskTolerance,
    researchMode,
  }
}

function buildEditorState(template: AnalysisTemplate): TemplateEditorState {
  const localizedTemplate = localizeAnalysisTemplate(template)
  const preferences = deriveTemplatePreferences(localizedTemplate)
  return {
    description: localizedTemplate.description ?? '',
    tags: toCsv(localizedTemplate.tags),
    sortFields: toCsv(localizedTemplate.sort_fields),
    preferenceProfile: preferences.preferenceProfile,
    riskTolerance: preferences.riskTolerance,
    researchMode: preferences.researchMode,
    layers: cloneLayers(localizedTemplate.layers),
  }
}

function createEmptyLayer(index: number): AnalysisLayer {
  return {
    key: `layer-${index + 1}`,
    label: `规则层 ${index + 1}`,
    enabled: true,
    mode: 'filter',
    conditions: [],
  }
}

function createEmptyCondition(): AnalysisCondition {
  return {
    key: '',
    label: '',
    enabled: true,
    operator: 'eq',
    value: null,
    weight: null,
    hard_fail: false,
    strictness: 'medium',
  }
}

export function AnalysisTemplatesPage() {
  const {
    templates,
    defaultTemplate,
    loading,
    error,
    createTemplate,
    duplicateTemplate,
    activateTemplate,
    updateTemplate,
    renameTemplate,
    deleteTemplate,
    refetch,
  } = useAnalysisTemplates()
  const [rerunFeedback, setRerunFeedback] = useState<string | null>(null)
  const [rerunLoading, setRerunLoading] = useState(false)
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null)
  const [previewByTemplate, setPreviewByTemplate] = useState<Record<string, AnalysisTemplatePreview>>({})
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null)
  const [editorState, setEditorState] = useState<TemplateEditorState | null>(null)
  const [editorError, setEditorError] = useState<string | null>(null)
  const [deleteImpact, setDeleteImpact] = useState<DeleteImpactState | null>(null)
  const [deleteImpactLoadingId, setDeleteImpactLoadingId] = useState<string | null>(null)
  const localizedTemplates = templates.map(template => localizeAnalysisTemplate(template))
  const localizedDefaultTemplate = defaultTemplate ? localizeAnalysisTemplate(defaultTemplate) : null

  function updateEditorState(updater: (current: TemplateEditorState) => TemplateEditorState) {
    setEditorState(current => (current ? updater(current) : current))
  }

  function hasUnsavedChanges(template: AnalysisTemplate) {
    if (editingTemplateId !== template.id || !editorState) {
      return false
    }

    return JSON.stringify(editorState) !== JSON.stringify(buildEditorState(template))
  }

  async function handleRerunAnalysis() {
    setRerunLoading(true)
    setRerunFeedback(null)
    try {
      const result = await api.runAnalysis()
      setRerunFeedback(`已重新分析 ${result.processed} 条机会`)
      await refetch()
    } catch (err) {
      const message = err instanceof Error ? err.message : '重新分析失败'
      setRerunFeedback(message)
    } finally {
      setRerunLoading(false)
    }
  }

  async function handlePreviewTemplate(templateId: string) {
    setPreviewLoadingId(templateId)
    try {
      const preview = await api.previewAnalysisTemplate(templateId)
      setPreviewByTemplate(current => ({ ...current, [templateId]: preview }))
    } finally {
      setPreviewLoadingId(current => (current === templateId ? null : current))
    }
  }

  function buildDraftLayers() {
    if (!editorState) {
      return []
    }

    const layerKeys = new Set<string>()

    return editorState.layers.map((layer, layerIndex) => {
      const key = layer.key.trim()
      if (!key) {
        throw new Error(`第 ${layerIndex + 1} 层缺少规则键`)
      }
      if (layerKeys.has(key)) {
        throw new Error(`规则层键重复：${key}`)
      }
      layerKeys.add(key)

      const conditionKeys = new Set<string>()

      const conditions = layer.conditions
        .filter(condition => {
          const hasKey = condition.key.trim().length > 0
          const hasLabel = condition.label.trim().length > 0
          const hasValue = stringifyConditionValue(condition.value).trim().length > 0
          return hasKey || hasLabel || hasValue
        })
        .map((condition, conditionIndex) => {
          const conditionKey = condition.key.trim()
          if (!conditionKey) {
            throw new Error(`第 ${layerIndex + 1} 层的第 ${conditionIndex + 1} 个条件缺少条件键`)
          }
          if (conditionKeys.has(conditionKey)) {
            throw new Error(`规则层 ${key} 中的条件键重复：${conditionKey}`)
          }
          conditionKeys.add(conditionKey)

          return {
            ...condition,
            key: conditionKey,
            label: condition.label.trim() || conditionKey,
            value: parseConditionValue(stringifyConditionValue(condition.value)),
            strictness: condition.strictness ?? 'medium',
            weight: condition.weight ?? null,
            hard_fail: Boolean(condition.hard_fail),
            enabled: Boolean(condition.enabled),
          }
        })

      return {
        ...layer,
        key,
        label: layer.label.trim() || key,
        mode: layer.mode || 'filter',
        enabled: Boolean(layer.enabled),
        conditions,
      }
    })
  }

  async function handlePreviewDraftTemplate(template: AnalysisTemplate) {
    if (!editorState) return

    try {
      const preview = await api.previewDraftAnalysisTemplate({
        id: `${template.id}-draft`,
        name: template.name,
        description: editorState.description.trim() || null,
        tags: parseCsv(editorState.tags),
        sort_fields: parseCsv(editorState.sortFields),
        layers: buildDraftLayers(),
      })
      setPreviewByTemplate(current => ({ ...current, [template.id]: preview }))
      setEditorError(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : '草稿预览失败'
      setEditorError(message)
    }
  }

  async function handleRenameTemplate(templateId: string, currentName: string) {
    const nextName = window.prompt('重命名模板', currentName)
    const normalizedName = nextName?.trim()
    if (!normalizedName || normalizedName === currentName) return
    await renameTemplate(templateId, normalizedName)
  }

  async function handleDuplicateTemplate(template: AnalysisTemplate) {
    const duplicated = await duplicateTemplate(template.id, `${template.name} 副本`)
    if (duplicated) {
      startEditingTemplate(localizeAnalysisTemplate(duplicated))
    }
  }

  async function handleDeleteTemplate(template: AnalysisTemplate) {
    const replacementTemplate = template.is_default
      ? localizedTemplates.find(candidate => candidate.id !== template.id) ?? null
      : localizedDefaultTemplate

    setDeleteImpactLoadingId(template.id)
    try {
      let replacementPreview: AnalysisTemplatePreview | null = null
      if (template.is_default && replacementTemplate) {
        replacementPreview = previewByTemplate[replacementTemplate.id] ?? null
        if (!replacementPreview) {
          replacementPreview = await api.previewAnalysisTemplate(replacementTemplate.id)
          setPreviewByTemplate(current => ({
            ...current,
            [replacementTemplate.id]: replacementPreview!,
          }))
        }
      }

      setDeleteImpact({
        templateId: template.id,
        replacementTemplate,
        preview: replacementPreview,
        message: template.is_default
          ? replacementTemplate
            ? `删除后会自动切换到 ${replacementTemplate.name}。`
            : '删除后将没有可用的分析模板。'
          : localizedDefaultTemplate
            ? `删除后不会影响当前默认模板 ${localizedDefaultTemplate.name}。`
            : '删除后不会影响当前机会池的默认模板。',
        error: null,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载删除影响预览失败'
      setDeleteImpact({
        templateId: template.id,
        replacementTemplate,
        preview: null,
        message: template.is_default
          ? replacementTemplate
            ? `删除后会自动切换到 ${replacementTemplate.name}。`
            : '删除后将没有可用的分析模板。'
          : localizedDefaultTemplate
            ? `删除后不会影响当前默认模板 ${localizedDefaultTemplate.name}。`
            : '删除后不会影响当前机会池的默认模板。',
        error: message,
      })
    } finally {
      setDeleteImpactLoadingId(current => (current === template.id ? null : current))
    }
  }

  async function confirmDeleteTemplate(templateId: string) {
    const deleted = await deleteTemplate(templateId)
    if (!deleted) return
    setPreviewByTemplate(current => {
      const next = { ...current }
      delete next[templateId]
      return next
    })
    if (editingTemplateId === templateId) stopEditingTemplate()
    setDeleteImpact(current => (current?.templateId === templateId ? null : current))
  }

  async function handleCreateTemplate() {
    const nextName = window.prompt('新模板名称', '我的分析模板')
    const normalizedName = nextName?.trim()
    if (!normalizedName) return
    const created = await createTemplate(normalizedName, localizedDefaultTemplate)
    if (created) {
      startEditingTemplate(localizeAnalysisTemplate(created))
    }
  }

  async function handleSaveAsTemplate(template: AnalysisTemplate) {
    if (!editorState) return

    const nextName = window.prompt('另存为模板名称', `${template.name} 副本`)
    const normalizedName = nextName?.trim()
    if (!normalizedName) return

    try {
      const created = await createTemplate(normalizedName, {
        ...template,
        description: editorState.description.trim() || null,
        tags: parseCsv(editorState.tags),
        sort_fields: parseCsv(editorState.sortFields),
        layers: buildDraftLayers(),
      })

      if (created) {
        setEditorError(null)
        startEditingTemplate(localizeAnalysisTemplate(created))
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '模板另存失败'
      setEditorError(message)
    }
  }

  function startEditingTemplate(template: AnalysisTemplate) {
    setDeleteImpact(null)
    setEditingTemplateId(template.id)
    setEditorState(buildEditorState(template))
    setEditorError(null)
  }

  function stopEditingTemplate() {
    setDeleteImpact(null)
    setEditingTemplateId(null)
    setEditorState(null)
    setEditorError(null)
  }

  function addLayer() {
    updateEditorState(current => ({
      ...current,
      layers: [...current.layers, createEmptyLayer(current.layers.length)],
    }))
  }

  function removeLayer(layerIndex: number) {
    updateEditorState(current => ({
      ...current,
      layers: current.layers.filter((_, index) => index !== layerIndex),
    }))
  }

  function updateLayer(layerIndex: number, patch: Partial<AnalysisLayer>) {
    updateEditorState(current => ({
      ...current,
      layers: current.layers.map((layer, index) =>
        index === layerIndex ? { ...layer, ...patch } : layer
      ),
    }))
  }

  function addCondition(layerIndex: number) {
    updateEditorState(current => ({
      ...current,
      layers: current.layers.map((layer, index) =>
        index === layerIndex
          ? { ...layer, conditions: [...layer.conditions, createEmptyCondition()] }
          : layer
      ),
    }))
  }

  function removeCondition(layerIndex: number, conditionIndex: number) {
    updateEditorState(current => ({
      ...current,
      layers: current.layers.map((layer, index) =>
        index === layerIndex
          ? {
              ...layer,
              conditions: layer.conditions.filter((_, currentIndex) => currentIndex !== conditionIndex),
            }
          : layer
      ),
    }))
  }

  function updateCondition(
    layerIndex: number,
    conditionIndex: number,
    patch: Partial<AnalysisCondition>
  ) {
    updateEditorState(current => ({
      ...current,
      layers: current.layers.map((layer, index) =>
        index === layerIndex
          ? {
              ...layer,
              conditions: layer.conditions.map((condition, currentIndex) =>
                currentIndex === conditionIndex ? { ...condition, ...patch } : condition
              ),
            }
          : layer
      ),
    }))
  }

  async function handleSaveTemplate(templateId: string) {
    if (!editorState) return

    try {
      const layers = buildDraftLayers()

      const updated = await updateTemplate(templateId, {
        description: editorState.description.trim() || null,
        tags: parseCsv(editorState.tags),
        sort_fields: parseCsv(editorState.sortFields),
        layers,
      })

      if (updated) {
        const preview = await api.previewAnalysisTemplate(templateId)
        setPreviewByTemplate(current => ({ ...current, [templateId]: preview }))
        setEditorError(null)
        stopEditingTemplate()
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '模板配置保存失败'
      setEditorError(message)
    }
  }

  if (loading && templates.length === 0) {
    return <Loading text="加载分析模板中..." />
  }

  if (error && templates.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void refetch()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">模板中心</h1>
          <p className="mt-2 text-sm text-gray-600">
            管理 AI 分析模板，切换默认策略，并快速预览不同模板对当前机会池的影响。
          </p>
        </div>
        {localizedDefaultTemplate && (
          <div className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-800">
            当前默认模板: {localizedDefaultTemplate.name}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          data-testid="create-analysis-template-button"
          onClick={() => void handleCreateTemplate()}
          className="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:border-emerald-300 hover:text-emerald-900"
        >
          新建模板
        </button>
        <button
          type="button"
          data-testid="rerun-analysis-button"
          onClick={() => void handleRerunAnalysis()}
          disabled={rerunLoading}
          className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {rerunLoading ? '重新分析中...' : '重新分析全部机会'}
        </button>
        {rerunFeedback && (
          <div data-testid="analysis-rerun-feedback" className="text-sm text-slate-600">
            {rerunFeedback}
          </div>
        )}
      </div>

      {error && templates.length > 0 && <ErrorMessage message={error} onRetry={() => void refetch()} />}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {localizedTemplates.map(template => {
          const preview = previewByTemplate[template.id]
          const isEditing = editingTemplateId === template.id && editorState
          const preferences = deriveTemplatePreferences(template)

          return (
            <section key={template.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-semibold text-slate-900">{template.name}</h2>
                    {template.is_default && (
                      <span
                        data-testid={`analysis-template-default-badge-${template.id}`}
                        className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
                      >
                        默认模板
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600">{template.description || '暂无模板说明'}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {!template.is_default && (
                    <button
                      type="button"
                      data-testid={`activate-analysis-template-${template.id}`}
                      onClick={() => void activateTemplate(template.id)}
                      className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                    >
                      设为默认
                    </button>
                  )}
                  <button
                    type="button"
                    data-testid={`edit-analysis-template-${template.id}`}
                    onClick={() => startEditingTemplate(template)}
                    className="rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 transition hover:border-indigo-300 hover:text-indigo-900"
                  >
                    编辑模板
                  </button>
                  <button
                    type="button"
                    data-testid={`rename-analysis-template-${template.id}`}
                    onClick={() => void handleRenameTemplate(template.id, template.name)}
                    className="rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-700 transition hover:border-violet-300 hover:text-violet-900"
                  >
                    重命名
                  </button>
                  <button
                    type="button"
                    data-testid={`preview-analysis-template-${template.id}`}
                    onClick={() => void handlePreviewTemplate(template.id)}
                    disabled={previewLoadingId === template.id}
                    className="rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 transition hover:border-sky-300 hover:text-sky-900 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {previewLoadingId === template.id ? '预览中...' : '查看预览'}
                  </button>
                  <button
                    type="button"
                    data-testid={`duplicate-analysis-template-${template.id}`}
                    onClick={() => void handleDuplicateTemplate(template)}
                    className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900"
                  >
                    复制模板
                  </button>
                  <button
                    type="button"
                    data-testid={`delete-analysis-template-${template.id}`}
                    onClick={() => void handleDeleteTemplate(template)}
                    disabled={deleteImpactLoadingId === template.id}
                    className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 transition hover:border-rose-300 hover:text-rose-900"
                  >
                    {deleteImpactLoadingId === template.id ? '加载影响中...' : '删除模板'}
                  </button>
                </div>
              </div>

              {deleteImpact?.templateId === template.id && (
                <div
                  data-testid={`analysis-template-delete-impact-${template.id}`}
                  className="mt-4 rounded-2xl border border-rose-200 bg-rose-50/70 p-4"
                >
                  <div className="text-sm font-semibold text-rose-900">删除影响预览</div>
                  <p className="mt-2 text-sm text-rose-800">{deleteImpact.message}</p>

                  {deleteImpact.error && (
                    <p className="mt-2 text-sm text-rose-700">{deleteImpact.error}</p>
                  )}

                  {deleteImpact.replacementTemplate && (
                    <div className="mt-3 inline-flex rounded-full border border-rose-200 bg-white px-3 py-1 text-xs font-medium text-rose-700">
                      替补模板: {deleteImpact.replacementTemplate.name}
                    </div>
                  )}

                  {deleteImpact.preview && (
                    <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                      <div className="rounded-xl bg-white p-3">
                        <div className="text-xs text-slate-500">总机会</div>
                        <div className="mt-1 text-xl font-semibold text-slate-900">{deleteImpact.preview.total}</div>
                      </div>
                      <div className="rounded-xl bg-white p-3">
                        <div className="text-xs text-emerald-600">通过</div>
                        <div className="mt-1 text-xl font-semibold text-emerald-700">{deleteImpact.preview.passed}</div>
                      </div>
                      <div className="rounded-xl bg-white p-3">
                        <div className="text-xs text-amber-600">待观察</div>
                        <div className="mt-1 text-xl font-semibold text-amber-700">{deleteImpact.preview.watch}</div>
                      </div>
                      <div className="rounded-xl bg-white p-3">
                        <div className="text-xs text-rose-600">淘汰</div>
                        <div className="mt-1 text-xl font-semibold text-rose-700">{deleteImpact.preview.rejected}</div>
                      </div>
                    </div>
                  )}

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      data-testid={`confirm-delete-analysis-template-${template.id}`}
                      onClick={() => void confirmDeleteTemplate(template.id)}
                      className="rounded-full border border-rose-300 bg-rose-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-700"
                    >
                      确认删除
                    </button>
                    <button
                      type="button"
                      data-testid={`cancel-delete-analysis-template-${template.id}`}
                      onClick={() => setDeleteImpact(null)}
                      className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              <div className="mt-5 flex flex-wrap gap-2">
                {template.tags.length > 0 ? (
                  template.tags.map(tag => (
                    <span
                      key={tag}
                      className="rounded-full border border-sky-100 bg-sky-50 px-3 py-1 text-xs text-sky-700"
                    >
                      {getAnalysisTagLabel(tag)}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400">暂无标签</span>
                )}
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-slate-500">Profile</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">
                    {PREFERENCE_PROFILE_LABELS[preferences.preferenceProfile]}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-slate-500">Risk tolerance</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">
                    {RISK_TOLERANCE_LABELS[preferences.riskTolerance]}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-slate-500">Research mode</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">
                    {RESEARCH_MODE_LABELS[preferences.researchMode]}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-slate-500">层数</div>
                  <div className="mt-2 text-2xl font-semibold text-slate-900">{template.layers.length}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <div className="text-xs text-slate-500">排序字段</div>
                  <div className="mt-2 text-2xl font-semibold text-slate-900">{template.sort_fields.length}</div>
                </div>
              </div>

              {isEditing && editorState ? (
                <div
                  data-testid={`analysis-template-editor-${template.id}`}
                  className="mt-5 rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4"
                >
                  {hasUnsavedChanges(template) ? (
                    <div
                      data-testid={`analysis-template-dirty-state-${template.id}`}
                      className="mb-3 inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700"
                    >
                      未保存修改
                    </div>
                  ) : null}
                  <div className="text-sm font-semibold text-slate-900">编辑模板配置</div>
                  <div className="mt-4 grid gap-4">
                    <label className="grid gap-2 text-sm text-slate-700">
                      <span>描述</span>
                      <textarea
                        data-testid={`analysis-template-description-input-${template.id}`}
                        value={editorState.description}
                        onChange={event =>
                          updateEditorState(current => ({ ...current, description: event.target.value }))
                        }
                        rows={3}
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                      />
                    </label>

                    <label className="grid gap-2 text-sm text-slate-700">
                      <span>标签</span>
                      <input
                        data-testid={`analysis-template-tags-input-${template.id}`}
                        value={editorState.tags}
                        onChange={event =>
                          updateEditorState(current => ({ ...current, tags: event.target.value }))
                        }
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                      />
                    </label>

                    <label className="grid gap-2 text-sm text-slate-700">
                      <span>排序字段</span>
                      <input
                        data-testid={`analysis-template-sort-fields-input-${template.id}`}
                        value={editorState.sortFields}
                        onChange={event =>
                          updateEditorState(current => ({ ...current, sortFields: event.target.value }))
                        }
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                      />
                    </label>

                    <div className="rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex flex-col gap-1">
                        <div className="text-sm font-medium text-slate-900">Business preferences</div>
                        <p className="text-xs text-slate-500">
                          用业务偏好定义 agent 策略，而不是继续暴露底层模型路由。
                        </p>
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        <label className="grid gap-1 text-xs text-slate-600">
                          <span>Preference profile</span>
                          <select
                            aria-label="Preference profile"
                            data-testid={`analysis-template-preference-profile-input-${template.id}`}
                            value={editorState.preferenceProfile}
                            onChange={event =>
                              updateEditorState(current => ({
                                ...current,
                                preferenceProfile: event.target.value as TemplatePreferenceProfile,
                              }))
                            }
                            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                          >
                            <option value="money_first">Money first</option>
                            <option value="trusted_sources">Trusted sources</option>
                            <option value="solo_friendly">Solo friendly</option>
                          </select>
                        </label>

                        <label className="grid gap-1 text-xs text-slate-600">
                          <span>Risk tolerance</span>
                          <select
                            aria-label="Risk tolerance"
                            data-testid={`analysis-template-risk-tolerance-input-${template.id}`}
                            value={editorState.riskTolerance}
                            onChange={event =>
                              updateEditorState(current => ({
                                ...current,
                                riskTolerance: event.target.value as TemplateRiskTolerance,
                              }))
                            }
                            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                          >
                            <option value="assertive">Assertive</option>
                            <option value="balanced">Balanced</option>
                            <option value="cautious">Cautious</option>
                          </select>
                        </label>

                        <label className="grid gap-1 text-xs text-slate-600">
                          <span>Research mode</span>
                          <select
                            aria-label="Research mode"
                            data-testid={`analysis-template-research-mode-input-${template.id}`}
                            value={editorState.researchMode}
                            onChange={event =>
                              updateEditorState(current => ({
                                ...current,
                                researchMode: event.target.value as TemplateResearchMode,
                              }))
                            }
                            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                          >
                            <option value="minimal">Minimal</option>
                            <option value="layered">Layered</option>
                            <option value="deep_dive">Deep dive</option>
                          </select>
                        </label>
                      </div>
                    </div>

                    <div className="grid gap-3">
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-medium text-slate-900">规则层</div>
                        <button
                          type="button"
                          data-testid={`add-analysis-template-layer-${template.id}`}
                          onClick={addLayer}
                          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900"
                        >
                          添加规则层
                        </button>
                      </div>

                      {editorState.layers.map((layer, layerIndex) => (
                        <div
                          key={`${template.id}-layer-${layerIndex}`}
                          className="rounded-2xl border border-slate-200 bg-white p-4"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-sm font-medium text-slate-900">第 {layerIndex + 1} 层</div>
                            <button
                              type="button"
                              data-testid={`remove-analysis-template-layer-${template.id}-${layerIndex}`}
                              onClick={() => removeLayer(layerIndex)}
                              className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 transition hover:border-rose-300 hover:text-rose-900"
                            >
                              删除这一层
                            </button>
                          </div>

                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            <label className="grid gap-1 text-xs text-slate-600">
                              <span>规则键</span>
                              <input
                                data-testid={`analysis-template-layer-key-input-${template.id}-${layerIndex}`}
                                value={layer.key}
                                onChange={event => updateLayer(layerIndex, { key: event.target.value })}
                                className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                              />
                            </label>

                            <label className="grid gap-1 text-xs text-slate-600">
                              <span>规则名称</span>
                              <input
                                data-testid={`analysis-template-layer-label-input-${template.id}-${layerIndex}`}
                                value={layer.label}
                                onChange={event => updateLayer(layerIndex, { label: event.target.value })}
                                className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                              />
                            </label>

                            <label className="grid gap-1 text-xs text-slate-600">
                              <span>执行模式</span>
                              <select
                                data-testid={`analysis-template-layer-mode-input-${template.id}-${layerIndex}`}
                                value={layer.mode}
                                onChange={event => updateLayer(layerIndex, { mode: event.target.value })}
                                className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                              >
                                <option value="filter">{getAnalysisModeLabel('filter')}</option>
                                <option value="rank">{getAnalysisModeLabel('rank')}</option>
                              </select>
                            </label>

                            <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700">
                              <input
                                type="checkbox"
                                data-testid={`analysis-template-layer-enabled-input-${template.id}-${layerIndex}`}
                                checked={layer.enabled}
                                onChange={event => updateLayer(layerIndex, { enabled: event.target.checked })}
                              />
                              启用这一层
                            </label>
                          </div>

                          <div className="mt-4 grid gap-3">
                            <div className="flex items-center justify-between">
                              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                条件列表
                              </div>
                              <button
                                type="button"
                                data-testid={`add-analysis-template-condition-${template.id}-${layerIndex}`}
                                onClick={() => addCondition(layerIndex)}
                                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900"
                              >
                                添加条件
                              </button>
                            </div>

                            {layer.conditions.map((condition, conditionIndex) => (
                              <div
                                key={`${template.id}-layer-${layerIndex}-condition-${conditionIndex}`}
                                className="rounded-2xl border border-slate-200 bg-slate-50 p-3"
                              >
                                <div className="flex justify-end">
                                  <button
                                    type="button"
                                    data-testid={`remove-analysis-template-condition-${template.id}-${layerIndex}-${conditionIndex}`}
                                    onClick={() => removeCondition(layerIndex, conditionIndex)}
                                    className="rounded-full border border-rose-200 bg-white px-3 py-1 text-xs font-medium text-rose-700 transition hover:border-rose-300 hover:text-rose-900"
                                  >
                                    删除条件
                                  </button>
                                </div>

                                <div className="mt-3 grid gap-3 md:grid-cols-2">
                                  <label className="grid gap-1 text-xs text-slate-600">
                                    <span>条件键</span>
                                    <input
                                      data-testid={`analysis-template-condition-key-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      value={condition.key}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, { key: event.target.value })
                                      }
                                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                                    />
                                  </label>

                                  <label className="grid gap-1 text-xs text-slate-600">
                                    <span>条件名称</span>
                                    <input
                                      data-testid={`analysis-template-condition-label-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      value={condition.label}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, { label: event.target.value })
                                      }
                                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                                    />
                                  </label>

                                  <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700">
                                    <input
                                      type="checkbox"
                                      data-testid={`analysis-template-condition-enabled-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      checked={condition.enabled}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, {
                                          enabled: event.target.checked,
                                        })
                                      }
                                    />
                                    启用条件
                                  </label>

                                  <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700">
                                    <input
                                      type="checkbox"
                                      data-testid={`analysis-template-condition-hard-fail-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      checked={Boolean(condition.hard_fail)}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, {
                                          hard_fail: event.target.checked,
                                        })
                                      }
                                    />
                                    硬性淘汰
                                  </label>

                                  <label className="grid gap-1 text-xs text-slate-600">
                                    <span>运算符</span>
                                    <select
                                      data-testid={`analysis-template-condition-operator-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      value={condition.operator}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, { operator: event.target.value })
                                      }
                                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                                    >
                                      <option value="eq">{getAnalysisOperatorLabel('eq')}</option>
                                      <option value="neq">{getAnalysisOperatorLabel('neq')}</option>
                                      <option value="gte">{getAnalysisOperatorLabel('gte')}</option>
                                      <option value="lte">{getAnalysisOperatorLabel('lte')}</option>
                                      <option value="gt">{getAnalysisOperatorLabel('gt')}</option>
                                      <option value="lt">{getAnalysisOperatorLabel('lt')}</option>
                                    </select>
                                  </label>

                                  <label className="grid gap-1 text-xs text-slate-600">
                                    <span>严格度</span>
                                    <select
                                      data-testid={`analysis-template-condition-strictness-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      value={condition.strictness ?? 'medium'}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, {
                                          strictness: event.target.value as AnalysisCondition['strictness'],
                                        })
                                      }
                                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                                    >
                                      <option value="strict">{getAnalysisStrictnessLabel('strict')}</option>
                                      <option value="medium">{getAnalysisStrictnessLabel('medium')}</option>
                                      <option value="relaxed">{getAnalysisStrictnessLabel('relaxed')}</option>
                                    </select>
                                  </label>

                                  <label className="grid gap-1 text-xs text-slate-600">
                                    <span>条件值</span>
                                    <input
                                      data-testid={`analysis-template-condition-value-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      value={stringifyConditionValue(condition.value)}
                                      onChange={event =>
                                        updateCondition(layerIndex, conditionIndex, { value: event.target.value })
                                      }
                                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                                    />
                                  </label>

                                  <label className="grid gap-1 text-xs text-slate-600">
                                    <span>权重</span>
                                    <input
                                      data-testid={`analysis-template-condition-weight-input-${template.id}-${layerIndex}-${conditionIndex}`}
                                      value={condition.weight ?? ''}
                                      onChange={event => {
                                        const rawValue = event.target.value.trim()
                                        const nextWeight = Number(rawValue)
                                        updateCondition(layerIndex, conditionIndex, {
                                          weight:
                                            rawValue && Number.isFinite(nextWeight) ? nextWeight : null,
                                        })
                                      }}
                                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
                                    />
                                  </label>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {editorError && (
                    <div
                      data-testid={`analysis-template-editor-error-${template.id}`}
                      className="mt-3 text-sm text-rose-600"
                    >
                      {editorError}
                    </div>
                  )}

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      data-testid={`preview-draft-analysis-template-${template.id}`}
                      onClick={() => void handlePreviewDraftTemplate(template)}
                      className="rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 transition hover:border-sky-300 hover:bg-sky-100"
                    >
                      预览草稿
                    </button>
                    <button
                      type="button"
                      data-testid={`save-analysis-template-${template.id}`}
                      onClick={() => void handleSaveTemplate(template.id)}
                      className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                    >
                      保存修改
                    </button>
                    <button
                      type="button"
                      data-testid={`save-as-analysis-template-${template.id}`}
                      onClick={() => void handleSaveAsTemplate(template)}
                      className="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-100"
                    >
                      另存为新模板
                    </button>
                    <button
                      type="button"
                      data-testid={`cancel-analysis-template-${template.id}`}
                      onClick={stopEditingTemplate}
                      className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900"
                    >
                      取消
                    </button>
                  </div>
                </div>
              ) : null}

              {preview && (
                <div
                  data-testid={`analysis-template-preview-${template.id}`}
                  className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="text-xs font-medium uppercase tracking-wide text-slate-500">预览结果</div>
                  <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                    <div className="rounded-xl bg-white p-3">
                      <div className="text-xs text-slate-500">总机会</div>
                      <div className="mt-1 text-xl font-semibold text-slate-900">{preview.total}</div>
                    </div>
                    <div className="rounded-xl bg-white p-3">
                      <div className="text-xs text-emerald-600">通过</div>
                      <div className="mt-1 text-xl font-semibold text-emerald-700">{preview.passed}</div>
                    </div>
                    <div className="rounded-xl bg-white p-3">
                      <div className="text-xs text-amber-600">待观察</div>
                      <div className="mt-1 text-xl font-semibold text-amber-700">{preview.watch}</div>
                    </div>
                    <div className="rounded-xl bg-white p-3">
                      <div className="text-xs text-rose-600">淘汰</div>
                      <div className="mt-1 text-xl font-semibold text-rose-700">{preview.rejected}</div>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )
        })}
      </div>
    </div>
  )
}

export default AnalysisTemplatesPage
