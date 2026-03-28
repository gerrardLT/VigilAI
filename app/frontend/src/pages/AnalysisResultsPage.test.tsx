import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AnalysisResultsPage from './AnalysisResultsPage'

const apiMocks = vi.hoisted(() => ({
  getAnalysisResults: vi.fn(),
}))
const agentAnalysisJobsHookState = vi.hoisted(() => ({
  current: {
    jobs: [
      {
        id: 'job-batch-1',
        trigger_type: 'scheduled',
        scope_type: 'batch',
        template_id: 'tpl-1',
        route_policy: {},
        budget_policy: {},
        status: 'completed',
        requested_by: null,
        created_at: '2026-03-23T08:00:00Z',
        finished_at: '2026-03-23T08:05:00Z',
        item_count: 2,
        completed_items: 2,
        failed_items: 0,
        needs_research_count: 1,
      },
    ],
    total: 1,
    activeJob: {
      id: 'job-batch-1',
      trigger_type: 'scheduled',
      scope_type: 'batch',
      template_id: 'tpl-1',
      route_policy: {},
      budget_policy: {},
      status: 'completed',
      requested_by: null,
      created_at: '2026-03-23T08:00:00Z',
      finished_at: '2026-03-23T08:05:00Z',
      item_count: 2,
      items: [
        {
          id: 'job-item-1',
          job_id: 'job-batch-1',
          activity_id: 'activity-1',
          status: 'completed',
          needs_research: false,
          final_draft_status: 'pass',
          created_at: '2026-03-23T08:00:00Z',
          updated_at: '2026-03-23T08:05:00Z',
          activity: {
            id: 'activity-1',
            title: 'AI Hackathon',
          },
          draft: {
            status: 'pass',
            summary: 'Safe to pursue',
            reasons: ['Reward clarity passed'],
            risk_flags: [],
            structured: {},
          },
          steps: [],
          evidence: [],
          reviews: [],
        },
        {
          id: 'job-item-2',
          job_id: 'job-batch-1',
          activity_id: 'activity-2',
          status: 'failed',
          needs_research: true,
          final_draft_status: 'watch',
          created_at: '2026-03-23T08:00:00Z',
          updated_at: '2026-03-23T08:05:00Z',
          activity: {
            id: 'activity-2',
            title: 'Enterprise RFP',
          },
          draft: {
            status: 'watch',
            summary: 'Blocked by team requirement',
            reasons: ['Solo only failed hard gate'],
            risk_flags: ['team_required'],
            structured: {},
          },
          steps: [],
          evidence: [],
          reviews: [],
        },
      ],
    },
    loading: false,
    refreshing: false,
    error: null,
    refetch: vi.fn(),
    loadJob: vi.fn(),
    createJob: vi.fn(),
  },
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

vi.mock('../hooks/useAgentAnalysisJobs', () => ({
  useAgentAnalysisJobs: () => agentAnalysisJobsHookState.current,
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
    expect(screen.getByTestId('analysis-results-active-template')).toHaveTextContent('Quick money')
    expect(screen.getByTestId('analysis-results-overview')).toHaveTextContent('3')
    expect(screen.getByText('AI Hackathon')).toBeInTheDocument()
    expect(screen.getByText('Enterprise RFP')).toBeInTheDocument()
    expect(screen.getByText('Solo only failed hard gate')).toBeInTheDocument()
  })

  it('filters the list by analysis status and refreshes the dataset', async () => {
    render(
      <MemoryRouter>
        <AnalysisResultsPage />
      </MemoryRouter>
    )

    await screen.findByTestId('analysis-results-page')
    expect(screen.getByRole('button', { name: '拦截' })).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('analysis-results-filter-rejected'))

    await waitFor(() => {
      expect(apiMocks.getAnalysisResults).toHaveBeenLastCalledWith({
        analysis_status: 'rejected',
        page: 1,
        page_size: 20,
      })
    })
    expect(await screen.findByText('Enterprise RFP')).toBeInTheDocument()
    expect(screen.queryByText('AI Hackathon')).not.toBeInTheDocument()
  })

  it('shows the job operations console with the latest agent-analysis job detail', async () => {
    render(
      <MemoryRouter>
        <AnalysisResultsPage />
      </MemoryRouter>
    )

    expect(await screen.findByTestId('analysis-results-job-list')).toBeInTheDocument()
    expect(screen.getByTestId('agent-analysis-job-banner')).toHaveTextContent('job-batch-1')
    expect(screen.getByText('Enterprise RFP')).toBeInTheDocument()
    expect(screen.getByText('Solo only failed hard gate')).toBeInTheDocument()
  })
})
