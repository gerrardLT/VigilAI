import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RewardOpportunitiesPage from './RewardOpportunitiesPage'

const rewardApiMocks = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getOpportunities: vi.fn(),
  getOperations: vi.fn(),
}))

vi.mock('../../services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('RewardOpportunitiesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rewardApiMocks.getOverview.mockResolvedValue({
      source_count: 1,
      opportunity_count: 1,
      candidate_count: 1,
      high_value_count: 1,
    })
    rewardApiMocks.getOpportunities.mockResolvedValue({
      items: [
        {
          id: 'reward-1',
          title: 'Invite friends and get $25',
          source_platform: 'web',
          source_url: 'https://example.com/post/1',
          ai_stage_2_label: '高价值',
          ai_confidence: 0.82,
          created_at: '2026-05-01T10:00:00Z',
        },
      ],
      total: 1,
    })
    rewardApiMocks.getOperations.mockResolvedValue({
      sources: [],
      recent_jobs: [],
    })
  })

  it('renders reward opportunities table', async () => {
    render(
      <MemoryRouter>
        <RewardOpportunitiesPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(rewardApiMocks.getOpportunities).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('reward-opportunities-page')).toBeInTheDocument()
    expect(screen.getByText('Invite friends and get $25')).toBeInTheDocument()
    expect(screen.getByText('82%')).toBeInTheDocument()
  })
})
