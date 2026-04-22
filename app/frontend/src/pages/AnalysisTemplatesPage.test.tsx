import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalysisTemplatesPage from './AnalysisTemplatesPage'

const apiMocks = vi.hoisted(() => ({
  runAnalysis: vi.fn(),
  previewAnalysisTemplate: vi.fn(),
  previewDraftAnalysisTemplate: vi.fn(),
}))

const analysisTemplateHookState = vi.hoisted(() => ({
  current: null as any,
}))

function buildAnalysisTemplateHookState() {
  return {
    templates: [
      {
        id: 'tpl-1',
        slug: 'quick-money',
        name: 'Quick money',
        description: 'Fast ROI first',
        is_default: true,
      tags: ['roi', 'solo'],
      layers: [{ key: 'hard-gates', label: 'Hard gates', enabled: true, mode: 'filter', conditions: [] }],
        sort_fields: ['roi_score'],
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      },
      {
        id: 'tpl-2',
        slug: 'safe-trust',
        name: 'Safe trust',
        description: 'Prefer trusted sources',
        is_default: false,
        tags: ['trust'],
        layers: [{ key: 'trust', label: 'Trust', enabled: true, mode: 'filter', conditions: [] }],
        sort_fields: ['trust_score'],
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      },
    ],
    defaultTemplate: {
      id: 'tpl-1',
      slug: 'quick-money',
      name: 'Quick money',
      description: 'Fast ROI first',
      is_default: true,
      tags: ['roi', 'solo'],
      layers: [{ key: 'hard-gates', label: 'Hard gates', enabled: true, mode: 'filter', conditions: [] }],
      sort_fields: ['roi_score'],
      created_at: '2026-03-23T08:00:00Z',
      updated_at: '2026-03-23T08:00:00Z',
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
    createTemplate: vi.fn(),
    duplicateTemplate: vi.fn(),
    activateTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    renameTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  }
}

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

describe('AnalysisTemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    analysisTemplateHookState.current = buildAnalysisTemplateHookState()
    apiMocks.runAnalysis.mockResolvedValue({ success: true, processed: 12 })
    apiMocks.previewAnalysisTemplate.mockResolvedValue({
      template_id: 'tpl-2',
      total: 12,
      passed: 5,
      watch: 4,
      rejected: 3,
    })
    apiMocks.previewDraftAnalysisTemplate.mockResolvedValue({
      template_id: 'tpl-2-draft',
      total: 10,
      passed: 4,
      watch: 3,
      rejected: 3,
    })
  })

  it('renders templates and supports activate actions', () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    expect(screen.getByText('快钱优先')).toBeInTheDocument()
    expect(screen.getByText('稳妥可信')).toBeInTheDocument()
    expect(screen.getByText('高回报')).toBeInTheDocument()
    expect(screen.getByText('可信度')).toBeInTheDocument()
    expect(screen.getByTestId('analysis-template-default-badge-tpl-1')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('activate-analysis-template-tpl-2'))
    expect(analysisTemplateHookState.current.activateTemplate).toHaveBeenCalledWith('tpl-2')
  })

  it('opens a duplicated template directly in the editor', async () => {
    analysisTemplateHookState.current.duplicateTemplate.mockImplementation(async (templateId: string, name: string) => {
      const source = analysisTemplateHookState.current.templates.find(
        (template: { id: string }) => template.id === templateId
      )!
      const created = {
        ...source,
        id: 'tpl-3',
        slug: 'quick-money-copy',
        name,
        is_default: false,
      }
      analysisTemplateHookState.current.templates = [...analysisTemplateHookState.current.templates, created]
      return created
    })

    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('duplicate-analysis-template-tpl-1'))

    await waitFor(() => {
      expect(analysisTemplateHookState.current.duplicateTemplate).toHaveBeenCalledWith(
        'tpl-1',
        '快钱优先 副本'
      )
    })
    expect(await screen.findByTestId('analysis-template-editor-tpl-3')).toBeInTheDocument()
  })

  it('can rerun analysis for all activities from the template center', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('rerun-analysis-button'))

    expect(apiMocks.runAnalysis).toHaveBeenCalledTimes(1)
    expect(await screen.findByTestId('analysis-rerun-feedback')).toHaveTextContent('12')
  })

  it('can preview how a template would classify current activities', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('preview-analysis-template-tpl-2'))

    await waitFor(() => {
      expect(apiMocks.previewAnalysisTemplate).toHaveBeenCalledWith('tpl-2')
    })
    expect(await screen.findByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('12')
    expect(screen.getByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('5')
    expect(screen.getByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('4')
    expect(screen.getByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('3')
  })

  it('supports rename actions', () => {
    vi.spyOn(window, 'prompt').mockReturnValue('Safe trust v2')

    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('rename-analysis-template-tpl-2'))

    expect(analysisTemplateHookState.current.renameTemplate).toHaveBeenCalledWith(
      'tpl-2',
      'Safe trust v2'
    )
  })

  it('shows delete impact before removing the current default template', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('delete-analysis-template-tpl-1'))

    await waitFor(() => {
      expect(apiMocks.previewAnalysisTemplate).toHaveBeenCalledWith('tpl-2')
    })
    expect(await screen.findByTestId('analysis-template-delete-impact-tpl-1')).toHaveTextContent('稳妥可信')
    expect(screen.getByTestId('analysis-template-delete-impact-tpl-1')).toHaveTextContent('12')

    fireEvent.click(screen.getByTestId('confirm-delete-analysis-template-tpl-1'))

    await waitFor(() => {
      expect(analysisTemplateHookState.current.deleteTemplate).toHaveBeenCalledWith('tpl-1')
    })
  })

  it('creates a template from the current default strategy and opens it for editing', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('Alpha template')
    analysisTemplateHookState.current.createTemplate.mockImplementation(
      async (name: string, sourceTemplate?: (typeof analysisTemplateHookState.current.templates)[number] | null) => {
        const created = {
          ...(sourceTemplate ?? analysisTemplateHookState.current.defaultTemplate!),
          id: 'tpl-3',
          slug: 'alpha-template',
          name,
          is_default: false,
        }
        analysisTemplateHookState.current.templates = [
          ...analysisTemplateHookState.current.templates,
          created,
        ]
        return created
      }
    )

    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('create-analysis-template-button'))

    expect(analysisTemplateHookState.current.createTemplate).toHaveBeenCalledWith(
      'Alpha template',
      expect.objectContaining({
        id: 'tpl-1',
        name: '快钱优先',
        description: '优先高回报、快决策的机会',
        layers: [expect.objectContaining({ key: 'hard-gates', label: '硬门槛' })],
      })
    )
    expect(await screen.findByTestId('analysis-template-editor-tpl-3')).toBeInTheDocument()
    expect(screen.getByTestId('analysis-template-description-input-tpl-3')).toHaveValue('优先高回报、快决策的机会')
  })

  it('supports editing template fields and saving them', () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))

    fireEvent.change(screen.getByTestId('analysis-template-description-input-tpl-2'), {
      target: { value: 'Prefer trusted and solo-friendly sources' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-tags-input-tpl-2'), {
      target: { value: 'trust, solo' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-sort-fields-input-tpl-2'), {
      target: { value: 'trust_score, roi_score' },
    })
    fireEvent.click(screen.getByTestId('add-analysis-template-condition-tpl-2-0'))
    fireEvent.change(screen.getByTestId('analysis-template-condition-key-input-tpl-2-0-0'), {
      target: { value: 'source_trust' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-label-input-tpl-2-0-0'), {
      target: { value: 'Source trust' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-operator-input-tpl-2-0-0'), {
      target: { value: 'gte' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-value-input-tpl-2-0-0'), {
      target: { value: 'high' },
    })
    fireEvent.click(screen.getByTestId('analysis-template-condition-enabled-input-tpl-2-0-0'))
    fireEvent.click(screen.getByTestId('analysis-template-condition-hard-fail-input-tpl-2-0-0'))
    fireEvent.change(screen.getByTestId('analysis-template-condition-strictness-input-tpl-2-0-0'), {
      target: { value: 'strict' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-weight-input-tpl-2-0-0'), {
      target: { value: '2.5' },
    })
    fireEvent.click(screen.getByTestId('add-analysis-template-layer-tpl-2'))
    fireEvent.change(screen.getByTestId('analysis-template-layer-key-input-tpl-2-1'), {
      target: { value: 'priority' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-layer-label-input-tpl-2-1'), {
      target: { value: 'Priority' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-layer-mode-input-tpl-2-1'), {
      target: { value: 'rank' },
    })

    fireEvent.click(screen.getByTestId('save-analysis-template-tpl-2'))

    expect(analysisTemplateHookState.current.updateTemplate).toHaveBeenCalledWith('tpl-2', {
      description: 'Prefer trusted and solo-friendly sources',
      tags: ['trust', 'solo'],
      sort_fields: ['trust_score', 'roi_score'],
      layers: [
        {
          key: 'trust',
          label: '可信度',
          enabled: true,
          mode: 'filter',
          conditions: [
            {
              key: 'source_trust',
              label: 'Source trust',
              enabled: false,
              operator: 'gte',
              value: 'high',
              weight: 2.5,
              hard_fail: true,
              strictness: 'strict',
            },
          ],
        },
        { key: 'priority', label: 'Priority', enabled: true, mode: 'rank', conditions: [] },
      ],
    })
  })

  it('blocks saving when layer keys are duplicated', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))
    fireEvent.click(screen.getByTestId('add-analysis-template-layer-tpl-2'))
    fireEvent.change(screen.getByTestId('analysis-template-layer-key-input-tpl-2-1'), {
      target: { value: 'trust' },
    })
    fireEvent.click(screen.getByTestId('save-analysis-template-tpl-2'))

    expect(analysisTemplateHookState.current.updateTemplate).not.toHaveBeenCalled()
    expect(await screen.findByTestId('analysis-template-editor-error-tpl-2')).toHaveTextContent('trust')
  })

  it('blocks saving when condition keys repeat inside a layer', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))
    fireEvent.click(screen.getByTestId('add-analysis-template-condition-tpl-2-0'))
    fireEvent.change(screen.getByTestId('analysis-template-condition-key-input-tpl-2-0-0'), {
      target: { value: 'source_trust' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-label-input-tpl-2-0-0'), {
      target: { value: 'Source trust A' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-value-input-tpl-2-0-0'), {
      target: { value: 'medium' },
    })
    fireEvent.click(screen.getByTestId('add-analysis-template-condition-tpl-2-0'))
    fireEvent.change(screen.getByTestId('analysis-template-condition-key-input-tpl-2-0-1'), {
      target: { value: 'source_trust' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-label-input-tpl-2-0-1'), {
      target: { value: 'Source trust B' },
    })
    fireEvent.change(screen.getByTestId('analysis-template-condition-value-input-tpl-2-0-1'), {
      target: { value: 'high' },
    })
    fireEvent.click(screen.getByTestId('save-analysis-template-tpl-2'))

    expect(analysisTemplateHookState.current.updateTemplate).not.toHaveBeenCalled()
    expect(await screen.findByTestId('analysis-template-editor-error-tpl-2')).toHaveTextContent('source_trust')
  })

  it('can preview the unsaved draft template from the editor', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))
    fireEvent.click(screen.getByTestId('preview-draft-analysis-template-tpl-2'))

    expect(apiMocks.previewDraftAnalysisTemplate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'tpl-2-draft',
        name: '稳妥可信',
      })
    )
    expect(await screen.findByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('10')
    expect(screen.getByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('4')
  })

  it('shows an unsaved-changes badge while editing a modified template', () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))
    expect(screen.queryByTestId('analysis-template-dirty-state-tpl-2')).not.toBeInTheDocument()
    expect(screen.getByText('规则键')).toBeInTheDocument()
    expect(screen.getByText('规则名称')).toBeInTheDocument()
    expect(screen.getByText('执行模式')).toBeInTheDocument()
    expect(screen.getByText('规则层')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('analysis-template-description-input-tpl-2'), {
      target: { value: 'Prefer trusted sources with solo bias' },
    })

    expect(screen.getByTestId('analysis-template-dirty-state-tpl-2')).toHaveTextContent('未保存修改')
  })

  it('refreshes the saved preview after updating a template', async () => {
    analysisTemplateHookState.current.updateTemplate.mockResolvedValue({
      ...analysisTemplateHookState.current.templates[1],
      description: 'Prefer trusted sources with solo bias',
    })

    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))
    fireEvent.change(screen.getByTestId('analysis-template-description-input-tpl-2'), {
      target: { value: 'Prefer trusted sources with solo bias' },
    })
    fireEvent.click(screen.getByTestId('save-analysis-template-tpl-2'))

    await waitFor(() => {
      expect(analysisTemplateHookState.current.updateTemplate).toHaveBeenCalledWith(
        'tpl-2',
        expect.objectContaining({
          description: 'Prefer trusted sources with solo bias',
        })
      )
    })
    await waitFor(() => {
      expect(apiMocks.previewAnalysisTemplate).toHaveBeenCalledWith('tpl-2')
    })
    expect(await screen.findByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('12')
    expect(screen.getByTestId('analysis-template-preview-tpl-2')).toHaveTextContent('5')
  })

  it('can save the current draft as a new template', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('Safe trust branch')
    analysisTemplateHookState.current.createTemplate.mockImplementation(
      async (name: string, sourceTemplate?: (typeof analysisTemplateHookState.current.templates)[number] | null) => {
        const created = {
          ...(sourceTemplate ?? analysisTemplateHookState.current.templates[1]),
          id: 'tpl-4',
          slug: 'safe-trust-branch',
          name,
          is_default: false,
        }
        analysisTemplateHookState.current.templates = [
          ...analysisTemplateHookState.current.templates,
          created,
        ]
        return created
      }
    )

    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))
    fireEvent.change(screen.getByTestId('analysis-template-description-input-tpl-2'), {
      target: { value: 'Prefer trusted sources with solo bias' },
    })
    fireEvent.click(screen.getByTestId('save-as-analysis-template-tpl-2'))

    await waitFor(() => {
      expect(analysisTemplateHookState.current.createTemplate).toHaveBeenCalledWith(
        'Safe trust branch',
        expect.objectContaining({
          id: 'tpl-2',
          name: '稳妥可信',
          description: 'Prefer trusted sources with solo bias',
        })
      )
    })
    expect(await screen.findByTestId('analysis-template-editor-tpl-4')).toBeInTheDocument()
    expect(screen.getByTestId('analysis-template-description-input-tpl-4')).toHaveValue(
      'Prefer trusted sources with solo bias'
    )
  })

  it('edits business template preferences instead of raw model routing', async () => {
    render(
      <MemoryRouter>
        <AnalysisTemplatesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('edit-analysis-template-tpl-2'))

    expect(await screen.findByLabelText(/risk tolerance/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/research mode/i)).toBeInTheDocument()
    expect(screen.queryByText(/screening_model/i)).not.toBeInTheDocument()
  })
})
