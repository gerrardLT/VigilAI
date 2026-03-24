import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SourcesPage from './SourcesPage'

const apiMocks = vi.hoisted(() => ({
  refreshSource: vi.fn(),
  refreshAllSources: vi.fn(),
}))

const refetch = vi.fn()

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

vi.mock('../hooks/useSources', () => ({
  useSources: () => ({
    sources: [
      {
        id: 'devpost',
        name: 'Devpost',
        type: 'web',
        category: 'hackathon',
        status: 'success',
        last_run: '2026-03-24T08:00:00Z',
        last_success: '2026-03-24T08:00:00Z',
        activity_count: 12,
        error_message: null,
        health_score: 92,
        freshness_level: 'fresh',
        last_success_age_hours: 2,
        needs_attention: false,
      },
      {
        id: 'gitcoin',
        name: 'Gitcoin',
        type: 'web',
        category: 'grant',
        status: 'error',
        last_run: '2026-03-24T06:00:00Z',
        last_success: null,
        activity_count: 1,
        error_message: 'timeout',
        health_score: 28,
        freshness_level: 'critical',
        last_success_age_hours: null,
        needs_attention: true,
      },
    ],
    loading: false,
    error: null,
    refreshing: null,
    refreshSource: vi.fn(),
    refreshAllSources: vi.fn(),
    refetch,
  }),
}))

describe('SourcesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMocks.refreshAllSources.mockResolvedValue({ success: true, message: 'All refreshed' })
    apiMocks.refreshSource.mockResolvedValue({ success: true, message: 'Source refreshed' })
  })

  it('renders the V2 source health view and highlights alert sources', async () => {
    render(<SourcesPage />)

    expect(screen.getByText('来源健康')).toBeInTheDocument()
    expect(screen.getByText('监控来源可用性、刷新时效和异常来源。')).toBeInTheDocument()
    expect(screen.getByText('需要关注的来源')).toBeInTheDocument()
    expect(screen.getAllByText('Gitcoin').length).toBeGreaterThan(0)
    expect(screen.getAllByText('健康分 28').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByTestId('refresh-all-sources'))

    await waitFor(() => {
      expect(apiMocks.refreshAllSources).toHaveBeenCalled()
    })
    expect(refetch).toHaveBeenCalled()
  })
})
