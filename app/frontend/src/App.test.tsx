import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./hooks/useActivities', () => ({
  useActivities: () => ({
    activities: [],
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 0,
    loading: false,
    error: null,
    filters: {},
    setFilters: vi.fn(),
    setPage: vi.fn(),
    refetch: vi.fn(),
  }),
}))

vi.mock('./hooks/useSources', () => ({
  useSources: () => ({
    sources: [],
    loading: false,
    error: null,
    refreshing: null,
    refreshSource: vi.fn(),
    refreshAllSources: vi.fn(),
    refetch: vi.fn(),
  }),
}))

vi.mock('./hooks/useStats', () => ({
  useStats: () => ({
    stats: {
      total_activities: 0,
      total_sources: 0,
      activities_by_category: {},
      activities_by_source: {},
      recent_activities: 0,
      last_update: null,
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
    lastRefresh: null,
  }),
}))

vi.mock('./hooks/useWorkspace', () => ({
  useWorkspace: () => ({
    workspace: {
      overview: {
        total_activities: 3,
        total_sources: 2,
        activities_by_category: {},
        activities_by_source: {},
        recent_activities: 1,
        last_update: null,
        tracked_count: 1,
        favorited_count: 1,
      },
      top_opportunities: [],
      digest_preview: null,
      trends: [],
      alert_sources: [],
      first_actions: [],
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('./hooks/useTracking', () => ({
  useTracking: () => ({
    items: [],
    loading: false,
    error: null,
    statusFilter: undefined,
    setStatusFilter: vi.fn(),
    refetch: vi.fn(),
    createTracking: vi.fn(),
    updateTracking: vi.fn(),
    deleteTracking: vi.fn(),
  }),
}))

vi.mock('./hooks/useDigests', () => ({
  useDigests: () => ({
    digests: [],
    loading: false,
    error: null,
    refetch: vi.fn(),
    getDigest: vi.fn(),
    generateDigest: vi.fn(),
    sendDigest: vi.fn(),
  }),
}))

vi.mock('./services/api', () => ({
  api: {
    getActivity: vi.fn().mockResolvedValue(null),
    getSources: vi.fn().mockResolvedValue([]),
    refreshSource: vi.fn(),
    refreshAllSources: vi.fn(),
  },
  ApiService: vi.fn(),
  ApiError: class ApiError extends Error {},
}))

describe('App routing', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/')
  })

  it('renders the workspace page at the root route and exposes V2 navigation', async () => {
    render(<App />)

    expect(await screen.findByTestId('workspace-page')).toBeInTheDocument()
    expect(document.querySelector('a[href="/activities"]')).toBeTruthy()
    expect(document.querySelector('a[href="/tracking"]')).toBeTruthy()
    expect(document.querySelector('a[href="/digests"]')).toBeTruthy()
  })
})
