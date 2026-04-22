import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { AnalysisTemplate, AnalysisTemplateUpdateRequest } from '../types'

interface UseAnalysisTemplatesResult {
  templates: AnalysisTemplate[]
  defaultTemplate: AnalysisTemplate | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  createTemplate: (
    name: string,
    sourceTemplate?: AnalysisTemplate | null
  ) => Promise<AnalysisTemplate | null>
  duplicateTemplate: (templateId: string, name: string) => Promise<AnalysisTemplate | null>
  activateTemplate: (templateId: string) => Promise<AnalysisTemplate | null>
  updateTemplate: (
    templateId: string,
    payload: AnalysisTemplateUpdateRequest
  ) => Promise<AnalysisTemplate | null>
  renameTemplate: (templateId: string, name: string) => Promise<AnalysisTemplate | null>
  deleteTemplate: (templateId: string) => Promise<boolean>
}

export function useAnalysisTemplates(): UseAnalysisTemplatesResult {
  const [templates, setTemplates] = useState<AnalysisTemplate[]>([])
  const [defaultTemplate, setDefaultTemplate] = useState<AnalysisTemplate | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [templateList, currentDefault] = await Promise.all([
        api.getAnalysisTemplates(),
        api.getDefaultAnalysisTemplate(),
      ])
      setTemplates(templateList)
      setDefaultTemplate(currentDefault)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load analysis templates'
      setError(message)
      setTemplates([])
      setDefaultTemplate(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const createTemplate = useCallback(
    async (name: string, sourceTemplate?: AnalysisTemplate | null): Promise<AnalysisTemplate | null> => {
      setError(null)
      try {
        const created = await api.createAnalysisTemplate({
          name,
          description: sourceTemplate?.description ?? null,
          tags: sourceTemplate?.tags ?? [],
          layers: sourceTemplate?.layers ?? [],
          sort_fields: sourceTemplate?.sort_fields ?? [],
          is_default: false,
        })
        await refresh()
        return created
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create analysis template'
        setError(message)
        return null
      }
    },
    [refresh]
  )

  const duplicateTemplate = useCallback(
    async (templateId: string, name: string): Promise<AnalysisTemplate | null> => {
      setError(null)
      try {
        const duplicated = await api.duplicateAnalysisTemplate(templateId, name)
        await refresh()
        return duplicated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to duplicate analysis template'
        setError(message)
        return null
      }
    },
    [refresh]
  )

  const activateTemplate = useCallback(
    async (templateId: string): Promise<AnalysisTemplate | null> => {
      setError(null)
      try {
        const activated = await api.activateAnalysisTemplate(templateId)
        await refresh()
        return activated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to activate analysis template'
        setError(message)
        return null
      }
    },
    [refresh]
  )

  const updateTemplate = useCallback(
    async (
      templateId: string,
      payload: AnalysisTemplateUpdateRequest
    ): Promise<AnalysisTemplate | null> => {
      setError(null)
      try {
        const updated = await api.updateAnalysisTemplate(templateId, payload)
        await refresh()
        return updated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update analysis template'
        setError(message)
        return null
      }
    },
    [refresh]
  )

  const renameTemplate = useCallback(
    async (templateId: string, name: string): Promise<AnalysisTemplate | null> => {
      const updated = await updateTemplate(templateId, { name })
      if (!updated) {
        setError(prev => prev ?? 'Failed to rename analysis template')
      }
      return updated
    },
    [updateTemplate]
  )

  const deleteTemplate = useCallback(
    async (templateId: string): Promise<boolean> => {
      setError(null)
      try {
        await api.deleteAnalysisTemplate(templateId)
        await refresh()
        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete analysis template'
        setError(message)
        return false
      }
    },
    [refresh]
  )

  return {
    templates,
    defaultTemplate,
    loading,
    error,
    refetch: refresh,
    createTemplate,
    duplicateTemplate,
    activateTemplate,
    updateTemplate,
    renameTemplate,
    deleteTemplate,
  }
}

export default useAnalysisTemplates
