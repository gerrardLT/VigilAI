import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SelectionOpportunitiesPage from './SelectionOpportunitiesPage'

const selectionApiMocks = vi.hoisted(() => ({
  getOpportunities: vi.fn(),
  createResearchJob: vi.fn(),
}))

vi.mock('../../services/productSelectionApi', () => ({
  productSelectionApi: selectionApiMocks,
}))

describe('SelectionOpportunitiesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    selectionApiMocks.getOpportunities.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [
        {
          id: 'sel-1',
          query_id: 'job-1',
          platform: 'taobao',
          platform_item_id: 'tb-1',
          title: 'Pet Water Fountain Filter Set',
          image_url: null,
          category_path: 'Pets/Water',
          price_low: 29,
          price_mid: 49,
          price_high: 69,
          demand_score: 82,
          competition_score: 41,
          price_fit_score: 76,
          risk_score: 24,
          cross_platform_signal_score: 72,
          opportunity_score: 78,
          confidence_score: 74,
          risk_tags: ['after-sale'],
          reason_blocks: ['Demand looks strong and competition is still manageable.'],
          recommended_action: 'Review 20 competitor SKUs before sourcing.',
          source_urls: ['https://item.taobao.com/item.htm?id=1'],
          snapshot_at: '2026-04-26T08:00:00Z',
          created_at: '2026-04-26T08:00:00Z',
          updated_at: '2026-04-26T08:00:00Z',
          is_tracking: false,
          is_favorited: false,
        },
      ],
    })

    selectionApiMocks.createResearchJob.mockResolvedValue({
      job: {
        id: 'job-1',
        query_type: 'keyword',
        query_text: 'pet water fountain',
        platform_scope: 'both',
        status: 'completed',
        created_at: '2026-04-26T08:00:00Z',
        updated_at: '2026-04-26T08:00:00Z',
      },
      total: 1,
      items: [],
    })
  })

  it('renders product selection opportunities with platform filters', async () => {
    render(
      <MemoryRouter>
        <SelectionOpportunitiesPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(selectionApiMocks.getOpportunities).toHaveBeenCalled()
    })

    expect(await screen.findByText('Selection Opportunity Pool')).toBeInTheDocument()
    expect(screen.getByText('Platform')).toBeInTheDocument()
    expect(screen.getByText('Pet Water Fountain Filter Set')).toBeInTheDocument()
  })
})
