import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TrackingPage from './TrackingPage'

const updateTracking = vi.fn()
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
        remind_at: null,
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
    deleteTracking,
  }),
}))

describe('TrackingPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-24T08:00:00Z'))
    updateTracking.mockReset()
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
    expect(screen.getByText('今日跟进焦点')).toBeInTheDocument()
    expect(screen.queryByText('Today Focus')).not.toBeInTheDocument()
    expect(screen.getByTestId('tracking-summary-due-today-count')).toHaveTextContent('1')
    expect(screen.getByTestId('tracking-summary-due-soon-count')).toHaveTextContent('2')
    expect(screen.getByTestId('tracking-summary-stale-count')).toHaveTextContent('1')
    expect(screen.getByTestId('tracking-alerts-panel')).toBeInTheDocument()
    expect(screen.getAllByText('今日截止').length).toBeGreaterThan(0)
    expect(screen.getAllByText('最近更新').length).toBeGreaterThan(0)
    expect(screen.getAllByText('长时间未处理').length).toBeGreaterThan(0)
  })

  it('filters the tracking list to due-soon items from the reminder actions', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('tracking-focus-due-soon'))

    const trackingList = within(screen.getByTestId('tracking-list'))

    expect(trackingList.getByText('AI 驻留计划')).toBeInTheDocument()
    expect(trackingList.getByText('资助冲刺')).toBeInTheDocument()
    expect(trackingList.queryByText('任务复核')).not.toBeInTheDocument()
  })

  it('renders tracked items and allows marking one as done', () => {
    render(
      <MemoryRouter>
        <TrackingPage />
      </MemoryRouter>
    )

    expect(within(screen.getByTestId('tracking-list')).getByText('AI 驻留计划')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('tracking-done-activity-1'))

    expect(updateTracking).toHaveBeenCalledWith('activity-1', { status: 'done' })
  })
})
