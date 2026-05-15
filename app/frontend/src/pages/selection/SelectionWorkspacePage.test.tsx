import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SelectionWorkspacePage from './SelectionWorkspacePage'

const selectionApiMocks = vi.hoisted(() => ({
  getWorkspace: vi.fn(),
  createAutomationRun: vi.fn(),
  createOperationsRun: vi.fn(),
}))

vi.mock('../../services/productSelectionApi', () => ({
  productSelectionApi: selectionApiMocks,
}))

describe('SelectionWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    selectionApiMocks.getWorkspace
      .mockResolvedValueOnce({
        overview: {
          query_count: 3,
          opportunity_count: 12,
          tracked_count: 2,
          favorited_count: 1,
          due_tracking_count: 1,
        },
        recent_queries: [
          {
            id: 'job-1',
            query_type: 'keyword',
            query_text: 'pet water fountain',
            platform_scope: 'both',
            status: 'completed',
            created_at: '2026-04-26T08:00:00Z',
            updated_at: '2026-04-26T08:00:00Z',
          },
        ],
        top_opportunities: [
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
            is_tracking: true,
            is_favorited: false,
          },
        ],
        tracking_queue: [
          {
            opportunity_id: 'sel-1',
            is_favorited: false,
            status: 'tracking',
            notes: 'Need sourcing validation',
            next_action: 'Check return-rate risk',
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
              reason_blocks: ['Demand looks strong and competition is still manageable.'],
              recommended_action: 'Review 20 competitor SKUs before sourcing.',
              source_urls: ['https://item.taobao.com/item.htm?id=1'],
              snapshot_at: '2026-04-26T08:00:00Z',
              created_at: '2026-04-26T08:00:00Z',
              updated_at: '2026-04-26T08:00:00Z',
              is_tracking: true,
              is_favorited: false,
            },
          },
        ],
        due_tracking_queue: [
          {
            opportunity_id: 'sel-1',
            is_favorited: false,
            status: 'tracking',
            notes: 'Need sourcing validation',
            next_action: 'Check return-rate risk',
            remind_at: '2026-04-26T08:00:00Z',
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
              reason_blocks: ['Demand looks strong and competition is still manageable.'],
              recommended_action: 'Review 20 competitor SKUs before sourcing.',
              source_urls: ['https://item.taobao.com/item.htm?id=1'],
              snapshot_at: '2026-04-26T08:00:00Z',
              created_at: '2026-04-26T08:00:00Z',
              updated_at: '2026-04-26T08:00:00Z',
              is_tracking: true,
              is_favorited: false,
            },
          },
        ],
        platform_breakdown: [
          {
            platform: 'taobao',
            count: 1,
          },
        ],
        automation_runs: [
          {
            id: 'automation-1',
            session_id: null,
            domain_type: 'product_selection',
            job_type: 'selection_automation',
            status: 'completed',
            requested_by: 'scheduler',
            input_payload: {},
            result_payload: {
              triggered_queries: 2,
              candidate_count: 4,
              tracked_count: 1,
            },
            created_at: '2026-04-26T08:00:00Z',
            updated_at: '2026-04-26T08:00:00Z',
            finished_at: '2026-04-26T08:00:00Z',
          },
        ],
        operations_runs: [
          {
            id: 'ops-1',
            session_id: null,
            domain_type: 'product_selection',
            job_type: 'selection_tracking_ops',
            status: 'completed',
            requested_by: 'scheduler',
            input_payload: {},
            result_payload: {
              due_count: 1,
              processed_count: 1,
            },
            created_at: '2026-04-26T08:00:00Z',
            updated_at: '2026-04-26T08:00:00Z',
            finished_at: '2026-04-26T08:00:00Z',
          },
        ],
      })
      .mockResolvedValueOnce({
        overview: {
          query_count: 5,
          opportunity_count: 16,
          tracked_count: 3,
          favorited_count: 1,
          due_tracking_count: 2,
        },
        recent_queries: [
          {
            id: 'job-2',
            query_type: 'keyword',
            query_text: 'desk fan',
            platform_scope: 'both',
            status: 'completed',
            created_at: '2026-04-26T10:00:00Z',
            updated_at: '2026-04-26T10:00:00Z',
          },
        ],
        top_opportunities: [],
        tracking_queue: [],
        due_tracking_queue: [],
        platform_breakdown: [
          {
            platform: 'taobao',
            count: 2,
          },
        ],
        automation_runs: [
          {
            id: 'automation-2',
            session_id: null,
            domain_type: 'product_selection',
            job_type: 'selection_automation',
            status: 'completed',
            requested_by: 'selection_workspace',
            input_payload: {},
            result_payload: {
              triggered_queries: 3,
              candidate_count: 5,
              tracked_count: 2,
            },
            created_at: '2026-04-26T10:00:00Z',
            updated_at: '2026-04-26T10:00:00Z',
            finished_at: '2026-04-26T10:00:00Z',
          },
        ],
        operations_runs: [
          {
            id: 'ops-1',
            session_id: null,
            domain_type: 'product_selection',
            job_type: 'selection_tracking_ops',
            status: 'completed',
            requested_by: 'scheduler',
            input_payload: {},
            result_payload: {
              due_count: 1,
              processed_count: 1,
            },
            created_at: '2026-04-26T08:00:00Z',
            updated_at: '2026-04-26T08:00:00Z',
            finished_at: '2026-04-26T08:00:00Z',
          },
        ],
      })
      .mockResolvedValueOnce({
        overview: {
          query_count: 5,
          opportunity_count: 16,
          tracked_count: 3,
          favorited_count: 1,
          due_tracking_count: 0,
        },
        recent_queries: [
          {
            id: 'job-2',
            query_type: 'keyword',
            query_text: 'desk fan',
            platform_scope: 'both',
            status: 'completed',
            created_at: '2026-04-26T10:00:00Z',
            updated_at: '2026-04-26T10:00:00Z',
          },
        ],
        top_opportunities: [],
        tracking_queue: [],
        due_tracking_queue: [],
        platform_breakdown: [
          {
            platform: 'taobao',
            count: 2,
          },
        ],
        automation_runs: [
          {
            id: 'automation-2',
            session_id: null,
            domain_type: 'product_selection',
            job_type: 'selection_automation',
            status: 'completed',
            requested_by: 'selection_workspace',
            input_payload: {},
            result_payload: {
              triggered_queries: 3,
              candidate_count: 5,
              tracked_count: 2,
            },
            created_at: '2026-04-26T10:00:00Z',
            updated_at: '2026-04-26T10:00:00Z',
            finished_at: '2026-04-26T10:00:00Z',
          },
        ],
        operations_runs: [
          {
            id: 'ops-2',
            session_id: null,
            domain_type: 'product_selection',
            job_type: 'selection_tracking_ops',
            status: 'completed',
            requested_by: 'selection_workspace',
            input_payload: {},
            result_payload: {
              due_count: 2,
              processed_count: 2,
            },
            created_at: '2026-04-26T12:00:00Z',
            updated_at: '2026-04-26T12:00:00Z',
            finished_at: '2026-04-26T12:00:00Z',
          },
        ],
      })

    selectionApiMocks.createAutomationRun.mockResolvedValue({
      job: {
        id: 'automation-2',
        session_id: null,
        domain_type: 'product_selection',
        job_type: 'selection_automation',
        status: 'completed',
        requested_by: 'selection_workspace',
        input_payload: {},
        result_payload: {
          triggered_queries: 3,
          candidate_count: 5,
          tracked_count: 2,
        },
        created_at: '2026-04-26T10:00:00Z',
        updated_at: '2026-04-26T10:00:00Z',
        finished_at: '2026-04-26T10:00:00Z',
      },
      triggered_queries: 3,
      rerun_jobs: [],
      candidate_count: 5,
      tracked_count: 2,
      tracked_items: [],
    })

    selectionApiMocks.createOperationsRun.mockResolvedValue({
      job: {
        id: 'ops-2',
        session_id: null,
        domain_type: 'product_selection',
        job_type: 'selection_tracking_ops',
        status: 'completed',
        requested_by: 'selection_workspace',
        input_payload: {},
        result_payload: {
          due_count: 2,
          processed_count: 2,
        },
        created_at: '2026-04-26T12:00:00Z',
        updated_at: '2026-04-26T12:00:00Z',
        finished_at: '2026-04-26T12:00:00Z',
      },
      due_count: 2,
      processed_count: 2,
      processed_items: [],
    })
  })

  it('renders automation and operations runs and can trigger both cycles', async () => {
    render(
      <MemoryRouter>
        <SelectionWorkspacePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(selectionApiMocks.getWorkspace).toHaveBeenCalledTimes(1)
    })

    expect(await screen.findByText('Selection Workspace')).toBeInTheDocument()
    expect(screen.getByText('Automation Runs')).toBeInTheDocument()
    expect(screen.getByText('Tracking Operations')).toBeInTheDocument()
    expect(screen.getAllByText('Due Follow-Ups').length).toBeGreaterThan(0)
    expect(screen.getByText('automation-1')).toBeInTheDocument()
    expect(screen.getByText('Requested by scheduler | Candidates 4')).toBeInTheDocument()
    expect(screen.getByText('ops-1')).toBeInTheDocument()
    expect(screen.getByText('Requested by scheduler | Reminders refreshed 1')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Run Automation Cycle' }))

    await waitFor(() => {
      expect(selectionApiMocks.createAutomationRun).toHaveBeenCalledWith({
        requested_by: 'selection_workspace',
      })
    })

    await waitFor(() => {
      expect(selectionApiMocks.getWorkspace).toHaveBeenCalledTimes(2)
    })

    expect(
      await screen.findByText(
        'Triggered 3 reruns, shortlisted 5 candidates, and promoted 2 tracked items.'
      )
    ).toBeInTheDocument()
    expect(screen.getByText('automation-2')).toBeInTheDocument()
    expect(screen.getByText('Requested by selection_workspace | Candidates 5')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Run Tracking Review' }))

    await waitFor(() => {
      expect(selectionApiMocks.createOperationsRun).toHaveBeenCalledWith({
        requested_by: 'selection_workspace',
      })
    })

    await waitFor(() => {
      expect(selectionApiMocks.getWorkspace).toHaveBeenCalledTimes(3)
    })

    expect(
      await screen.findByText(
        'Reviewed 2 due tracking items and refreshed 2 follow-up reminders.'
      )
    ).toBeInTheDocument()
    expect(screen.getByText('ops-2')).toBeInTheDocument()
    expect(screen.getByText('Requested by selection_workspace | Reminders refreshed 2')).toBeInTheDocument()
  })
})
