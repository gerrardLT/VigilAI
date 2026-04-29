import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useWorkspace } from './useWorkspace'

const apiMocks = vi.hoisted(() => ({
  getWorkspace: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

describe('useWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads the workspace snapshot on mount', async () => {
    apiMocks.getWorkspace.mockResolvedValue({
      overview: {
        total_activities: 12,
        total_sources: 3,
        activities_by_category: {},
        activities_by_source: {},
        recent_activities: 4,
        last_update: '2026-03-23T08:00:00Z',
        tracked_count: 2,
        favorited_count: 1,
      },
      top_opportunities: [],
      digest_preview: null,
      trends: [],
      alert_sources: [],
      first_actions: [],
    })

    const { result } = renderHook(() => useWorkspace())

    await waitFor(() => {
      expect(result.current.workspace?.overview.total_activities).toBe(12)
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('captures workspace loading errors', async () => {
    apiMocks.getWorkspace.mockRejectedValue(new Error('workspace failed'))

    const { result } = renderHook(() => useWorkspace())

    await waitFor(() => {
      expect(result.current.error).toContain('workspace failed')
    })

    expect(result.current.workspace).toBeNull()
    expect(result.current.loading).toBe(false)
  })

  it('refetches when tracking data changes elsewhere in the app', async () => {
    apiMocks.getWorkspace
      .mockResolvedValueOnce({
        overview: {
          total_activities: 12,
          total_sources: 3,
          activities_by_category: {},
          activities_by_source: {},
          recent_activities: 4,
          last_update: '2026-03-23T08:00:00Z',
          tracked_count: 2,
          favorited_count: 1,
        },
        top_opportunities: [],
        digest_preview: null,
        trends: [],
        alert_sources: [],
        first_actions: [],
      })
      .mockResolvedValueOnce({
        overview: {
          total_activities: 12,
          total_sources: 3,
          activities_by_category: {},
          activities_by_source: {},
          recent_activities: 4,
          last_update: '2026-03-23T08:05:00Z',
          tracked_count: 3,
          favorited_count: 1,
        },
        top_opportunities: [],
        digest_preview: null,
        trends: [],
        alert_sources: [],
        first_actions: [],
      })

    const { result } = renderHook(() => useWorkspace())

    await waitFor(() => {
      expect(result.current.workspace?.overview.tracked_count).toBe(2)
    })

    window.dispatchEvent(new CustomEvent('vigilai:tracking-updated'))

    await waitFor(() => {
      expect(result.current.workspace?.overview.tracked_count).toBe(3)
    })

    expect(apiMocks.getWorkspace).toHaveBeenCalledTimes(2)
  })
})
