import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ActivityDetailPage from './ActivityDetailPage'

const apiMocks = vi.hoisted(() => ({
  getActivity: vi.fn(),
  createTracking: vi.fn(),
  updateTracking: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

const baseActivity = {
  id: 'activity-1',
  title: 'AI Fellowship',
  description: 'Build an AI product.',
  full_content: 'Longer description for the opportunity.',
  source_id: 'devpost',
  source_name: 'Devpost',
  url: 'https://example.com/ai-fellowship',
  category: 'hackathon',
  tags: ['ai', 'builder'],
  prize: null,
  dates: null,
  location: null,
  organizer: 'Open Builders',
  image_url: null,
  summary: 'High fit for builder-focused teams.',
  score: 9.2,
  score_reason: 'Fresh, urgent, and high trust.',
  deadline_level: 'urgent',
  trust_level: 'high',
  updated_fields: [],
  timeline: [],
  related_items: [],
  status: 'upcoming',
  created_at: '2026-03-24T08:00:00Z',
  updated_at: '2026-03-24T08:00:00Z',
}

function renderDetailPage() {
  render(
    <MemoryRouter initialEntries={['/activities/activity-1']}>
      <Routes>
        <Route path="/activities/:id" element={<ActivityDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ActivityDetailPage planning actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('updates an existing tracking plan from the detail page', async () => {
    apiMocks.getActivity.mockResolvedValueOnce({
      ...baseActivity,
      is_tracking: true,
      is_favorited: true,
      tracking: {
        activity_id: 'activity-1',
        is_favorited: true,
        status: 'saved',
        notes: 'Review brief first.',
        next_action: 'Check eligibility',
        remind_at: '2026-03-25T09:30',
        created_at: '2026-03-24T08:00:00Z',
        updated_at: '2026-03-24T08:00:00Z',
      },
    })
    apiMocks.updateTracking.mockResolvedValueOnce({
      activity_id: 'activity-1',
      is_favorited: true,
      status: 'tracking',
      notes: 'Need portfolio and intro.',
      next_action: 'Submit shortlist',
      remind_at: '2026-03-26T10:30',
      created_at: '2026-03-24T08:00:00Z',
      updated_at: '2026-03-24T09:00:00Z',
    })

    renderDetailPage()

    await waitFor(() => {
      expect(screen.getByText('AI Fellowship')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText('跟进状态'), { target: { value: 'tracking' } })
    fireEvent.change(screen.getByLabelText('下一步动作'), { target: { value: 'Submit shortlist' } })
    fireEvent.change(screen.getByLabelText('提醒时间'), { target: { value: '2026-03-26T10:30' } })
    fireEvent.change(screen.getByLabelText('跟进备注'), {
      target: { value: 'Need portfolio and intro.' },
    })
    fireEvent.click(screen.getByTestId('detail-save-plan-button'))

    await waitFor(() => {
      expect(apiMocks.updateTracking).toHaveBeenCalledWith('activity-1', {
        status: 'tracking',
        next_action: 'Submit shortlist',
        remind_at: '2026-03-26T10:30',
        notes: 'Need portfolio and intro.',
      })
    })
  })

  it('creates a new tracking plan when the opportunity has not been tracked yet', async () => {
    apiMocks.getActivity.mockResolvedValueOnce({
      ...baseActivity,
      is_tracking: false,
      is_favorited: false,
      tracking: null,
    })
    apiMocks.createTracking.mockResolvedValueOnce({
      activity_id: 'activity-1',
      is_favorited: false,
      status: 'tracking',
      notes: null,
      next_action: 'Draft shortlist',
      remind_at: '2026-03-27T09:00',
      created_at: '2026-03-24T08:00:00Z',
      updated_at: '2026-03-24T09:00:00Z',
    })

    renderDetailPage()

    await waitFor(() => {
      expect(screen.getByText('AI Fellowship')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText('下一步动作'), { target: { value: 'Draft shortlist' } })
    fireEvent.change(screen.getByLabelText('提醒时间'), { target: { value: '2026-03-27T09:00' } })
    fireEvent.click(screen.getByTestId('detail-save-plan-button'))

    await waitFor(() => {
      expect(apiMocks.createTracking).toHaveBeenCalledWith('activity-1', {
        status: 'tracking',
        next_action: 'Draft shortlist',
        remind_at: '2026-03-27T09:00',
        notes: null,
      })
    })
  })
})
