import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useTracking } from './useTracking'

const apiMocks = vi.hoisted(() => ({
  getTracking: vi.fn(),
  createTracking: vi.fn(),
  updateTracking: vi.fn(),
  deleteTracking: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

const trackingItem = {
  activity_id: 'activity-1',
  is_favorited: true,
  status: 'tracking',
  notes: 'Prepare deck',
  next_action: 'Submit',
  remind_at: null,
  created_at: '2026-03-23T08:00:00Z',
  updated_at: '2026-03-23T08:00:00Z',
  activity: {
    id: 'activity-1',
    title: 'AI Hackathon',
    source_id: 'devpost',
    source_name: 'Devpost',
    url: 'https://example.com/a',
    category: 'hackathon',
    tags: [],
    status: 'upcoming',
    created_at: '2026-03-23T08:00:00Z',
    updated_at: '2026-03-23T08:00:00Z',
  },
}

describe('useTracking', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads tracking items on mount', async () => {
    apiMocks.getTracking.mockResolvedValue([trackingItem])

    const { result } = renderHook(() => useTracking())

    await waitFor(() => {
      expect(result.current.items).toHaveLength(1)
    })

    expect(apiMocks.getTracking).toHaveBeenCalledWith(undefined)
    expect(result.current.loading).toBe(false)
  })

  it('refreshes after creating a tracking item', async () => {
    apiMocks.getTracking.mockResolvedValue([trackingItem])
    apiMocks.createTracking.mockResolvedValue({
      activity_id: 'activity-1',
      status: 'tracking',
      is_favorited: true,
    })

    const { result } = renderHook(() => useTracking())

    await waitFor(() => {
      expect(result.current.items).toHaveLength(1)
    })

    await act(async () => {
      await result.current.createTracking('activity-1', {
        status: 'tracking',
        is_favorited: true,
      })
    })

    expect(apiMocks.createTracking).toHaveBeenCalledWith('activity-1', {
      status: 'tracking',
      is_favorited: true,
    })
    expect(apiMocks.getTracking).toHaveBeenCalledTimes(2)
  })

  it('refreshes after deleting a tracking item', async () => {
    apiMocks.getTracking.mockResolvedValue([])
    apiMocks.deleteTracking.mockResolvedValue({ success: true })

    const { result } = renderHook(() => useTracking())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.deleteTracking('activity-1')
    })

    expect(apiMocks.deleteTracking).toHaveBeenCalledWith('activity-1')
    expect(apiMocks.getTracking).toHaveBeenCalledTimes(2)
  })
})
