import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ActivityDetailPage from './ActivityDetailPage'

const apiMocks = vi.hoisted(() => ({
  getActivity: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: {
    getActivity: apiMocks.getActivity,
    createTracking: vi.fn(),
    updateTracking: vi.fn(),
    addDigestCandidate: vi.fn(),
    removeDigestCandidate: vi.fn(),
  },
}))

describe('ActivityDetailPage text wrapping', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('applies safe wrapping styles to summary and description text blocks', async () => {
    const longToken = 'VERYLONGTOKENWITHOUTSPACES'.repeat(20)

    apiMocks.getActivity.mockResolvedValue({
      id: 'activity-1',
      title: 'AI Hackathon',
      description: `Short description ${longToken}`,
      full_content: null,
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
      summary: `Summary ${longToken}`,
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

    const summary = screen.getByTestId('activity-summary')
    const description = screen.getByTestId('activity-description')

    expect(summary).toHaveTextContent(`Summary ${longToken}`)
    expect(description).toHaveTextContent(`Short description ${longToken}`)
    expect(summary.className).toContain('break-words')
    expect(description.className).toContain('break-words')
  })
})
