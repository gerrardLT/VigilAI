import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAgentAnalysisJobs } from './useAgentAnalysisJobs'

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

const apiMocks = vi.hoisted(() => ({
  getAgentAnalysisJobs: vi.fn(),
  getAgentAnalysisJob: vi.fn(),
  createAgentAnalysisJob: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

describe('useAgentAnalysisJobs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads agent-analysis jobs and exposes refresh state', async () => {
    const deferred = createDeferred<{
      total: number
      items: Array<Record<string, unknown>>
    }>()

    apiMocks.getAgentAnalysisJobs
      .mockResolvedValueOnce({
        total: 1,
        items: [
          {
            id: 'job-1',
            trigger_type: 'scheduled',
            scope_type: 'batch',
            template_id: null,
            route_policy: {},
            budget_policy: {},
            status: 'completed',
            requested_by: null,
            created_at: '2026-03-28T08:00:00Z',
            finished_at: '2026-03-28T08:05:00Z',
            item_count: 4,
            completed_items: 4,
            failed_items: 0,
            needs_research_count: 2,
          },
        ],
      })
      .mockReturnValueOnce(deferred.promise)

    const { result } = renderHook(() => useAgentAnalysisJobs())

    await waitFor(() => {
      expect(result.current.jobs[0]?.id).toBe('job-1')
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.refreshing).toBe(false)
    expect(result.current.error).toBeNull()

    let refetchPromise: Promise<void> | undefined
    act(() => {
      refetchPromise = result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.refreshing).toBe(true)
    })

    deferred.resolve({
      total: 1,
      items: [
        {
          id: 'job-2',
          trigger_type: 'scheduled',
          scope_type: 'batch',
          template_id: null,
          route_policy: {},
          budget_policy: {},
          status: 'running',
          requested_by: null,
          created_at: '2026-03-28T09:00:00Z',
          finished_at: null,
          item_count: 3,
          completed_items: 1,
          failed_items: 0,
          needs_research_count: 1,
        },
      ],
    })

    await act(async () => {
      await refetchPromise
    })

    await waitFor(() => {
      expect(result.current.jobs[0]?.id).toBe('job-2')
    })

    expect(result.current.refreshing).toBe(false)
  })

  it('loads job detail and creates new agent-analysis jobs', async () => {
    apiMocks.getAgentAnalysisJobs.mockResolvedValue({
      total: 0,
      items: [],
    })
    apiMocks.getAgentAnalysisJob.mockResolvedValue({
      id: 'job-1',
      trigger_type: 'scheduled',
      scope_type: 'batch',
      template_id: null,
      route_policy: {},
      budget_policy: {},
      status: 'completed',
      requested_by: null,
      created_at: '2026-03-28T08:00:00Z',
      finished_at: '2026-03-28T08:05:00Z',
      item_count: 1,
      items: [
        {
          id: 'item-1',
          job_id: 'job-1',
          activity_id: 'activity-1',
          status: 'completed',
          needs_research: true,
          final_draft_status: 'watch',
          created_at: '2026-03-28T08:00:00Z',
          updated_at: '2026-03-28T08:05:00Z',
          activity: null,
          draft: null,
          steps: [],
          evidence: [],
          reviews: [],
        },
      ],
    })
    apiMocks.createAgentAnalysisJob.mockResolvedValue({
      id: 'job-2',
      trigger_type: 'manual',
      scope_type: 'single',
      template_id: 'tpl-1',
      route_policy: {},
      budget_policy: {},
      status: 'completed',
      requested_by: 'tester',
      created_at: '2026-03-28T09:00:00Z',
      finished_at: '2026-03-28T09:00:02Z',
      item_count: 1,
      items: [
        {
          id: 'item-2',
          job_id: 'job-2',
          activity_id: 'activity-2',
          status: 'completed',
          needs_research: false,
          final_draft_status: 'pass',
          created_at: '2026-03-28T09:00:00Z',
          updated_at: '2026-03-28T09:00:02Z',
          activity: null,
          draft: null,
          steps: [],
          evidence: [],
          reviews: [],
        },
      ],
    })

    const { result } = renderHook(() => useAgentAnalysisJobs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.loadJob('job-1')
    })

    expect(apiMocks.getAgentAnalysisJob).toHaveBeenCalledWith('job-1')
    expect(result.current.activeJob?.id).toBe('job-1')

    await act(async () => {
      await result.current.createJob({
        scope_type: 'single',
        trigger_type: 'manual',
        activity_ids: ['activity-2'],
        template_id: 'tpl-1',
        requested_by: 'tester',
      })
    })

    expect(apiMocks.createAgentAnalysisJob).toHaveBeenCalledWith({
      scope_type: 'single',
      trigger_type: 'manual',
      activity_ids: ['activity-2'],
      template_id: 'tpl-1',
      requested_by: 'tester',
    })
    expect(result.current.activeJob?.id).toBe('job-2')
  })
})
