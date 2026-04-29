import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SelectionTrackingPage from './SelectionTrackingPage'

const selectionApiMocks = vi.hoisted(() => ({
  getTracking: vi.fn(),
  updateTracking: vi.fn(),
  deleteTracking: vi.fn(),
}))

vi.mock('../../services/productSelectionApi', () => ({
  productSelectionApi: selectionApiMocks,
}))

describe('SelectionTrackingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    selectionApiMocks.getTracking.mockResolvedValue([
      {
        opportunity_id: 'sel-1',
        is_favorited: true,
        status: 'tracking',
        notes: 'watch seller behavior',
        next_action: 'compare 10 listings',
        remind_at: null,
        created_at: '2026-04-26T08:00:00Z',
        updated_at: '2026-04-26T08:00:00Z',
        opportunity: {
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
          reason_blocks: ['Demand looks strong and competition is manageable.'],
          recommended_action: 'Review 20 competitor SKUs before sourcing.',
          source_urls: ['https://item.taobao.com/item.htm?id=1'],
          source_mode: 'fallback',
          source_diagnostics: { fallback_reason: 'search_shell_only' },
          snapshot_at: '2026-04-26T08:00:00Z',
          created_at: '2026-04-26T08:00:00Z',
          updated_at: '2026-04-26T08:00:00Z',
          is_tracking: true,
          is_favorited: true,
        },
      },
    ])
    selectionApiMocks.updateTracking.mockResolvedValue({ status: 'done' })
    selectionApiMocks.deleteTracking.mockResolvedValue({ success: true })
  })

  it('renders tracking items with provenance badges', async () => {
    render(
      <MemoryRouter>
        <SelectionTrackingPage />
      </MemoryRouter>
    )

    expect(await screen.findByText('选品跟进')).toBeInTheDocument()
    expect(screen.getByText('Pet Water Fountain Filter Set')).toBeInTheDocument()
    expect(screen.getAllByText('回退').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/只有搜索壳页/i).length).toBeGreaterThan(0)
  })

  it('sends provenance filters when changed', async () => {
    render(
      <MemoryRouter initialEntries={['/selection/tracking?source_mode=fallback&fallback_reason=search_shell_only']}>
        <SelectionTrackingPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(selectionApiMocks.getTracking).toHaveBeenCalledWith(
        expect.objectContaining({ status: null, source_mode: 'fallback', fallback_reason: 'search_shell_only' })
      )
    })

    fireEvent.change(screen.getByLabelText('回退原因'), {
      target: { value: 'search_shell_only' },
    })
    await waitFor(() => {
      expect(selectionApiMocks.getTracking).toHaveBeenLastCalledWith(
        expect.objectContaining({
          source_mode: 'fallback',
          fallback_reason: 'search_shell_only',
        })
      )
    })
  })

  it('syncs tracking provenance filters back into the URL', async () => {
    const router = createMemoryRouter(
      [{ path: '/selection/tracking', element: <SelectionTrackingPage /> }],
      { initialEntries: ['/selection/tracking'] }
    )

    render(
      <RouterProvider router={router} />
    )

    await waitFor(() => {
      expect(selectionApiMocks.getTracking).toHaveBeenCalled()
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

  it('syncs tracking status back into the URL', async () => {
    const router = createMemoryRouter(
      [{ path: '/selection/tracking', element: <SelectionTrackingPage /> }],
      { initialEntries: ['/selection/tracking'] }
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(selectionApiMocks.getTracking).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByRole('button', { name: '已完成' }))

    await waitFor(() => {
      expect(router.state.location.search).toContain('status=done')
    })
  })
})
