import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceResponse } from '../types'
import WorkspacePage from './WorkspacePage'

const refetch = vi.fn()

function buildLocalIso(daysOffset: number, hour: number) {
  const date = new Date()
  date.setDate(date.getDate() + daysOffset)
  date.setHours(hour, 0, 0, 0)
  return date.toISOString()
}

type WorkspaceHookState = {
  workspace: WorkspaceResponse | null
  loading: boolean
  error: string | null
  refetch: typeof refetch
}

type TrackingHookState = {
  items: Array<Record<string, unknown>>
  loading: boolean
  error: string | null
}

const workspaceHookState = vi.hoisted(() => ({ current: null as WorkspaceHookState | null }))
const trackingHookState = vi.hoisted(() => ({ current: null as TrackingHookState | null }))
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
        item_count: 3,
        completed_items: 2,
        failed_items: 1,
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
      item_count: 3,
      items: [],
    },
    loading: false,
    refreshing: false,
    error: null,
    refetch: vi.fn(),
    loadJob: vi.fn(),
    createJob: vi.fn(),
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
        content: ')](\n- AI Hackathon\nrmat=webp&resize=400x300\n[更多](https://example.com/more)\nShip MVP Fast\nBuild an AI agent.',
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
          title: 'Ship MVP Fast',
          description: 'Fast deadline',
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
          title: 'Enterprise RFP',
          description: 'Looks big but not solo-friendly.',
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

function buildTrackingItems() {
  return [
    {
      activity_id: 'tracking-1',
      is_favorited: false,
      status: 'saved',
      stage: 'to_decide',
      notes: null,
      next_action: null,
      remind_at: null,
      created_at: '2026-03-20T08:00:00Z',
      updated_at: '2026-03-20T08:00:00Z',
      activity: {
        id: 'tracking-1',
        title: 'Backlog Grant',
        description: 'Need a decision',
        source_id: 'source-1',
        source_name: 'Source One',
        url: 'https://example.com/backlog',
        category: 'grant',
        tags: [],
        prize: null,
        dates: null,
        location: null,
        organizer: null,
        summary: 'Worth saving',
        score: 7,
        score_reason: 'Good fit',
        deadline_level: 'later',
        trust_level: 'high',
        updated_fields: [],
        is_tracking: true,
        is_favorited: false,
        status: 'upcoming',
        created_at: '2026-03-20T08:00:00Z',
        updated_at: '2026-03-20T08:00:00Z',
      },
    },
    {
      activity_id: 'tracking-2',
      is_favorited: true,
      status: 'tracking',
      stage: 'watching',
      notes: null,
      next_action: '今天确认报名条件',
      remind_at: buildLocalIso(0, 18),
      created_at: '2026-03-21T08:00:00Z',
      updated_at: '2026-03-22T08:00:00Z',
      activity: {
        id: 'tracking-2',
        title: '今日提醒机会',
        description: '需要今天跟进',
        source_id: 'source-2',
        source_name: 'Source Two',
        url: 'https://example.com/remind-today',
        category: 'hackathon',
        tags: [],
        prize: null,
        dates: null,
        location: null,
        organizer: null,
        summary: '今天推进',
        score: 8.2,
        score_reason: 'Need follow-up',
        deadline_level: 'soon',
        trust_level: 'high',
        updated_fields: [],
        is_tracking: true,
        is_favorited: true,
        status: 'upcoming',
        created_at: '2026-03-21T08:00:00Z',
        updated_at: '2026-03-22T08:00:00Z',
      },
    },
    {
      activity_id: 'tracking-3',
      is_favorited: false,
      status: 'tracking',
      stage: 'preparing',
      notes: null,
      next_action: '补交材料',
      remind_at: buildLocalIso(-1, 9),
      created_at: '2026-03-18T08:00:00Z',
      updated_at: '2026-03-19T08:00:00Z',
      activity: {
        id: 'tracking-3',
        title: '超时提醒机会',
        description: '已经超过提醒时间',
        source_id: 'source-3',
        source_name: 'Source Three',
        url: 'https://example.com/remind-overdue',
        category: 'bounty',
        tags: [],
        prize: null,
        dates: null,
        location: null,
        organizer: null,
        summary: '尽快处理',
        score: 7.8,
        score_reason: 'Overdue follow-up',
        deadline_level: 'normal',
        trust_level: 'medium',
        updated_fields: [],
        is_tracking: true,
        is_favorited: false,
        status: 'upcoming',
        created_at: '2026-03-18T08:00:00Z',
        updated_at: '2026-03-19T08:00:00Z',
      },
    },
  ]
}

function buildTrackingHookState(overrides?: Partial<TrackingHookState>): TrackingHookState {
  return {
    items: buildTrackingItems(),
    loading: false,
    error: null,
    ...overrides,
  }
}

vi.mock('../hooks/useWorkspace', () => ({
  useWorkspace: () => workspaceHookState.current ?? buildWorkspaceHookState(),
}))

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
}))

vi.mock('../hooks/useTracking', () => ({
  useTracking: () => ({
    items: trackingHookState.current?.items ?? buildTrackingItems(),
    loading: trackingHookState.current?.loading ?? false,
    error: trackingHookState.current?.error ?? null,
    statusFilter: undefined,
    setStatusFilter: vi.fn(),
    refetch: vi.fn(),
    createTracking: vi.fn(),
    updateTracking: vi.fn(),
    batchUpdateTracking: vi.fn(),
    deleteTracking: vi.fn(),
  }),
}))

vi.mock('../hooks/useAgentAnalysisJobs', () => ({
  useAgentAnalysisJobs: () => agentAnalysisJobsHookState.current,
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
  trackingHookState.current = buildTrackingHookState()
  serviceMocks.createTracking.mockReset()
  serviceMocks.updateTracking.mockReset()
  serviceMocks.createTracking.mockResolvedValue({
    activity_id: 'activity-1',
    is_favorited: false,
    status: 'saved',
    notes: null,
    next_action: '先确认参赛要求，再拆出报名和交付准备',
    remind_at: null,
    created_at: '2026-03-23T08:00:00Z',
    updated_at: '2026-03-23T08:00:00Z',
  })
  serviceMocks.updateTracking.mockResolvedValue({
    activity_id: 'activity-1',
    is_favorited: true,
    status: 'tracking',
    notes: null,
    next_action: '先确认参赛要求，再拆出报名和交付准备',
    remind_at: null,
    created_at: '2026-03-23T08:00:00Z',
    updated_at: '2026-03-23T08:00:00Z',
  })
})

describe('WorkspacePage', () => {
  it('keeps hook ordering stable when the workspace finishes loading', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    workspaceHookState.current = buildWorkspaceHookState({ workspace: null, loading: true })

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

  it('renders workspace overview and digest sections', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('workspace-page')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-summary-banner')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-action-cards')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-today-actions')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-untracked-high-value-panel')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-backlog-panel')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-reminder-panel')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-analysis-overview')).toHaveTextContent('2')
    expect(screen.getByTestId('workspace-default-template')).toHaveTextContent('快钱优先')
    expect(screen.getByTestId('workspace-template-performance')).toHaveTextContent('50%')
    expect(screen.getByTestId('workspace-digest-excerpt')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '机会工作台' })).toBeInTheDocument()
    expect(screen.getByText('AI 智能代理决策驾驶舱')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-action-card-recent')).toHaveTextContent('今日新增')
    expect(screen.getByTestId('workspace-action-card-backlog')).toHaveTextContent('推进积压')
    expect(screen.getByTestId('workspace-action-card-remind-overdue')).toHaveTextContent('超时提醒')
    expect(screen.getByTestId('workspace-today-actions')).toHaveTextContent('今日先做什么')
    expect(screen.getByTestId('workspace-agent-analysis-summary')).toHaveTextContent('Agent 分析摘要')
    expect(screen.getByTestId('workspace-untracked-high-value-panel')).toHaveTextContent('高价值待转化')
    expect(screen.getByTestId('workspace-backlog-panel')).toHaveTextContent('推进积压')
    expect(screen.queryByText('VigilAI Workspace')).not.toBeInTheDocument()
  })

  it('renders a cleaned digest excerpt instead of raw scraped noise', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    const excerpt = screen.getByTestId('workspace-digest-excerpt')

    expect((excerpt.textContent ?? '').length).toBeGreaterThan(0)
    expect(excerpt).not.toHaveTextContent(')](')
    expect(excerpt).not.toHaveTextContent('rmat=webp')
    expect(excerpt).not.toHaveTextContent('resize=400x300')
    expect(excerpt).not.toHaveTextContent('https://example.com/more')
  })

  it('supports refreshing the workspace', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

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
      expect(serviceMocks.createTracking).toHaveBeenCalledWith(
        'activity-1',
        expect.objectContaining({
          status: 'saved',
          stage: 'to_decide',
          next_action: expect.any(String),
          remind_at: null,
        })
      )
    })

    expect(screen.getByTestId('workspace-closure-feedback')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('workspace-favorite-activity-1'))

    await waitFor(() => {
      expect(serviceMocks.updateTracking).toHaveBeenCalledWith('activity-1', { is_favorited: true })
    })

    expect(screen.getByTestId('workspace-closure-feedback')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-closure-feedback')).toHaveTextContent('已加入收藏')
    expect(screen.getByTestId('workspace-closure-feedback').querySelector('a')).toHaveAttribute(
      'href',
      '/tracking?stage=to_decide'
    )
  })

  it('supports converting a high-value untracked opportunity into the tracking flow', async () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('workspace-convert-track-activity-1'))

    await waitFor(() => {
      expect(serviceMocks.createTracking).toHaveBeenCalledWith(
        'activity-1',
        expect.objectContaining({
          status: 'saved',
          stage: 'to_decide',
          next_action: expect.any(String),
          remind_at: null,
        })
      )
    })
  })

  it('supports pushing a today-action opportunity into the tracking flow', async () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('workspace-today-action-track-activity-2'))

    await waitFor(() => {
      expect(serviceMocks.createTracking).toHaveBeenCalledWith(
        'activity-2',
        expect.objectContaining({
          status: 'saved',
          stage: 'to_decide',
          next_action: expect.any(String),
        })
      )
    })

    expect(screen.getByTestId('workspace-closure-feedback')).toHaveTextContent('已加入推进')
  })

  it('renders action cards that route to the expected destinations', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('workspace-action-card-recent')).toHaveAttribute('href', '/activities?sort_by=created_at&sort_order=desc')
    expect(screen.getByTestId('workspace-action-card-high-value')).toHaveAttribute('href', '/activities?sort_by=score&sort_order=desc')
    expect(screen.getByTestId('workspace-action-card-due-soon')).toHaveAttribute('href', '/tracking?focus=due_soon')
    expect(screen.getByTestId('workspace-action-card-backlog')).toHaveAttribute('href', '/tracking?focus=backlog')
    expect(screen.getByTestId('workspace-action-card-remind-today')).toHaveAttribute('href', '/tracking?focus=remind_today')
    expect(screen.getByTestId('workspace-action-card-remind-overdue')).toHaveAttribute('href', '/tracking?focus=remind_overdue')
    expect(screen.getByTestId('workspace-action-card-alerts')).toHaveAttribute('href', '/sources')
  })

  it('surfaces reminder-driven tracking work on the workspace home', () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    const reminderPanel = screen.getByTestId('workspace-reminder-panel')

    expect(reminderPanel).toBeInTheDocument()
    expect(screen.getByTestId('workspace-action-card-remind-today')).toHaveTextContent('1')
    expect(screen.getByTestId('workspace-action-card-remind-overdue')).toHaveTextContent('1')
    expect(reminderPanel).toHaveTextContent('今日提醒')
    expect(screen.getByTestId('workspace-reminder-link-today')).toHaveAttribute('href', '/tracking?focus=remind_today')
    expect(screen.getByTestId('workspace-reminder-link-overdue')).toHaveAttribute('href', '/tracking?focus=remind_overdue')
    expect(screen.getByTestId('workspace-backlog-link-backlog')).toHaveAttribute('href', '/tracking?focus=backlog')
    expect(screen.getByTestId('workspace-backlog-link-to-decide')).toHaveAttribute(
      'href',
      '/tracking?focus=backlog&stage=to_decide'
    )
  })

  it('shows synced tracking feedback after cross-page updates', async () => {
    render(
      <MemoryRouter>
        <WorkspacePage />
      </MemoryRouter>
    )

    trackingHookState.current = buildTrackingHookState({
      items: buildTrackingItems().filter(item => item.activity_id !== 'tracking-3'),
    })
    workspaceHookState.current = buildWorkspaceHookState({
      workspace: {
        ...buildWorkspaceHookState().workspace!,
        overview: {
          ...buildWorkspaceHookState().workspace!.overview,
          tracked_count: 2,
        },
      },
    })

    await act(async () => {
      window.dispatchEvent(new CustomEvent('vigilai:tracking-updated'))
    })

    await waitFor(() => {
      expect(screen.getByTestId('workspace-sync-feedback')).not.toHaveTextContent('正在同步最新跟进结果...')
    })

    expect(screen.getByTestId('workspace-sync-feedback')).toHaveTextContent('2')
    expect(screen.getByTestId('workspace-sync-feedback')).toHaveTextContent('0')
  })
})
