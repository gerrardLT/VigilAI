import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ActivitiesPage from './ActivitiesPage'

const setFilters = vi.fn()
const apiMocks = vi.hoisted(() => ({
  getSources: vi.fn(),
  createTracking: vi.fn(),
  updateTracking: vi.fn(),
  previewDraftAnalysisTemplateResults: vi.fn(),
}))
const analysisTemplateHookState = vi.hoisted(() => ({
  current: {
    templates: [
      {
        id: 'tpl-1',
        slug: 'quick-money',
        name: 'Quick money',
        description: 'Focus on solo-friendly, clear-reward opportunities',
        is_default: true,
        tags: ['roi'],
        layers: [
          {
            key: 'hard_gate',
            label: 'Hard gate',
            enabled: true,
            mode: 'filter',
            conditions: [
              {
                key: 'solo_friendliness',
                label: 'Solo only',
                enabled: true,
                operator: 'eq',
                value: 'solo_friendly',
                hard_fail: true,
                strictness: 'strict',
              },
            ],
          },
        ],
        sort_fields: ['roi_score'],
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      },
      {
        id: 'tpl-2',
        slug: 'steady-trust',
        name: 'Steady trust',
        description: 'Prefer trustworthy and well-documented opportunities',
        is_default: false,
        tags: ['trust'],
        layers: [
          {
            key: 'trust_gate',
            label: 'Trust gate',
            enabled: true,
            mode: 'filter',
            conditions: [
              {
                key: 'trust_risk_level',
                label: 'Low risk only',
                enabled: true,
                operator: 'in',
                value: ['low', 'medium'],
                hard_fail: true,
                strictness: 'strict',
              },
            ],
          },
        ],
        sort_fields: ['trust_score'],
        created_at: '2026-03-23T09:00:00Z',
        updated_at: '2026-03-23T09:00:00Z',
      },
    ],
    defaultTemplate: {
      id: 'tpl-1',
      slug: 'quick-money',
      name: 'Quick money',
      description: 'Focus on solo-friendly, clear-reward opportunities',
      is_default: true,
      tags: ['roi'],
      layers: [
        {
          key: 'hard_gate',
          label: 'Hard gate',
          enabled: true,
          mode: 'filter',
          conditions: [
            {
              key: 'solo_friendliness',
              label: 'Solo only',
              enabled: true,
              operator: 'eq',
              value: 'solo_friendly',
              hard_fail: true,
              strictness: 'strict',
            },
          ],
        },
      ],
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
  },
}))

const refetch = vi.fn()

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
}))

vi.mock('../hooks/useActivities', () => ({
  useActivities: () => ({
    activities: [
      {
        id: 'activity-1',
        title: 'AI Hackathon',
        description: 'Build an AI prototype.',
        source_id: 'devpost',
        source_name: 'Devpost',
        url: 'https://example.com/a',
        category: 'hackathon',
        tags: ['ai'],
        prize: null,
        dates: { start_date: null, end_date: null, deadline: null },
        location: null,
        organizer: null,
        summary: 'High priority',
        score: 9.1,
        score_reason: 'Recommended first',
        deadline_level: 'urgent',
        trust_level: 'high',
        updated_fields: [],
        analysis_status: 'passed',
        is_tracking: false,
        is_favorited: false,
        status: 'upcoming',
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      },
      {
        id: 'activity-2',
        title: 'Grant Program',
        description: 'Funding support for builders.',
        source_id: 'gitcoin',
        source_name: 'Gitcoin',
        url: 'https://example.com/b',
        category: 'grant',
        tags: ['funding'],
        prize: null,
        dates: { start_date: null, end_date: null, deadline: null },
        location: null,
        organizer: null,
        summary: 'Worth saving',
        score: 8.4,
        score_reason: 'Good fit',
        deadline_level: 'soon',
        trust_level: 'medium',
        updated_fields: [],
        analysis_status: 'watch',
        is_tracking: true,
        is_favorited: false,
        status: 'upcoming',
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    loading: false,
    error: null,
    filters: {
      category: '',
      source_id: '',
      search: '',
      deadline_level: '',
      tracking_state: '',
      analysis_status: '',
      sort_by: 'score',
      sort_order: 'desc',
      page: 1,
    },
    setFilters,
    setPage: vi.fn(),
    refetch,
  }),
}))

describe('Opportunity pool page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMocks.getSources.mockResolvedValue([
      {
        id: 'devpost',
        name: 'Devpost',
        type: 'web',
        category: 'hackathon',
        status: 'success',
        last_run: null,
        last_success: null,
        activity_count: 5,
        error_message: null,
      },
    ])
    apiMocks.createTracking.mockResolvedValue({})
    apiMocks.updateTracking.mockResolvedValue({})
    apiMocks.previewDraftAnalysisTemplateResults.mockResolvedValue({
      template_id: 'tpl-1-draft',
      total: 2,
      passed: 1,
      watch: 0,
      rejected: 1,
      items: [
        {
          activity_id: 'activity-1',
          status: 'passed',
          failed_layer: null,
          summary_reasons: ['Reward clarity passed'],
          layer_results: [],
        },
        {
          activity_id: 'activity-2',
          status: 'rejected',
          failed_layer: 'hard_gate',
          summary_reasons: ['Solo only failed hard gate'],
          layer_results: [],
        },
      ],
    })
    analysisTemplateHookState.current.createTemplate.mockResolvedValue({
      ...analysisTemplateHookState.current.defaultTemplate,
      id: 'tpl-3',
      slug: 'adjusted-quick-money',
      name: 'Adjusted quick money',
      is_default: false,
    })
  })

  it('renders the V2 opportunity pool and supports batch tracking/favorite actions', async () => {
    render(
      <MemoryRouter initialEntries={['/activities']}>
        <ActivitiesPage />
      </MemoryRouter>
    )

    expect(screen.getByText('机会池')).toBeInTheDocument()
    expect(screen.getByText('按推荐优先级筛选、批量处理并推进机会。')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('select-activity-1'))
    fireEvent.click(screen.getByTestId('select-activity-2'))
    fireEvent.click(screen.getByTestId('batch-track-button'))

    await waitFor(() => {
      expect(apiMocks.createTracking).toHaveBeenCalledWith('activity-1', { status: 'tracking' })
    })
    expect(apiMocks.updateTracking).toHaveBeenCalledWith('activity-2', { status: 'tracking' })
    expect(refetch).toHaveBeenCalled()

    fireEvent.click(screen.getByTestId('batch-favorite-button'))

    await waitFor(() => {
      expect(apiMocks.createTracking).toHaveBeenCalledWith('activity-1', {
        status: 'saved',
        is_favorited: true,
      })
    })
    expect(apiMocks.updateTracking).toHaveBeenCalledWith('activity-2', { is_favorited: true })
  })

  it('shows the active AI template and lets the user switch analysis status filters', () => {
    render(
      <MemoryRouter initialEntries={['/activities']}>
        <ActivitiesPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('opportunity-pool-active-template')).toHaveTextContent('快钱优先')

    fireEvent.click(screen.getByTestId('analysis-status-filter-passed'))
    expect(setFilters).toHaveBeenCalledWith({ analysis_status: 'passed' })

    fireEvent.click(screen.getByTestId('analysis-status-filter-cleared'))
    expect(setFilters).toHaveBeenCalledWith({ analysis_status: '' })
  })

  it('applies temporary rule adjustments and refreshes the visible AI verdicts', async () => {
    render(
      <MemoryRouter initialEntries={['/activities']}>
        <ActivitiesPage />
      </MemoryRouter>
    )

    expect(await screen.findByTestId('opportunity-pool-draft-banner')).toHaveTextContent('当前模板 快钱优先')
    expect(screen.getByText('仅限单人')).toBeInTheDocument()
    expect(screen.getByText('单人友好度 · 等于')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('opportunity-pool-condition-enabled-tpl-1-0-0'))

    await waitFor(() => {
      expect(apiMocks.previewDraftAnalysisTemplateResults).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'tpl-1-draft',
          activity_ids: ['activity-1', 'activity-2'],
        })
      )
    })

    expect(await screen.findByTestId('opportunity-pool-draft-banner')).toHaveTextContent('临时调整已生效')
    expect(screen.getByTestId('opportunity-pool-draft-preview')).toHaveTextContent('1')
    expect(screen.getAllByTestId('activity-card-analysis-status')[1]).toHaveTextContent('淘汰')
    expect(screen.getByText('Solo only failed hard gate')).toBeInTheDocument()
  })

  it('can save temporary adjustments as a new template', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('Adjusted quick money')

    render(
      <MemoryRouter initialEntries={['/activities']}>
        <ActivitiesPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('opportunity-pool-condition-enabled-tpl-1-0-0'))
    fireEvent.click(screen.getByTestId('save-draft-as-template-button'))

    await waitFor(() => {
      expect(analysisTemplateHookState.current.createTemplate).toHaveBeenCalledWith(
        'Adjusted quick money',
        expect.objectContaining({
          id: 'tpl-1',
          layers: [
            expect.objectContaining({
              conditions: [
                expect.objectContaining({
                  enabled: false,
                }),
              ],
            }),
          ],
        })
      )
    })

    await waitFor(() => {
      expect(analysisTemplateHookState.current.activateTemplate).toHaveBeenCalledWith('tpl-3')
    })
  })

  it('allows switching the active template from the opportunity pool', async () => {
    render(
      <MemoryRouter initialEntries={['/activities']}>
        <ActivitiesPage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByTestId('opportunity-pool-template-switcher'), {
      target: { value: 'tpl-2' },
    })

    await waitFor(() => {
      expect(analysisTemplateHookState.current.activateTemplate).toHaveBeenCalledWith('tpl-2')
    })
  })
})
