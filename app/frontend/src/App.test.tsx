import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

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

vi.mock('./services/api', () => ({
  api: {
    getSources: vi.fn().mockResolvedValue([]),
    refreshSource: vi.fn(),
    refreshAllSources: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}))

describe('App routing', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/sources')
  })

  it('renders the retained sources page and only exposes the kept navigation domains', async () => {
    render(<App />)

    expect(await screen.findByRole('heading', { name: '来源健康' })).toBeInTheDocument()
    expect(document.querySelector('a[href="/agent"]')).toBeTruthy()
    expect(document.querySelector('a[href="/rewards/overview"]')).toBeTruthy()
    expect(document.querySelector('a[href="/selection/workspace"]')).toBeTruthy()
    expect(document.querySelector('a[href="/sources"]')).toBeTruthy()
    expect(document.querySelector('a[href="/activities"]')).toBeFalsy()
    expect(document.querySelector('a[href="/tracking"]')).toBeFalsy()
    expect(document.querySelector('a[href="/digests"]')).toBeFalsy()
    expect(document.querySelector('a[href="/analysis/results"]')).toBeFalsy()
  })
})
