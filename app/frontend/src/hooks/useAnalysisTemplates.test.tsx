import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAnalysisTemplates } from './useAnalysisTemplates'

const apiMocks = vi.hoisted(() => ({
  getAnalysisTemplates: vi.fn(),
  getDefaultAnalysisTemplate: vi.fn(),
  createAnalysisTemplate: vi.fn(),
  duplicateAnalysisTemplate: vi.fn(),
  activateAnalysisTemplate: vi.fn(),
  updateAnalysisTemplate: vi.fn(),
  deleteAnalysisTemplate: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

describe('useAnalysisTemplates', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads templates and current default on mount', async () => {
    apiMocks.getAnalysisTemplates.mockResolvedValue([{ id: 'tpl-1', slug: 'quick-money' }])
    apiMocks.getDefaultAnalysisTemplate.mockResolvedValue({ id: 'tpl-1', slug: 'quick-money' })

    const { result } = renderHook(() => useAnalysisTemplates())

    await waitFor(() => {
      expect(result.current.templates[0]?.id).toBe('tpl-1')
    })

    expect(result.current.defaultTemplate?.slug).toBe('quick-money')
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('duplicates and activates templates through the API', async () => {
    apiMocks.getAnalysisTemplates
      .mockResolvedValueOnce([{ id: 'tpl-1', slug: 'quick-money' }])
      .mockResolvedValueOnce([
        { id: 'tpl-1', slug: 'quick-money' },
        { id: 'tpl-2', slug: 'quick-money-copy' },
      ])
      .mockResolvedValueOnce([
        { id: 'tpl-1', slug: 'quick-money' },
        { id: 'tpl-2', slug: 'quick-money-copy', is_default: true },
      ])
    apiMocks.getDefaultAnalysisTemplate
      .mockResolvedValueOnce({ id: 'tpl-1', slug: 'quick-money' })
      .mockResolvedValueOnce({ id: 'tpl-1', slug: 'quick-money' })
      .mockResolvedValueOnce({ id: 'tpl-2', slug: 'quick-money-copy', is_default: true })
    apiMocks.duplicateAnalysisTemplate.mockResolvedValue({
      id: 'tpl-2',
      slug: 'quick-money-copy',
    })
    apiMocks.activateAnalysisTemplate.mockResolvedValue({
      id: 'tpl-2',
      slug: 'quick-money-copy',
      is_default: true,
    })

    const { result } = renderHook(() => useAnalysisTemplates())

    await waitFor(() => {
      expect(result.current.templates).toHaveLength(1)
    })

    await act(async () => {
      await result.current.duplicateTemplate('tpl-1', 'Quick money copy')
    })
    await act(async () => {
      await result.current.activateTemplate('tpl-2')
    })

    await waitFor(() => {
      expect(result.current.defaultTemplate?.id).toBe('tpl-2')
    })

    expect(apiMocks.duplicateAnalysisTemplate).toHaveBeenCalledWith('tpl-1', 'Quick money copy')
    expect(apiMocks.activateAnalysisTemplate).toHaveBeenCalledWith('tpl-2')
  })

  it('creates templates by copying the current default settings', async () => {
    const defaultTemplate = {
      id: 'tpl-1',
      slug: 'quick-money',
      name: 'Quick money',
      description: 'Fast ROI first',
      tags: ['roi'],
      layers: [{ key: 'hard-gate', label: 'Hard gate', enabled: true, mode: 'filter', conditions: [] }],
      sort_fields: ['roi_score'],
    }
    apiMocks.getAnalysisTemplates
      .mockResolvedValueOnce([{ id: 'tpl-1', slug: 'quick-money' }])
      .mockResolvedValueOnce([
        { id: 'tpl-1', slug: 'quick-money' },
        { id: 'tpl-3', slug: 'alpha-template' },
      ])
    apiMocks.getDefaultAnalysisTemplate
      .mockResolvedValueOnce(defaultTemplate)
      .mockResolvedValueOnce(defaultTemplate)
    apiMocks.createAnalysisTemplate.mockResolvedValue({
      id: 'tpl-3',
      slug: 'alpha-template',
      name: 'Alpha template',
    })

    const { result } = renderHook(() => useAnalysisTemplates())

    await waitFor(() => {
      expect(result.current.defaultTemplate?.id).toBe('tpl-1')
    })

    await act(async () => {
      await result.current.createTemplate('Alpha template', result.current.defaultTemplate)
    })

    expect(apiMocks.createAnalysisTemplate).toHaveBeenCalledWith({
      name: 'Alpha template',
      description: 'Fast ROI first',
      tags: ['roi'],
      layers: [{ key: 'hard-gate', label: 'Hard gate', enabled: true, mode: 'filter', conditions: [] }],
      sort_fields: ['roi_score'],
      is_default: false,
    })
  })

  it('updates template fields through the API', async () => {
    const updatedTemplate = {
      id: 'tpl-2',
      slug: 'safe-trust',
      name: 'Safe trust',
      description: 'Prefer trusted and solo-friendly sources',
      tags: ['trust', 'solo'],
      layers: [{ key: 'trust', label: 'Trust', enabled: true, mode: 'filter', conditions: [] }],
      sort_fields: ['trust_score', 'roi_score'],
    }
    apiMocks.getAnalysisTemplates
      .mockResolvedValueOnce([{ id: 'tpl-2', slug: 'safe-trust' }])
      .mockResolvedValueOnce([{ id: 'tpl-2', slug: 'safe-trust', description: updatedTemplate.description }])
    apiMocks.getDefaultAnalysisTemplate
      .mockResolvedValueOnce({ id: 'tpl-2', slug: 'safe-trust' })
      .mockResolvedValueOnce({ id: 'tpl-2', slug: 'safe-trust' })
    apiMocks.updateAnalysisTemplate.mockResolvedValue(updatedTemplate)

    const { result } = renderHook(() => useAnalysisTemplates())

    await waitFor(() => {
      expect(result.current.templates[0]?.id).toBe('tpl-2')
    })

    await act(async () => {
      await result.current.updateTemplate('tpl-2', {
        description: updatedTemplate.description,
        tags: updatedTemplate.tags,
        layers: updatedTemplate.layers,
        sort_fields: updatedTemplate.sort_fields,
      })
    })

    expect(apiMocks.updateAnalysisTemplate).toHaveBeenCalledWith('tpl-2', {
      description: updatedTemplate.description,
      tags: updatedTemplate.tags,
      layers: updatedTemplate.layers,
      sort_fields: updatedTemplate.sort_fields,
    })
  })
})
