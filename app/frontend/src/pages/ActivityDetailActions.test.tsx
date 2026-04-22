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

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
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
      analysis_fields: {
        roi_level: 'high',
        solo_friendliness: 'solo_friendly',
      },
      analysis_status: 'passed',
      analysis_failed_layer: null,
      analysis_summary_reasons: ['Reward clarity passed', 'ROI score passed'],
      analysis_layer_results: [
        {
          key: 'hard_gate',
          label: 'Hard gate',
          decision: 'passed',
          reasons: ['Reward clarity passed'],
          score: 1,
        },
        {
          key: 'roi',
          label: 'ROI',
          decision: 'passed',
          reasons: ['ROI score passed'],
          score: 1,
        },
      ],
      analysis_score_breakdown: {
        hard_gate: 1,
        roi: 1,
      },
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
      expect(screen.getByText('AI 黑客松')).toBeInTheDocument()
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
      expect(screen.getByText('AI 黑客松')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('detail-digest-button'))

    await waitFor(() => {
      expect(apiMocks.addDigestCandidate).toHaveBeenCalledWith('activity-1')
    })
  })

  it('renders the analysis verdict and folded reasons from the detail payload', async () => {
    render(
      <MemoryRouter initialEntries={['/activities/activity-1']}>
        <Routes>
          <Route path="/activities/:id" element={<ActivityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('activity-analysis-panel')).toBeInTheDocument()
    })

    expect(screen.getByTestId('activity-analysis-status')).toHaveTextContent('通过')
    expect(screen.getByTestId('activity-analysis-template-context')).toHaveTextContent('快钱优先')
    expect(screen.getAllByText('奖励清晰度通过')).toHaveLength(2)
    expect(screen.getAllByText('回报评分通过')).toHaveLength(2)
    expect(screen.getByTestId('activity-analysis-chain')).toHaveTextContent('硬门槛')
    expect(screen.getByTestId('activity-analysis-chain')).toHaveTextContent('回报效率')
    expect(screen.getByTestId('activity-analysis-fields')).toHaveTextContent('单人友好度')
    expect(screen.getByTestId('activity-analysis-fields')).toHaveTextContent('适合单人')
    expect(screen.getByTestId('activity-analysis-adjust-link')).toHaveAttribute(
      'href',
      '/activities?analysis_status=passed'
    )
  })
})
