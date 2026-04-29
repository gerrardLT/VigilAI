import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom'
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
      source_summary: {
        overall_mode: 'fallback',
        mode_counts: { live: 0, fallback: 1 },
        fallback_used: true,
        fallback_reasons: ['search_shell_only'],
        adapter_runs: [],
        extraction_stats_summary: {
          http_candidates_seen: 4,
          platform_candidates_seen: 1,
          accepted_candidates: 1,
          accepted_with_price: 1,
          accepted_without_price: 0,
          rejected_non_listing_url: 1,
          rejected_noise_title: 1,
          rejected_query_miss: 2,
          rejected_duplicate_url: 0,
        },
        seller_mix: {
          enterprise: 1,
          personal: 0,
          unknown: 0,
          with_sales_volume: 1,
          with_seller_count: 1,
        },
      },
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
          sales_volume: 320,
          seller_count: 14,
          seller_type: 'enterprise',
          seller_name: 'PetLab Official',
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
          source_mode: 'fallback',
          source_diagnostics: { fallback_reason: 'search_shell_only' },
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
      source_summary: {
        overall_mode: 'live',
        mode_counts: { live: 1, fallback: 0 },
        fallback_used: false,
        fallback_reasons: [],
        adapter_runs: [],
        extraction_stats_summary: {
          http_candidates_seen: 5,
          platform_candidates_seen: 2,
          accepted_candidates: 1,
          accepted_with_price: 1,
          accepted_without_price: 0,
          rejected_non_listing_url: 1,
          rejected_noise_title: 1,
          rejected_query_miss: 4,
          rejected_duplicate_url: 0,
        },
        seller_mix: {
          enterprise: 1,
          personal: 0,
          unknown: 0,
          with_sales_volume: 1,
          with_seller_count: 1,
        },
      },
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

    expect(await screen.findByText('选品机会池')).toBeInTheDocument()
    expect(screen.getByText('平台')).toBeInTheDocument()
    expect(screen.getByText('Pet Water Fountain Filter Set')).toBeInTheDocument()
    expect(screen.getAllByText('回退').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/未能完成实时提取/).length).toBeGreaterThan(0)
    expect(screen.getByText(/1 条采纳 \/ 5 条扫描/i)).toBeInTheDocument()
    expect(screen.getByText(/企业卖家/i)).toBeInTheDocument()
    expect(screen.getByText(/销量：320/i)).toBeInTheDocument()
  })

  it('sends provenance filters when source mode and fallback reason change', async () => {
    render(
      <MemoryRouter initialEntries={['/selection/opportunities?source_mode=fallback&fallback_reason=search_shell_only']}>
        <SelectionOpportunitiesPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(selectionApiMocks.getOpportunities).toHaveBeenCalledTimes(1)
    })
    expect(selectionApiMocks.getOpportunities).toHaveBeenLastCalledWith(
      expect.objectContaining({ source_mode: 'fallback', fallback_reason: 'search_shell_only' })
    )

    fireEvent.change(screen.getByLabelText('回退原因'), {
      target: { value: 'search_shell_only' },
    })
    await waitFor(() => {
      expect(selectionApiMocks.getOpportunities).toHaveBeenLastCalledWith(
        expect.objectContaining({
          source_mode: 'fallback',
          fallback_reason: 'search_shell_only',
        })
      )
    })
  })

  it('syncs provenance filters back into the URL', async () => {
    const router = createMemoryRouter(
      [{ path: '/selection/opportunities', element: <SelectionOpportunitiesPage /> }],
      { initialEntries: ['/selection/opportunities'] }
    )

    render(
      <RouterProvider router={router} />
    )

    await waitFor(() => {
      expect(selectionApiMocks.getOpportunities).toHaveBeenCalled()
    })

    fireEvent.change(screen.getByLabelText('来源模式'), { target: { value: 'fallback' } })
    fireEvent.change(screen.getByLabelText('回退原因'), {
      target: { value: 'search_shell_only' },
    })

    await waitFor(() => {
      expect(router.state.location.search).toContain('source_mode=fallback')
      expect(router.state.location.search).toContain('fallback_reason=search_shell_only')
    })
  })

  it('syncs platform, search, sort, and page back into the URL', async () => {
    const router = createMemoryRouter(
      [{ path: '/selection/opportunities', element: <SelectionOpportunitiesPage /> }],
      { initialEntries: ['/selection/opportunities'] }
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(selectionApiMocks.getOpportunities).toHaveBeenCalled()
    })

    fireEvent.change(screen.getByLabelText('平台'), { target: { value: 'taobao' } })
    fireEvent.change(screen.getByLabelText('排序'), { target: { value: 'created_at' } })
    fireEvent.change(screen.getByLabelText('搜索活动'), { target: { value: 'filter' } })

    await waitFor(() => {
      expect(router.state.location.search).toContain('platform=taobao')
      expect(router.state.location.search).toContain('sort_by=created_at')
      expect(router.state.location.search).toContain('search=filter')
    })
  })

  it('syncs research form state back into the URL', async () => {
    const router = createMemoryRouter(
      [{ path: '/selection/opportunities', element: <SelectionOpportunitiesPage /> }],
      { initialEntries: ['/selection/opportunities'] }
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(selectionApiMocks.getOpportunities).toHaveBeenCalled()
    })

    fireEvent.change(screen.getByLabelText('研究关键词'), { target: { value: 'desk lamp' } })
    fireEvent.change(screen.getByLabelText('查询类型'), { target: { value: 'category' } })
    fireEvent.change(screen.getByLabelText('平台范围'), { target: { value: 'taobao' } })

    await waitFor(() => {
      expect(router.state.location.search).toContain('query_text=desk+lamp')
      expect(router.state.location.search).toContain('query_type=category')
      expect(router.state.location.search).toContain('platform_scope=taobao')
    })
  })
})
