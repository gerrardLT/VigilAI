import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RewardOpportunitiesPage from './RewardOpportunitiesPage'

const rewardApiMocks = vi.hoisted(() => ({
  listOpportunities: vi.fn(),
}))

vi.mock('../../services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('RewardOpportunitiesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rewardApiMocks.listOpportunities.mockResolvedValue({
      items: [
        {
          id: 'reward-1',
          title: 'Invite friends and get $25',
          source_platform: 'web',
          source_url: 'https://example.com/post/1',
          ai_stage_2_label: '高价值',
          ai_confidence: 0.82,
          ai_summary: 'Clear invite reward.',
          created_at: '2026-05-01T10:00:00Z',
        },
      ],
      total: 1,
    })
  })

  it('renders reward opportunities list', async () => {
    render(
      <MemoryRouter>
        <RewardOpportunitiesPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(rewardApiMocks.listOpportunities).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('reward-opportunities-page')).toBeInTheDocument()
    expect(screen.getByText('Invite friends and get $25')).toBeInTheDocument()
    expect(screen.getByText('置信度 82%')).toBeInTheDocument()
    expect(screen.getAllByText('高价值').length).toBeGreaterThan(0)
  })
})
