import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RewardOpportunityDetailPage from './RewardOpportunityDetailPage'

const rewardApiMocks = vi.hoisted(() => ({
  getOpportunity: vi.fn(),
}))

vi.mock('../../services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('RewardOpportunityDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rewardApiMocks.getOpportunity.mockResolvedValue({
      id: 'reward-1',
      title: 'Invite friends and get $25',
      source_platform: 'web',
      source_url: 'https://example.com/post/1',
      ai_stage_2_label: '高价值',
      ai_confidence: 0.82,
      reward_type: 'cash',
      reward_value_text: '$25',
      action_required: 'Invite three friends',
      ai_summary: 'Clear reward with action.',
      ai_risk_flags: ['deadline_missing'],
      ai_missing_evidence: ['rule_or_faq'],
      evidence: [
        {
          id: 'ev-1',
          opportunity_id: 'reward-1',
          evidence_type: 'reward',
          snippet: 'Receive a $25 cash reward.',
          source_url: 'https://example.com/post/1',
          created_at: '2026-05-01T10:00:00Z',
        },
      ],
      created_at: '2026-05-01T10:00:00Z',
    })
  })

  it('renders reward opportunity detail', async () => {
    render(
      <MemoryRouter initialEntries={['/rewards/opportunities/reward-1']}>
        <Routes>
          <Route path="/rewards/opportunities/:id" element={<RewardOpportunityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(rewardApiMocks.getOpportunity).toHaveBeenCalledWith('reward-1')
    })

    expect(await screen.findByTestId('reward-opportunity-detail-page')).toBeInTheDocument()
    expect(screen.getByText('Invite friends and get $25')).toBeInTheDocument()
    expect(screen.getByText('Invite three friends')).toBeInTheDocument()
    expect(screen.getByText('风险标记')).toBeInTheDocument()
    expect(screen.getByText('deadline_missing')).toBeInTheDocument()
  })
})
