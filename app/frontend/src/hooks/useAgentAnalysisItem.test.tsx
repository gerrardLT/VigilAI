import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAgentAnalysisItem } from './useAgentAnalysisItem'
import { useAgentAnalysisReview } from './useAgentAnalysisReview'

const apiMocks = vi.hoisted(() => ({
  getAgentAnalysisItem: vi.fn(),
  createAgentAnalysisJob: vi.fn(),
  approveAgentAnalysisItem: vi.fn(),
  rejectAgentAnalysisItem: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

describe('useAgentAnalysisItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads an agent-analysis item and reruns deep analysis for its activity', async () => {
    apiMocks.getAgentAnalysisItem.mockResolvedValue({
      id: 'item-1',
      job_id: 'job-1',
      activity_id: 'activity-1',
      status: 'completed',
      needs_research: true,
      final_draft_status: 'watch',
      created_at: '2026-03-28T08:00:00Z',
      updated_at: '2026-03-28T08:05:00Z',
      activity: {
        id: 'activity-1',
        title: 'Solo bug bounty with reward ambiguity',
      },
      draft: {
        status: 'watch',
        summary: 'Need manual review',
        reasons: ['Reward cap is unclear'],
        risk_flags: [],
        structured: { should_deep_research: true },
      },
      steps: [
        {
          id: 'step-1',
          job_item_id: 'item-1',
          step_type: 'screening',
          step_status: 'completed',
          output_payload: {},
          created_at: '2026-03-28T08:00:00Z',
        },
      ],
      evidence: [],
      reviews: [],
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
          activity_id: 'activity-1',
          status: 'completed',
          needs_research: false,
          final_draft_status: 'pass',
          created_at: '2026-03-28T09:00:00Z',
          updated_at: '2026-03-28T09:00:02Z',
          activity: {
            id: 'activity-1',
            title: 'Solo bug bounty with reward ambiguity',
          },
          draft: {
            status: 'pass',
            summary: 'Safe to pursue',
            reasons: ['Reward cap confirmed'],
            risk_flags: [],
            structured: { should_deep_research: false },
          },
          steps: [],
          evidence: [],
          reviews: [],
        },
      ],
    })

    const { result } = renderHook(() => useAgentAnalysisItem('item-1'))

    await waitFor(() => {
      expect(result.current.item?.id).toBe('item-1')
    })

    await act(async () => {
      await result.current.rerunItem({ template_id: 'tpl-1', requested_by: 'tester' })
    })

    expect(apiMocks.createAgentAnalysisJob).toHaveBeenCalledWith({
      scope_type: 'single',
      trigger_type: 'manual',
      activity_ids: ['activity-1'],
      template_id: 'tpl-1',
      requested_by: 'tester',
    })
    expect(result.current.item?.id).toBe('item-2')
    expect(result.current.lastJob?.id).toBe('job-2')
  })
})

describe('useAgentAnalysisReview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('approves and rejects items through the review hook', async () => {
    apiMocks.approveAgentAnalysisItem.mockResolvedValue({
      review_action: 'approved',
      item_id: 'item-1',
      activity_id: 'activity-1',
      review_note: 'approved',
      snapshot: {
        status: 'pass',
        summary: 'Safe to pursue',
        reasons: ['Reward confirmed'],
        risk_flags: [],
        structured: { should_deep_research: false },
      },
    })
    apiMocks.rejectAgentAnalysisItem.mockResolvedValue({
      review_action: 'rejected',
      item_id: 'item-1',
      activity_id: 'activity-1',
      review_note: 'needs rewrite',
      snapshot: null,
    })

    const { result } = renderHook(() => useAgentAnalysisReview())

    await act(async () => {
      await result.current.approveItem('item-1', { review_note: 'approved' })
    })

    await act(async () => {
      await result.current.rejectItem('item-1', { review_note: 'needs rewrite' })
    })

    expect(apiMocks.approveAgentAnalysisItem).toHaveBeenCalledWith('item-1', {
      review_note: 'approved',
    })
    expect(apiMocks.rejectAgentAnalysisItem).toHaveBeenCalledWith('item-1', {
      review_note: 'needs rewrite',
    })
    expect(result.current.reviewing).toBe(false)
    expect(result.current.error).toBeNull()
  })
})
