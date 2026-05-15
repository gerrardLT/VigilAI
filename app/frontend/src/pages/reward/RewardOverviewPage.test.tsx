import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RewardOverviewPage from './RewardOverviewPage'

const rewardApiMocks = vi.hoisted(() => ({
  getOverview: vi.fn(),
}))

vi.mock('../../services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('RewardOverviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rewardApiMocks.getOverview.mockResolvedValue({
      source_count: 2,
      opportunity_count: 5,
      candidate_count: 6,
      high_value_count: 2,
      paused_source_count: 1,
      needs_attention_source_count: 1,
      today_crawled_count: 7,
      today_candidate_count: 4,
      today_deep_screened_count: 3,
      classification_distribution: { high_value: 2, needs_follow_up: 1 },
      source_health: { success: 1, error: 1 },
      failure_category_counts: { timeout: 1 },
      recommended_action_counts: { reduce_depth: 1 },
      source_health_trend_summary: { healthy: 1, cold: 1 },
      recent_high_value: [],
      recent_failed_jobs: [],
    })
  })

  it('renders overview cards', async () => {
    render(
      <MemoryRouter>
        <RewardOverviewPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(rewardApiMocks.getOverview).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('reward-overview-page')).toBeInTheDocument()
    expect(screen.getByText('奖励活动发现系统')).toBeInTheDocument()
    expect(screen.getByText('今日抓取')).toBeInTheDocument()
    expect(screen.getByText('来源健康分布')).toBeInTheDocument()
    expect(screen.getByText('失败分类分布')).toBeInTheDocument()
    expect(screen.getByText('建议动作分布')).toBeInTheDocument()
  })
})
