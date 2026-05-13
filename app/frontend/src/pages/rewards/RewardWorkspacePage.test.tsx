import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RewardWorkspacePage from './RewardWorkspacePage'

const rewardApiMocks = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getOpportunities: vi.fn(),
  getOperations: vi.fn(),
}))

vi.mock('../../services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('RewardWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rewardApiMocks.getOverview.mockResolvedValue({
      source_count: 3,
      opportunity_count: 8,
      candidate_count: 12,
      high_value_count: 2,
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
      sources: [{ id: 'source-1' }],
      recent_jobs: [{ id: 'job-1' }],
    })
  })

  it('renders reward workspace overview cards', async () => {
    render(
      <MemoryRouter>
        <RewardWorkspacePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(rewardApiMocks.getOverview).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('reward-workspace-page')).toBeInTheDocument()
    expect(screen.getByText('奖励工作台')).toBeInTheDocument()
    expect(screen.getByText('Invite friends and get $25')).toBeInTheDocument()
  })
})
