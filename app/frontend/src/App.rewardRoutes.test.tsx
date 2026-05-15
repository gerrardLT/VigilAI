import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

const rewardApiMocks = vi.hoisted(() => ({
  getOverview: vi.fn(),
  listOpportunities: vi.fn(),
  getOpportunity: vi.fn(),
  getOperations: vi.fn(),
}))

vi.mock('./services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('App reward routes', () => {
  it('renders reward overview page at /rewards/overview', async () => {
    rewardApiMocks.getOverview.mockResolvedValue({
      source_count: 1,
      opportunity_count: 1,
      candidate_count: 1,
      high_value_count: 1,
      today_crawled_count: 1,
      today_candidate_count: 1,
      today_deep_screened_count: 1,
      classification_distribution: {},
      recent_high_value: [],
    })

    window.history.pushState({}, '', '/rewards/overview')
    render(<App />)

    await waitFor(() => {
      expect(rewardApiMocks.getOverview).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('reward-overview-page')).toBeInTheDocument()
  })
})
