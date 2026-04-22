import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceResponse } from '../types'
import WorkspacePage from './WorkspacePage'

const refetch = vi.fn()
type WorkspaceHookState = {
  workspace: WorkspaceResponse | null
  loading: boolean
  error: string | null
  refetch: typeof refetch
}
const workspaceHookState = vi.hoisted(() => ({
  current: null as WorkspaceHookState | null,
}))
const serviceMocks = vi.hoisted(() => ({
  createTracking: vi.fn(),
  updateTracking: vi.fn(),
}))
const analysisTemplateHookState = vi.hoisted(() => ({
  current: {
    templates: [{ id: 'tpl-1', slug: 'quick-money', name: 'Quick money' }],
    defaultTemplate: { id: 'tpl-1', slug: 'quick-money', name: 'Quick money' },
    loading: false,
    error: null,
    refetch: vi.fn(),
    duplicateTemplate: vi.fn(),
    activateTemplate: vi.fn(),
  },
}))

function buildWorkspaceHookState(overrides?: Partial<WorkspaceHookState>): WorkspaceHookState {
  return {
    workspace: {
      overview: {
        total_activities: 24,
        total_sources: 5,
        activities_by_category: { hackathon: 8 },
        activities_by_source: { devpost: 12 },
        recent_activities: 4,
        last_update: '2026-03-23T08:00:00Z',
        tracked_count: 3,
        favorited_count: 2,
      },
      top_opportunities: [
        {
          id: 'activity-1',
          title: 'AI Hackathon',
          description: 'Build an AI agent.',
          source_id: 'devpost',
          source_name: 'Devpost',
          url: 'https://example.com/ai-hackathon',
          category: 'hackathon',
          tags: ['ai'],
          prize: null,
          dates: null,
          location: null,
          organizer: null,
          summary: 'High priority AI event.',
          score: 9.2,
          score_reason: 'High score',
          deadline_level: 'urgent',
          trust_level: 'high',
          updated_fields: [],
          is_tracking: false,
          is_favorited: false,
          status: 'upcoming',
          created_at: '2026-03-22T08:00:00Z',
          updated_at: '2026-03-23T08:00:00Z',
        },
      ],
      digest_preview: {
        id: 'digest-1',
        digest_date: '2026-03-23',
        title: 'Daily Digest',
        summary: 'Top picks for today',
        content: ')]( \n- AI Hackathon\nrmat=webp&resize=400x300\n[更多](https://example.com/more)\nShip MVP Fast\nBuild an AI agent.',
        item_ids: ['activity-1'],
        status: 'draft',
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
        last_sent_at: null,
        send_channel: null,
      },
      trends: [
        { date: '2026-03-20', count: 2 },
        { date: '2026-03-21', count: 3 },
      ],
      alert_sources: [
        {
          id: 'source-1',
          name: 'Hackathon Feed',
          type: 'web',
          category: 'hackathon',
          status: 'error',
          last_run: '2026-03-23T08:00:00Z',
          last_success: '2026-03-21T08:00:00Z',
          activity_count: 10,
          error_message: 'Timed out',
        },
      ],
      first_actions: [
        {
          id: 'activity-2',
          title: 'Ship MVP Fast )]( Ship MVP Fast 2026-03-24 21:00 线上活动 1(current) 2 3',
          description: 'Fast deadline [更多](https://example.com/more)',
          source_id: 'devpost',
          source_name: 'Devpost',
          url: 'https://example.com/mvp',
          category: 'hackathon',
          tags: [],
          prize: null,
          dates: null,
          location: null,
          organizer: null,
          summary: 'Do this first',
          score: 8.5,
          score_reason: 'Urgent',
          deadline_level: 'urgent',
          trust_level: 'high',
          updated_fields: [],
          is_tracking: false,
          is_favorited: false,
          status: 'upcoming',
          created_at: '2026-03-22T08:00:00Z',
          updated_at: '2026-03-23T08:00:00Z',
        },
      ],
      analysis_overview: {
        total: 4,
        passed: 2,
        watch: 1,
        rejected: 1,
      },
      blocked_opportunities: [
        {
          id: 'activity-3',
          title: 'Enterprise RFP )]( Enterprise RFP 2026-03-30 10:00 线下活动 1(current) 2 3',
          description: 'Looks big but not solo-friendly. [更多](https://example.com/more)',
          source_id: 'enterprise',
          source_name: 'Enterprise Feed',
          url: 'https://example.com/rfp',
          category: 'bounty',
          tags: [],
          prize: null,
          dates: null,
          location: null,
          organizer: null,
          summary: 'Likely blocked by hard gate.',
          score: 6.2,
          score_reason: 'Low solo fit',
          deadline_level: 'soon',
          trust_level: 'medium',
          updated_fields: [],
          analysis_status: 'rejected',
          analysis_summary_reasons: ['Solo only failed hard gate'],
          is_tracking: false,
          is_favorited: false,
          status: 'upcoming',
          created_at: '2026-03-22T08:00:00Z',
          updated_at: '2026-03-23T08:00:00Z',
        },
      ],
    },
    loading: false,
    error: null,
    refetch,
    ...overrides,
  }
}

vi.mock('../hooks/useWorkspace', () => ({
  useWorkspace: () => workspaceHookState.current ?? buildWorkspaceHookState(),
}))

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
}))

vi.mock('../services/api', () => ({
  api: {
    createTracking: serviceMocks.createTracking,
    updateTracking: serviceMocks.updateTracking,
  },
}))

beforeEach(() => {
  refetch.mockClear()
  workspaceHookState.current = buildWorkspaceHookState()
  serviceMocks.createTracking.mockReset()
  serviceMocks.updateTracking.mockReset()
  serviceMocks.createTracking.mockResolvedValue({
    activity_id: 'activity-1',
    is_favorited: false,
    status: 'tracking',
    notes: null,
    next_action: null,
    remind_at: null,
    created_at: '2026-03-23T08:00:00Z',
    updated_at: '2026-03-23T08:00:00Z',
  })
  serviceMocks.updateTracking.mockResolvedValue({
    activity_id: 'activity-1',
    is_favorited: true,
    status: 'tracking',
    notes: null,
    next_action: null,
    remind_at: null,
    created_at: '2026-03-23T08:00:00Z',
    updated_at: '2026-03-23T08:00:00Z',
  })
})

describe('WorkspacePage', () => {
  it('keeps hook ordering stable when the workspace finishes loading', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    workspaceHookState.current = buildWorkspaceHookState({
      workspace: null,
      loading: true,
    })

    const { rerender } = render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    workspaceHookState.current = buildWorkspaceHookState()

    expect(() => {
      rerender(
        <MemoryRouter>
          <WorkspacePage />
        </MemoryRouter>
      )
    }).not.toThrow()

    expect(screen.getByTestId('workspace-page')).toBeInTheDocument()
    consoleErrorSpy.mockRestore()
  })

  it('renders workspace overview, digest preview, alerts, and first actions', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('workspace-page')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '机会工作台' })).toBeInTheDocument()
    expect(screen.getByText('AI 智能代理决策驾驶舱')).toBeInTheDocument()
    expect(screen.getByText('今日结论')).toBeInTheDocument()
    expect(screen.getByText('立即处理')).toBeInTheDocument()
    expect(screen.getByText('系统告警')).toBeInTheDocument()
    expect(screen.getByText('模板诊断')).toBeInTheDocument()
    expect(screen.getByText('AI 黑客松')).toBeInTheDocument()
    expect(screen.getByText('今日日报')).toBeInTheDocument()
    expect(screen.getByText('黑客松情报源')).toBeInTheDocument()
    expect(screen.getByText('MVP 快速交付')).toBeInTheDocument()
    expect(screen.getByText('企业需求征集')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-analysis-overview')).toHaveTextContent('2')
    expect(screen.getByTestId('workspace-default-template')).toHaveTextContent('快钱优先')
    expect(screen.getByTestId('workspace-template-performance')).toHaveTextContent('50%')
    expect(screen.getByTestId('workspace-template-performance')).toHaveTextContent('未通过仅限单人的硬门槛')
    expect(screen.queryByText('VigilAI Workspace')).not.toBeInTheDocument()
  })

  it('renders a cleaned digest excerpt instead of raw scraped noise', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    const excerpt = screen.getByTestId('workspace-digest-excerpt')

    expect(excerpt).toHaveTextContent('- AI 黑客松')
    expect(excerpt).toHaveTextContent('MVP 快速交付')
    expect(excerpt).toHaveTextContent('构建一个 AI Agent。')
    expect(excerpt).not.toHaveTextContent(')](')
    expect(excerpt).not.toHaveTextContent('rmat=webp')
    expect(excerpt).not.toHaveTextContent('resize=400x300')
    expect(excerpt).not.toHaveTextContent('https://example.com/more')
  })

  it('exposes decision-first panels and supports refreshing the workspace', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('workspace-priority-panel')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-template-diagnosis')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-alert-panel')).toBeInTheDocument()
    expect(screen.queryByTestId('workspace-quick-actions')).not.toBeInTheDocument()
    expect(screen.getByText('先处理高优先级机会')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('workspace-refresh-button'))

    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it('supports tracking and favoriting top opportunities directly from the workspace', async () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('workspace-track-activity-1'))

    await waitFor(() => {
      expect(serviceMocks.createTracking).toHaveBeenCalledWith('activity-1', { status: 'tracking' })
    })

    fireEvent.click(screen.getByTestId('workspace-favorite-activity-1'))

    await waitFor(() => {
      expect(serviceMocks.updateTracking).toHaveBeenCalledWith('activity-1', { is_favorited: true })
    })
  })
})
