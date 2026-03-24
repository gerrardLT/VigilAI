import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ActivitiesPage from './ActivitiesPage'

const apiMocks = vi.hoisted(() => ({
  getSources: vi.fn(),
  createTracking: vi.fn(),
  updateTracking: vi.fn(),
}))

const refetch = vi.fn()

vi.mock('../services/api', () => ({
  api: apiMocks,
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
      sort_by: 'score',
      sort_order: 'desc',
      page: 1,
    },
    setFilters: vi.fn(),
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
})
