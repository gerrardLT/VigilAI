import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SelectionWorkspacePage from './SelectionWorkspacePage'

const selectionApiMocks = vi.hoisted(() => ({
  getWorkspace: vi.fn(),
  createResearchJob: vi.fn(),
}))

vi.mock('../../services/productSelectionApi', () => ({
  productSelectionApi: selectionApiMocks,
}))

describe('SelectionWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    selectionApiMocks.getWorkspace.mockResolvedValue({
      overview: {
        query_count: 3,
        opportunity_count: 12,
        tracked_count: 2,
        favorited_count: 1,
      },
      recent_queries: [],
      top_opportunities: [],
      tracking_queue: [],
      platform_breakdown: [],
      source_summary: {
        overall_mode: 'mixed',
        mode_counts: { live: 2, fallback: 3 },
        fallback_used: true,
        fallback_reasons: ['search_shell_only'],
        adapter_runs: [],
        extraction_stats_summary: {
          http_candidates_seen: 12,
          platform_candidates_seen: 3,
          accepted_candidates: 5,
          accepted_with_price: 4,
          accepted_without_price: 1,
          rejected_non_listing_url: 2,
          rejected_noise_title: 1,
          rejected_query_miss: 7,
          rejected_duplicate_url: 0,
        },
        seller_mix: {
          enterprise: 2,
          personal: 1,
          unknown: 2,
          with_sales_volume: 3,
          with_seller_count: 2,
        },
      },
      top_opportunities_source_summary: {
        overall_mode: 'fallback',
        mode_counts: { live: 0, fallback: 5 },
        fallback_used: true,
        fallback_reasons: ['search_shell_only'],
        adapter_runs: [],
        extraction_stats_summary: {
          http_candidates_seen: 12,
          platform_candidates_seen: 3,
          accepted_candidates: 5,
          accepted_with_price: 4,
          accepted_without_price: 1,
          rejected_non_listing_url: 2,
          rejected_noise_title: 1,
          rejected_query_miss: 7,
          rejected_duplicate_url: 0,
        },
        seller_mix: {
          enterprise: 2,
          personal: 1,
          unknown: 2,
          with_sales_volume: 3,
          with_seller_count: 2,
        },
      },
      tracking_queue_source_summary: {
        overall_mode: 'live',
        mode_counts: { live: 2, fallback: 0 },
        fallback_used: false,
        fallback_reasons: [],
        adapter_runs: [],
        extraction_stats_summary: {
          http_candidates_seen: 2,
          platform_candidates_seen: 2,
          accepted_candidates: 2,
          accepted_with_price: 2,
          accepted_without_price: 0,
          rejected_non_listing_url: 0,
          rejected_noise_title: 0,
          rejected_query_miss: 0,
          rejected_duplicate_url: 0,
        },
        seller_mix: {
          enterprise: 1,
          personal: 1,
          unknown: 0,
          with_sales_volume: 2,
          with_seller_count: 1,
        },
      },
    })
    selectionApiMocks.createResearchJob.mockResolvedValue({
      job: {
        id: 'job-local-1',
        query_type: 'keyword',
        query_text: 'Mate X6',
        platform_scope: 'xianyu',
        status: 'completed',
        created_at: '2026-04-27T10:00:00Z',
        updated_at: '2026-04-27T10:00:01Z',
      },
      total: 3,
      items: [],
      source_summary: {
        overall_mode: 'live',
        mode_counts: { live: 3, fallback: 0 },
        fallback_used: false,
        fallback_reasons: [],
        adapter_runs: [],
        extraction_stats_summary: {
          http_candidates_seen: 3,
          platform_candidates_seen: 3,
          accepted_candidates: 3,
          accepted_with_price: 3,
          accepted_without_price: 0,
          rejected_non_listing_url: 0,
          rejected_noise_title: 0,
          rejected_query_miss: 0,
          rejected_duplicate_url: 0,
        },
        seller_mix: {
          enterprise: 1,
          personal: 2,
          unknown: 0,
          with_sales_volume: 3,
          with_seller_count: 1,
        },
      },
    })
  })

  it('renders workspace provenance summaries for top opportunities and tracking queue', async () => {
    render(
      <MemoryRouter>
        <SelectionWorkspacePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(selectionApiMocks.getWorkspace).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('selection-workspace-page')).toBeInTheDocument()
    expect(screen.getByText('高优先级机会来源')).toBeInTheDocument()
    expect(screen.getByText('跟进队列来源')).toBeInTheDocument()
      expect(screen.getAllByText('回退').length).toBeGreaterThan(0)
      expect(screen.getAllByText('实时').length).toBeGreaterThan(0)
      expect(
        screen.getAllByText((_, element) => element?.textContent?.includes('只有搜索壳页') ?? false)
        .length
      ).toBeGreaterThan(0)
    expect(screen.getByText('采纳商品数')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('企业 / 个人')).toBeInTheDocument()
    expect(document.querySelector('a[href="/selection/opportunities?source_mode=fallback&fallback_reason=search_shell_only"]')).toBeTruthy()
    expect(document.querySelector('a[href="/selection/tracking?source_mode=live"]')).toBeTruthy()
  })

  it('submits local fixture research input from the workspace panel', async () => {
    render(
      <MemoryRouter>
        <SelectionWorkspacePage />
      </MemoryRouter>
    )

    expect(await screen.findByTestId('selection-local-research-panel')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('查询词'), { target: { value: 'Mate X6' } })
    fireEvent.change(screen.getByLabelText('详情页 Manifest 路径'), {
      target: {
        value:
          'app/backend/tests/fixtures/product_selection/goofish_detail_pages.manifest.json',
      },
    })
    fireEvent.change(screen.getByLabelText('渲染搜索快照路径'), {
      target: { value: 'docs/goofish-rendered-search.html' },
    })

    fireEvent.click(screen.getByRole('button', { name: '运行样本研究' }))

    await waitFor(() => {
      expect(selectionApiMocks.createResearchJob).toHaveBeenCalledWith({
        query_type: 'keyword',
        query_text: 'Mate X6',
        platform_scope: 'xianyu',
        rendered_snapshot_path: 'docs/goofish-rendered-search.html',
        detail_snapshot_manifest_path:
          'app/backend/tests/fixtures/product_selection/goofish_detail_pages.manifest.json',
      })
    })

    expect(await screen.findByText(/任务 job-local-1 已完成/i)).toBeInTheDocument()
    expect(document.querySelector('a[href="/selection/opportunities?query_id=job-local-1"]')).toBeTruthy()
  })
})
