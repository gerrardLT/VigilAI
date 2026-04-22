import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalysisResultsPage from './AnalysisResultsPage'

const apiMocks = vi.hoisted(() => ({
  getAnalysisResults: vi.fn(),
}))

const analysisTemplateHookState = vi.hoisted(() => ({
  current: {
    templates: [{ id: 'tpl-1', slug: 'quick-money', name: 'Quick money' }],
    defaultTemplate: { id: 'tpl-1', slug: 'quick-money', name: 'Quick money' },
    loading: false,
    error: null,
    refetch: vi.fn(),
    createTemplate: vi.fn(),
    duplicateTemplate: vi.fn(),
    activateTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    renameTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  },
}))

const workspaceHookState = vi.hoisted(() => ({
  current: {
    workspace: {
      overview: {
        total_activities: 12,
        total_sources: 4,
        activities_by_category: {},
        activities_by_source: {},
        recent_activities: 2,
        last_update: '2026-03-23T08:00:00Z',
        tracked_count: 2,
        favorited_count: 1,
      },
      top_opportunities: [],
      digest_preview: null,
      trends: [],
      alert_sources: [],
      first_actions: [],
      analysis_overview: {
        total: 6,
        passed: 3,
        watch: 2,
        rejected: 1,
      },
      blocked_opportunities: [],
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
}))

vi.mock('../hooks/useWorkspace', () => ({
  useWorkspace: () => workspaceHookState.current,
}))

describe('AnalysisResultsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMocks.getAnalysisResults.mockImplementation(async (filters?: { analysis_status?: string }) => {
      if (filters?.analysis_status === 'rejected') {
        return {
          total: 1,
          page: 1,
          page_size: 20,
          items: [
            {
              id: 'activity-2',
              title: 'Enterprise RFP',
              description: 'Requires a large team.',
              source_id: 'enterprise',
              source_name: 'Enterprise Feed',
              url: 'https://example.com/rfp',
              category: 'bounty',
              tags: [],
              prize: null,
              dates: null,
              location: null,
              organizer: null,
              summary: 'Blocked by team requirement',
              score: 5.1,
              score_reason: 'Low solo fit',
              deadline_level: 'soon',
              trust_level: 'medium',
              updated_fields: [],
              analysis_status: 'rejected',
              analysis_failed_layer: 'hard_gate',
              analysis_summary_reasons: ['Solo only failed hard gate'],
              analysis_layer_results: [],
              analysis_score_breakdown: { hard_gate: 0 },
              status: 'upcoming',
              created_at: '2026-03-23T08:00:00Z',
              updated_at: '2026-03-23T08:00:00Z',
            },
          ],
        }
      }

      return {
        total: 2,
        page: 1,
        page_size: 20,
        items: [
          {
            id: 'activity-1',
            title: 'AI Hackathon',
            description: 'Solo-friendly build sprint.',
            source_id: 'devpost',
            source_name: 'Devpost',
            url: 'https://example.com/hackathon',
            category: 'hackathon',
            tags: ['ai'],
            prize: null,
            dates: null,
            location: null,
            organizer: null,
            summary: 'Fast payout path',
            score: 9.1,
            score_reason: 'High ROI',
            deadline_level: 'urgent',
            trust_level: 'high',
            updated_fields: [],
            analysis_status: 'passed',
            analysis_failed_layer: null,
            analysis_summary_reasons: ['Reward clarity passed'],
            analysis_layer_results: [],
            analysis_score_breakdown: { roi: 1 },
            status: 'upcoming',
            created_at: '2026-03-23T08:00:00Z',
            updated_at: '2026-03-23T08:00:00Z',
          },
          {
            id: 'activity-2',
            title: 'Enterprise RFP',
            description: 'Requires a large team.',
            source_id: 'enterprise',
            source_name: 'Enterprise Feed',
            url: 'https://example.com/rfp',
            category: 'bounty',
            tags: [],
            prize: null,
            dates: null,
            location: null,
            organizer: null,
            summary: 'Blocked by team requirement',
            score: 5.1,
            score_reason: 'Low solo fit',
            deadline_level: 'soon',
            trust_level: 'medium',
            updated_fields: [],
            analysis_status: 'rejected',
            analysis_failed_layer: 'hard_gate',
            analysis_summary_reasons: ['Solo only failed hard gate'],
            analysis_layer_results: [],
            analysis_score_breakdown: { hard_gate: 0 },
            status: 'upcoming',
            created_at: '2026-03-23T08:00:00Z',
            updated_at: '2026-03-23T08:00:00Z',
          },
        ],
      }
    })
  })

  it('renders the analysis overview, active template, and result cards', async () => {
    render(
      <MemoryRouter>
        <AnalysisResultsPage />
      </MemoryRouter>
    )

    expect(await screen.findByTestId('analysis-results-page')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'AI 分析结果' })).toBeInTheDocument()
    expect(screen.getByText('AI 智能代理决策记录')).toBeInTheDocument()
    expect(screen.queryByText('Analysis Results')).not.toBeInTheDocument()
    expect(screen.getByTestId('analysis-results-active-template')).toHaveTextContent('快钱优先')
    expect(screen.getByTestId('analysis-results-overview')).toHaveTextContent('3')
    expect(screen.getByTestId('analysis-results-diagnosis')).toBeInTheDocument()
    expect(screen.getByText('AI 黑客松')).toBeInTheDocument()
    expect(screen.getByText('企业需求征集')).toBeInTheDocument()
    expect(screen.getByText('未通过仅限单人的硬门槛')).toBeInTheDocument()
    expect(screen.getByText('拦截位置：硬门槛')).toBeInTheDocument()
    expect(screen.getByText('理由条数')).toBeInTheDocument()
    expect(screen.queryByText('失败层：硬门槛')).not.toBeInTheDocument()
  })

  it('filters the list by analysis status and refreshes the dataset', async () => {
    render(
      <MemoryRouter>
        <AnalysisResultsPage />
      </MemoryRouter>
    )

    await screen.findByTestId('analysis-results-page')
    expect(screen.getByRole('button', { name: '淘汰' })).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('analysis-results-filter-rejected'))

    await waitFor(() => {
      expect(apiMocks.getAnalysisResults).toHaveBeenLastCalledWith({
        analysis_status: 'rejected',
        page: 1,
        page_size: 20,
      })
    })
    expect(await screen.findByText('企业需求征集')).toBeInTheDocument()
    expect(screen.queryByText('AI 黑客松')).not.toBeInTheDocument()
  })

  it('shows a strict-template diagnosis when almost everything is rejected', async () => {
    workspaceHookState.current = {
      ...workspaceHookState.current,
      workspace: {
        ...workspaceHookState.current.workspace,
        analysis_overview: {
          total: 6,
          passed: 0,
          watch: 0,
          rejected: 6,
        },
      },
    }
    apiMocks.getAnalysisResults.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [
        {
          id: 'activity-2',
          title: 'Enterprise RFP',
          description: null,
          source_id: 'enterprise',
          source_name: 'Enterprise Feed',
          url: 'https://example.com/rfp',
          category: 'bounty',
          tags: [],
          prize: null,
          dates: null,
          location: null,
          organizer: null,
          summary: null,
          score: 5.1,
          score_reason: 'Low solo fit',
          deadline_level: 'soon',
          trust_level: 'medium',
          updated_fields: [],
          analysis_status: 'rejected',
          analysis_failed_layer: 'hard_gate',
          analysis_summary_reasons: ['Solo only failed hard gate'],
          analysis_layer_results: [],
          analysis_score_breakdown: { hard_gate: 0 },
          status: 'upcoming',
          created_at: '2026-03-23T08:00:00Z',
          updated_at: '2026-03-23T08:00:00Z',
        },
      ],
    })

    render(
      <MemoryRouter>
        <AnalysisResultsPage />
      </MemoryRouter>
    )

    expect(await screen.findByTestId('analysis-results-diagnosis')).toHaveTextContent('当前模板偏严格')
    expect(screen.getByText('几乎所有机会都被拦掉了')).toBeInTheDocument()
    expect(screen.getByText('优先放宽一条硬门槛')).toBeInTheDocument()
  })
})
