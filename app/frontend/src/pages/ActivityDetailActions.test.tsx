import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ActivityDetailPage from './ActivityDetailPage'

const apiMocks = vi.hoisted(() => ({
  getActivity: vi.fn(),
  createTracking: vi.fn(),
  updateTracking: vi.fn(),
  addDigestCandidate: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

describe('ActivityDetailPage tracking actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMocks.getActivity.mockResolvedValue({
      id: 'activity-1',
      title: 'AI Hackathon',
      description: 'Build an AI app.',
      full_content: 'Long description',
      source_id: 'devpost',
      source_name: 'Devpost',
      url: 'https://example.com/ai-hackathon',
      category: 'hackathon',
      tags: ['ai'],
      prize: null,
      dates: null,
      location: null,
      organizer: null,
      image_url: null,
      summary: 'Recommended for AI builders',
      score: 8.9,
      score_reason: 'Urgent and high trust',
      deadline_level: 'urgent',
      trust_level: 'high',
      updated_fields: [],
      is_tracking: false,
      is_favorited: false,
      is_digest_candidate: false,
      tracking: null,
      timeline: [],
      related_items: [],
      status: 'upcoming',
      created_at: '2026-03-23T08:00:00Z',
      updated_at: '2026-03-23T08:00:00Z',
    })
    apiMocks.createTracking.mockResolvedValue({
      activity_id: 'activity-1',
      is_favorited: false,
      status: 'tracking',
      notes: null,
      next_action: null,
      remind_at: null,
      created_at: '2026-03-23T08:00:00Z',
      updated_at: '2026-03-23T08:00:00Z',
    })
    apiMocks.updateTracking.mockResolvedValue({
      activity_id: 'activity-1',
      is_favorited: true,
      status: 'tracking',
      notes: null,
      next_action: null,
      remind_at: null,
      created_at: '2026-03-23T08:00:00Z',
      updated_at: '2026-03-23T08:00:00Z',
    })
    apiMocks.addDigestCandidate.mockResolvedValue({ success: true })
  })

  it('adds the activity to tracking and favorites from the detail page', async () => {
    render(
      <MemoryRouter initialEntries={['/activities/activity-1']}>
        <Routes>
          <Route path="/activities/:id" element={<ActivityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('AI Hackathon')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('detail-track-button'))
    fireEvent.click(screen.getByTestId('detail-favorite-button'))

    await waitFor(() => {
      expect(apiMocks.createTracking).toHaveBeenCalledWith('activity-1', { status: 'tracking' })
    })

    await waitFor(() => {
      expect(apiMocks.updateTracking).toHaveBeenCalledWith('activity-1', { is_favorited: true })
    })
  })

  it('adds the activity to today digest candidates from the detail page', async () => {
    render(
      <MemoryRouter initialEntries={['/activities/activity-1']}>
        <Routes>
          <Route path="/activities/:id" element={<ActivityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('AI Hackathon')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('detail-digest-button'))

    await waitFor(() => {
      expect(apiMocks.addDigestCandidate).toHaveBeenCalledWith('activity-1')
    })
  })
})
