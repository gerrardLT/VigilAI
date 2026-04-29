import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TrackingPage from './TrackingPage'

const updateTracking = vi.fn()
const batchUpdateTracking = vi.fn()
const deleteTracking = vi.fn()
const setStatusFilter = vi.fn()

vi.mock('../hooks/useTracking', () => ({
  useTracking: () => ({
    items: [
      {
        activity_id: 'activity-1',
        is_favorited: true,
        status: 'tracking',
        notes: 'Need to submit by Friday',
        next_action: 'Prepare proposal',
        remind_at: '2026-03-24T09:00:00Z',
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
        activity: {
          id: 'activity-1',
          title: 'AI Fellowship',
          description: 'A strong fit for ML engineers.',
          source_id: 'source-1',
          source_name: 'Source One',
          url: 'https://example.com/fellowship',
          category: 'grant',
          tags: ['ml'],
          prize: null,
          dates: {
            start_date: null,
            end_date: null,
            deadline: '2026-03-24T12:00:00Z',
          },
          location: null,
          organizer: null,
          summary: 'Worth tracking',
          score: 8.4,
          score_reason: 'Strong fit',
          deadline_level: 'urgent',
          trust_level: 'high',
          updated_fields: [],
          is_tracking: true,
          is_favorited: true,
          status: 'upcoming',
          created_at: '2026-03-23T08:00:00Z',
          updated_at: '2026-03-23T08:00:00Z',
        },
      },
      {
        activity_id: 'activity-2',
        is_favorited: false,
        status: 'saved',
        notes: null,
        next_action: 'Submit budget',
        remind_at: null,
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-24T02:00:00Z',
        activity: {
          id: 'activity-2',
          title: 'Grant Sprint',
          description: 'Funding round for builders.',
          source_id: 'source-2',
          source_name: 'Source Two',
          url: 'https://example.com/grant',
          category: 'grant',
          tags: ['funding'],
          prize: null,
          dates: {
            start_date: null,
            end_date: null,
            deadline: '2026-03-26T10:00:00Z',
          },
          location: null,
          organizer: null,
          summary: 'Updated budget requirement',
          score: 7.9,
          score_reason: 'Upcoming funding',
          deadline_level: 'soon',
          trust_level: 'high',
          updated_fields: ['prize'],
          is_tracking: true,
          is_favorited: false,
          status: 'upcoming',
          created_at: '2026-03-23T08:00:00Z',
          updated_at: '2026-03-24T02:00:00Z',
        },
      },
      {
        activity_id: 'activity-3',
        is_favorited: false,
        status: 'tracking',
        notes: 'Waiting for teammate input',
        next_action: 'Review partner feedback',
        remind_at: '2026-03-23T07:00:00Z',
        created_at: '2026-03-20T08:00:00Z',
        updated_at: '2026-03-19T08:00:00Z',
        activity: {
          id: 'activity-3',
          title: 'Quest Review',
          description: 'Community quest backlog.',
          source_id: 'source-3',
          source_name: 'Source Three',
          url: 'https://example.com/quest',
          category: 'bounty',
          tags: ['quest'],
          prize: null,
          dates: {
            start_date: null,
            end_date: null,
            deadline: '2026-04-02T10:00:00Z',
          },
          location: null,
          organizer: null,
          summary: 'Long time no progress',
          score: 6.2,
          score_reason: 'Needs a decision',
          deadline_level: 'later',
          trust_level: 'medium',
          updated_fields: [],
          is_tracking: true,
          is_favorited: false,
          status: 'upcoming',
          created_at: '2026-03-20T08:00:00Z',
          updated_at: '2026-03-19T08:00:00Z',
        },
      },
    ],
    loading: false,
    error: null,
    statusFilter: undefined,
    setStatusFilter,
    refetch: vi.fn(),
    createTracking: vi.fn(),
    updateTracking,
    batchUpdateTracking,
    deleteTracking,
  }),
}))

describe('TrackingPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-24T08:00:00Z'))
    updateTracking.mockReset()
    batchUpdateTracking.mockReset()
    deleteTracking.mockReset()
    setStatusFilter.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders reminder summaries and the right-side alerts panel', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('tracking-page')).toBeInTheDocument()
    expect(screen.getByTestId('tracking-reminder-strip')).toBeInTheDocument()
    expect(screen.getByTestId('tracking-backlog-panel')).toBeInTheDocument()
    expect(screen.getByText('今日跟进焦点')).toBeInTheDocument()
    expect(screen.getByTestId('tracking-focus-due-soon')).toBeInTheDocument()
    expect(screen.queryByText('Today Focus')).not.toBeInTheDocument()
    expect(screen.getByTestId('tracking-summary-due-today-count')).toHaveTextContent('1')
    expect(screen.getByTestId('tracking-summary-due-soon-count')).toHaveTextContent('2')
    expect(screen.getByTestId('tracking-summary-remind-today-count')).toHaveTextContent('1')
    expect(screen.getByTestId('tracking-summary-remind-overdue-count')).toHaveTextContent('1')
    expect(screen.getByTestId('tracking-summary-stale-count')).toHaveTextContent('1')
    expect(screen.getByTestId('tracking-alerts-panel')).toBeInTheDocument()
    expect(screen.getAllByText('今日截止').length).toBeGreaterThan(0)
    expect(screen.getByTestId('tracking-focus-remind-overdue')).toBeInTheDocument()
    expect(screen.getAllByText('长时间未处理').length).toBeGreaterThan(0)
    expect(screen.getByText('查看全部')).toBeInTheDocument()
  })

  it('filters the tracking list to due-soon items from the reminder actions', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('tracking-focus-due-soon'))

    const trackingList = within(screen.getByTestId('tracking-list'))

    expect(trackingList.getByTestId('tracking-card-activity-1')).toBeInTheDocument()
    expect(trackingList.getByTestId('tracking-card-activity-2')).toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-3')).not.toBeInTheDocument()
  })

  it('filters the tracking list to overdue reminder items', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('tracking-focus-remind-overdue'))

    const trackingList = within(screen.getByTestId('tracking-list'))

    expect(trackingList.getByTestId('tracking-card-activity-3')).toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-1')).not.toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-2')).not.toBeInTheDocument()
  })

  it('reads the focus filter from the URL query', () => {
    render(
      <MemoryRouter initialEntries={['/tracking?focus=remind_overdue']}>
        <TrackingPage />
      </MemoryRouter>
    )

    const trackingList = within(screen.getByTestId('tracking-list'))

    expect(trackingList.getByTestId('tracking-card-activity-3')).toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-1')).not.toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-2')).not.toBeInTheDocument()
    expect(screen.getByTestId('tracking-entry-feedback')).toHaveTextContent('超时提醒')
  })

  it('reads the stage filter from the URL query', () => {
    render(
      <MemoryRouter initialEntries={['/tracking?stage=to_decide']}>
        <TrackingPage />
      </MemoryRouter>
    )

    const trackingList = within(screen.getByTestId('tracking-list'))

    expect(trackingList.getByTestId('tracking-card-activity-2')).toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-1')).not.toBeInTheDocument()
    expect(trackingList.queryByTestId('tracking-card-activity-3')).not.toBeInTheDocument()
    expect(screen.getByTestId('tracking-entry-feedback')).toHaveTextContent('待判断')
  })

  it('surfaces backlog context when entering from the workspace backlog link', () => {
    render(
      <MemoryRouter initialEntries={['/tracking?focus=backlog']}>
        <TrackingPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('tracking-entry-feedback')).toHaveTextContent('推进积压')
    expect(screen.getByTestId('tracking-entry-feedback')).toHaveTextContent('下一步')
  })

  it('renders tracked items and allows marking one as done', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    expect(within(screen.getByTestId('tracking-list')).getByTestId('tracking-card-activity-1')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('tracking-done-activity-1'))

    expect(updateTracking).toHaveBeenCalledWith('activity-1', { status: 'done', stage: 'submitted' })
  })

  it('supports batch stage updates for selected tracking items', async () => {
    batchUpdateTracking.mockResolvedValue(true)

    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('tracking-select-activity-1'))
    fireEvent.click(screen.getByTestId('tracking-select-activity-2'))
    fireEvent.change(screen.getByTestId('tracking-batch-next-action'), {
      target: { value: '浠婃櫄鍓嶇‘璁よ祫鏍煎苟鏁寸悊鏉愭枡' },
    })

    expect(screen.getByTestId('tracking-batch-toolbar')).toBeInTheDocument()

    await act(async () => {
      fireEvent.click(screen.getByTestId('tracking-batch-preparing'))
      await Promise.resolve()
    })

    expect(batchUpdateTracking).toHaveBeenCalledWith(['activity-1', 'activity-2'], {
      status: 'tracking',
      stage: 'preparing',
      next_action: '浠婃櫄鍓嶇‘璁よ祫鏍煎苟鏁寸悊鏉愭枡',
      remind_at: undefined,
    })
    expect(screen.getByTestId('tracking-closure-feedback')).toHaveTextContent('批量')
    expect(screen.getByTestId('tracking-closure-feedback')).toHaveTextContent('准备参与')
  })

  it('can fill a suggested batch action for selected tracking items', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('tracking-select-activity-1'))
    fireEvent.click(screen.getByTestId('tracking-batch-fill-suggestion'))

    expect(screen.getByTestId('tracking-batch-next-action')).not.toHaveValue('')
  })
  it('saves block and abandon reasons on a tracking card', async () => {
    updateTracking.mockResolvedValue({
      activity_id: 'activity-1',
      is_favorited: true,
      status: 'archived',
      stage: 'dropped',
      notes: 'Need to submit by Friday',
      next_action: 'Prepare proposal',
      remind_at: '2026-03-24T09:00',
      block_reason: 'Waiting on docs',
      abandon_reason: 'ROI too low',
      created_at: '2026-03-23T08:00:00Z',
      updated_at: '2026-03-24T08:30:00Z',
    })

    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByTestId('tracking-stage-activity-1'), { target: { value: 'dropped' } })
    fireEvent.change(screen.getByTestId('tracking-block-reason-activity-1'), {
      target: { value: 'Waiting on docs' },
    })
    fireEvent.change(screen.getByTestId('tracking-abandon-reason-activity-1'), {
      target: { value: 'ROI too low' },
    })
    await act(async () => {
      fireEvent.click(screen.getByTestId('tracking-save-activity-1'))
      await Promise.resolve()
    })

    expect(updateTracking).toHaveBeenCalledWith('activity-1', {
      status: 'archived',
      stage: 'dropped',
      next_action: 'Prepare proposal',
      remind_at: '2026-03-24T17:00',
      block_reason: 'Waiting on docs',
      abandon_reason: 'ROI too low',
    })
    expect(screen.getByTestId('tracking-closure-feedback')).toHaveTextContent('放弃')
    expect(screen.getByTestId('tracking-closure-feedback')).toHaveTextContent('查看已放弃')
  })
})
