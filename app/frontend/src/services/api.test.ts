import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, ApiService } from './api'

declare const globalThis: {
  fetch: typeof fetch
}

function jsonResponse<T>(data: T, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data)),
  }
}

describe('ApiService', () => {
  const originalFetch = globalThis.fetch
  let api: ApiService

  beforeEach(() => {
    api = new ApiService('http://localhost:8000')
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('throws ApiError for HTTP failures', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse('missing', 404)) as typeof fetch

    await expect(api.getActivity('missing-id')).rejects.toMatchObject({
      statusCode: 404,
    })
  })

  it('throws ApiError for network failures', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down')) as typeof fetch

    await expect(api.getActivities()).rejects.toEqual(expect.any(ApiError))
    await expect(api.getActivities()).rejects.toMatchObject({
      statusCode: 0,
    })
  })

  it('serializes activity filters into the activities query string', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ total: 0, page: 1, page_size: 20, items: [] })
    ) as typeof fetch

    await api.getActivities({
      category: 'hackathon',
      search: 'ai',
      sort_by: 'score',
      sort_order: 'desc',
      page: 2,
      page_size: 10,
    })

    const requestUrl = new URL((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0])
    expect(requestUrl.pathname).toBe('/api/activities')
    expect(requestUrl.searchParams.get('category')).toBe('hackathon')
    expect(requestUrl.searchParams.get('search')).toBe('ai')
    expect(requestUrl.searchParams.get('sort_by')).toBe('score')
    expect(requestUrl.searchParams.get('page')).toBe('2')
    expect(requestUrl.searchParams.get('page_size')).toBe('10')
  })

  it('requests the workspace aggregate endpoint', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        overview: {
          total_activities: 1,
          total_sources: 1,
          activities_by_category: {},
          activities_by_source: {},
          recent_activities: 1,
          last_update: null,
          tracked_count: 0,
          favorited_count: 0,
        },
        top_opportunities: [],
        digest_preview: null,
        trends: [],
        alert_sources: [],
        first_actions: [],
      })
    ) as typeof fetch

    const workspace = await api.getWorkspace()

    expect(workspace.overview.recent_activities).toBe(1)
    expect((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]).toBe(
      'http://localhost:8000/api/workspace'
    )
  })

  it('creates tracking items with a JSON POST body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        activity_id: 'activity-1',
        is_favorited: true,
        status: 'tracking',
        notes: null,
        next_action: null,
        remind_at: null,
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      })
    ) as typeof fetch

    await api.createTracking('activity-1', { status: 'tracking', is_favorited: true })

    const [, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestInit).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ status: 'tracking', is_favorited: true }),
    })
  })

  it('updates tracking items with PATCH', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        activity_id: 'activity-1',
        is_favorited: false,
        status: 'done',
        notes: 'Submitted',
        next_action: null,
        remind_at: null,
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T09:00:00Z',
      })
    ) as typeof fetch

    await api.updateTracking('activity-1', { status: 'done', notes: 'Submitted' })

    const [requestUrl, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestUrl).toBe('http://localhost:8000/api/tracking/activity-1')
    expect(requestInit).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify({ status: 'done', notes: 'Submitted' }),
    })
  })

  it('deletes tracking items with DELETE', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({ success: true })) as typeof fetch

    const result = await api.deleteTracking('activity-1')

    const [, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestInit).toMatchObject({ method: 'DELETE' })
    expect(result.success).toBe(true)
  })

  it('lists digests and fetches a digest by id', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: 'digest-1', digest_date: '2026-03-23' }]))
      .mockResolvedValueOnce(jsonResponse({ id: 'digest-1', digest_date: '2026-03-23' })) as typeof fetch

    const digests = await api.getDigests()
    const digest = await api.getDigest('digest-1')

    expect(digests[0].id).toBe('digest-1')
    expect(digest.id).toBe('digest-1')
  })

  it('generates and sends digests with POST payloads', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 'digest-1', digest_date: '2026-03-23', status: 'draft' }))
      .mockResolvedValueOnce(jsonResponse({ id: 'digest-1', digest_date: '2026-03-23', status: 'sent' })) as typeof fetch

    await api.generateDigest({ digest_date: '2026-03-23' })
    await api.sendDigest('digest-1', { send_channel: 'manual' })

    const firstCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const secondCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[1]
    expect(firstCall[0]).toBe('http://localhost:8000/api/digests/generate')
    expect(firstCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ digest_date: '2026-03-23' }),
    })
    expect(secondCall[0]).toBe('http://localhost:8000/api/digests/digest-1/send')
    expect(secondCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ send_channel: 'manual' }),
    })
  })

  it('lists and mutates digest candidates', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: 'activity-1', title: 'AI Hackathon' }]))
      .mockResolvedValueOnce(jsonResponse({ success: true }))
      .mockResolvedValueOnce(jsonResponse({ success: true })) as typeof fetch

    const candidates = await api.getDigestCandidates('2026-03-23')
    await api.addDigestCandidate('activity-1', { digest_date: '2026-03-23' })
    await api.removeDigestCandidate('activity-1', { digest_date: '2026-03-23' })

    const firstCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const secondCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[1]
    const thirdCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[2]
    expect(candidates[0].id).toBe('activity-1')
    expect(firstCall[0]).toBe('http://localhost:8000/api/digests/candidates?digest_date=2026-03-23')
    expect(secondCall[0]).toBe('http://localhost:8000/api/digests/candidates/activity-1')
    expect(secondCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ digest_date: '2026-03-23' }),
    })
    expect(thirdCall[0]).toBe(
      'http://localhost:8000/api/digests/candidates/activity-1?digest_date=2026-03-23'
    )
    expect(thirdCall[1]).toMatchObject({ method: 'DELETE' })
  })
})
