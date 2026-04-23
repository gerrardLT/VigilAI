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

  it('serializes extended activity filters into the activities query string', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ total: 0, page: 1, page_size: 20, items: [] })
    ) as typeof fetch

    await api.getActivities({
      prize_range: '500-2000',
      solo_friendliness: 'solo_friendly',
      reward_clarity: 'high',
      effort_level: 'low',
      remote_mode: 'remote',
    })

    const requestUrl = new URL((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0])
    expect(requestUrl.searchParams.get('prize_range')).toBe('500-2000')
    expect(requestUrl.searchParams.get('solo_friendliness')).toBe('solo_friendly')
    expect(requestUrl.searchParams.get('reward_clarity')).toBe('high')
    expect(requestUrl.searchParams.get('effort_level')).toBe('low')
    expect(requestUrl.searchParams.get('remote_mode')).toBe('remote')
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

  it('lists, duplicates, and activates analysis templates', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: 'tpl-1', slug: 'quick-money' }]))
      .mockResolvedValueOnce(jsonResponse({ id: 'tpl-1', slug: 'quick-money' }))
      .mockResolvedValueOnce(jsonResponse({ id: 'tpl-2', name: 'Quick money copy' }))
      .mockResolvedValueOnce(jsonResponse({ id: 'tpl-2', is_default: true })) as typeof fetch

    const templates = await api.getAnalysisTemplates()
    const current = await api.getDefaultAnalysisTemplate()
    const duplicated = await api.duplicateAnalysisTemplate('tpl-1', 'Quick money copy')
    const activated = await api.activateAnalysisTemplate('tpl-2')

    expect(templates[0].slug).toBe('quick-money')
    expect(current.id).toBe('tpl-1')
    expect(duplicated.name).toBe('Quick money copy')
    expect(activated.id).toBe('tpl-2')

    const duplicateCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[2]
    const activateCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[3]
    expect(duplicateCall[0]).toBe(
      'http://localhost:8000/api/analysis/templates/tpl-1/duplicate'
    )
    expect(duplicateCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ name: 'Quick money copy' }),
    })
    expect(activateCall[0]).toBe(
      'http://localhost:8000/api/analysis/templates/tpl-2/activate'
    )
    expect(activateCall[1]).toMatchObject({ method: 'POST' })
  })

  it('updates and deletes analysis templates', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 'tpl-2', name: 'Safe trust v2', slug: 'safe-trust-v2' }))
      .mockResolvedValueOnce(jsonResponse({ success: true })) as typeof fetch

    const updated = await api.updateAnalysisTemplate('tpl-2', { name: 'Safe trust v2' })
    const deleted = await api.deleteAnalysisTemplate('tpl-2')

    const updateCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const deleteCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[1]
    expect(updated.name).toBe('Safe trust v2')
    expect(updateCall[0]).toBe('http://localhost:8000/api/analysis/templates/tpl-2')
    expect(updateCall[1]).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify({ name: 'Safe trust v2' }),
    })
    expect(deleteCall[0]).toBe('http://localhost:8000/api/analysis/templates/tpl-2')
    expect(deleteCall[1]).toMatchObject({ method: 'DELETE' })
    expect(deleted).toEqual({ success: true })
  })

  it('triggers a full analysis rerun', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ success: true, processed: 12 })
    ) as typeof fetch

    const result = await api.runAnalysis()

    const [requestUrl, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestUrl).toBe('http://localhost:8000/api/analysis/run')
    expect(requestInit).toMatchObject({ method: 'POST' })
    expect(result).toEqual({ success: true, processed: 12 })
  })

  it('loads a template analysis preview', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ template_id: 'tpl-1', total: 12, passed: 5, watch: 4, rejected: 3 })
    ) as typeof fetch

    const result = await api.previewAnalysisTemplate('tpl-1')

    const [requestUrl, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestUrl).toBe('http://localhost:8000/api/analysis/templates/tpl-1/preview')
    expect(requestInit).toMatchObject({})
    expect(result).toEqual({ template_id: 'tpl-1', total: 12, passed: 5, watch: 4, rejected: 3 })
  })

  it('loads a draft template preview from a payload', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ template_id: 'draft-template', total: 12, passed: 6, watch: 3, rejected: 3 })
    ) as typeof fetch

    const result = await api.previewDraftAnalysisTemplate({
      id: 'draft-template',
      name: 'Draft template',
      layers: [],
      sort_fields: ['roi_score'],
    })

    const [requestUrl, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestUrl).toBe('http://localhost:8000/api/analysis/templates/preview')
    expect(requestInit).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        id: 'draft-template',
        name: 'Draft template',
        layers: [],
        sort_fields: ['roi_score'],
      }),
    })
    expect(result).toEqual({ template_id: 'draft-template', total: 12, passed: 6, watch: 3, rejected: 3 })
  })

  it('loads draft template preview results for specific activities', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        template_id: 'draft-template',
        total: 2,
        passed: 1,
        watch: 0,
        rejected: 1,
        items: [
          {
            activity_id: 'activity-1',
            status: 'passed',
            failed_layer: null,
            summary_reasons: ['Reward clarity passed'],
            layer_results: [],
          },
          {
            activity_id: 'activity-2',
            status: 'rejected',
            failed_layer: 'hard_gate',
            summary_reasons: ['Solo only failed hard gate'],
            layer_results: [],
          },
        ],
      })
    ) as typeof fetch

    const result = await api.previewDraftAnalysisTemplateResults({
      id: 'draft-template',
      name: 'Draft template',
      activity_ids: ['activity-1', 'activity-2'],
      layers: [],
    })

    const [requestUrl, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestUrl).toBe('http://localhost:8000/api/analysis/templates/preview/results')
    expect(requestInit).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        id: 'draft-template',
        name: 'Draft template',
        activity_ids: ['activity-1', 'activity-2'],
        layers: [],
      }),
    })
    expect(result.items[1].status).toBe('rejected')
    expect(result.items[1].failed_layer).toBe('hard_gate')
  })

  it('loads analysis results list and detail endpoints', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          total: 1,
          page: 1,
          page_size: 20,
          items: [
            {
              id: 'activity-1',
              title: 'AI Hackathon',
              analysis_status: 'passed',
              analysis_layer_results: [],
              analysis_score_breakdown: {},
            },
          ],
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'activity-1',
          title: 'AI Hackathon',
          analysis_status: 'passed',
          analysis_layer_results: [],
          analysis_score_breakdown: {},
        })
      ) as typeof fetch

    const results = await api.getAnalysisResults({ analysis_status: 'passed', page: 1, page_size: 20 })
    const detail = await api.getAnalysisResult('activity-1')

    const firstCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const secondCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[1]
    expect(firstCall[0]).toBe(
      'http://localhost:8000/api/analysis/results?analysis_status=passed&page=1&page_size=20'
    )
    expect(secondCall[0]).toBe('http://localhost:8000/api/analysis/results/activity-1')
    expect(results.items[0].analysis_status).toBe('passed')
    expect(detail.id).toBe('activity-1')
  })

  it('creates and loads agent-analysis jobs and item detail', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'job-1',
          trigger_type: 'manual',
          scope_type: 'single',
          template_id: 'tpl-1',
          route_policy: {},
          budget_policy: {},
          status: 'completed',
          requested_by: 'tester',
          created_at: '2026-03-28T08:00:00Z',
          finished_at: '2026-03-28T08:00:02Z',
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
              updated_at: '2026-03-28T08:00:02Z',
              draft: {
                status: 'watch',
                summary: 'Need manual review',
                reasons: ['Reward cap is unclear'],
                risk_flags: [],
                structured: { should_deep_research: true },
              },
              steps: [],
              evidence: [],
              reviews: [],
            },
          ],
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          total: 1,
          items: [
            {
              id: 'job-1',
              trigger_type: 'manual',
              scope_type: 'single',
              template_id: 'tpl-1',
              route_policy: {},
              budget_policy: {},
              status: 'completed',
              requested_by: 'tester',
              created_at: '2026-03-28T08:00:00Z',
              finished_at: '2026-03-28T08:00:02Z',
              item_count: 1,
              completed_items: 1,
              failed_items: 0,
              needs_research_count: 1,
            },
          ],
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'job-1',
          trigger_type: 'manual',
          scope_type: 'single',
          template_id: 'tpl-1',
          route_policy: {},
          budget_policy: {},
          status: 'completed',
          requested_by: 'tester',
          created_at: '2026-03-28T08:00:00Z',
          finished_at: '2026-03-28T08:00:02Z',
          item_count: 1,
          items: [],
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'item-1',
          job_id: 'job-1',
          activity_id: 'activity-1',
          status: 'completed',
          needs_research: true,
          final_draft_status: 'watch',
          created_at: '2026-03-28T08:00:00Z',
          updated_at: '2026-03-28T08:00:02Z',
          activity: null,
          draft: {
            status: 'watch',
            summary: 'Need manual review',
            reasons: ['Reward cap is unclear'],
            risk_flags: [],
            structured: { should_deep_research: true },
          },
          steps: [],
          evidence: [],
          reviews: [],
        })
      ) as typeof fetch

    const created = await api.createAgentAnalysisJob({
      scope_type: 'single',
      trigger_type: 'manual',
      activity_ids: ['activity-1'],
      template_id: 'tpl-1',
      requested_by: 'tester',
    })
    const list = await api.getAgentAnalysisJobs()
    const detail = await api.getAgentAnalysisJob('job-1')
    const item = await api.getAgentAnalysisItem('item-1')

    expect(created.items[0].draft?.status).toBe('watch')
    expect(list.items[0].needs_research_count).toBe(1)
    expect(detail.id).toBe('job-1')
    expect(item.id).toBe('item-1')

    const createCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const listCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[1]
    const detailCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[2]
    const itemCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[3]
    expect(createCall[0]).toBe('http://localhost:8000/api/agent-analysis/jobs')
    expect(createCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        scope_type: 'single',
        trigger_type: 'manual',
        activity_ids: ['activity-1'],
        template_id: 'tpl-1',
        requested_by: 'tester',
      }),
    })
    expect(listCall[0]).toBe('http://localhost:8000/api/agent-analysis/jobs')
    expect(detailCall[0]).toBe('http://localhost:8000/api/agent-analysis/jobs/job-1')
    expect(itemCall[0]).toBe('http://localhost:8000/api/agent-analysis/items/item-1')
  })

  it('approves and rejects agent-analysis items with review payloads', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          review_action: 'approved',
          item_id: 'item-1',
          activity_id: 'activity-1',
          review_note: 'Looks good',
          snapshot: {
            status: 'pass',
            summary: 'Safe to pursue',
            reasons: ['Reward and deadline are clear'],
            risk_flags: [],
            structured: { should_deep_research: false },
          },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          review_action: 'rejected',
          item_id: 'item-1',
          activity_id: 'activity-1',
          review_note: 'Need a human rewrite first',
          snapshot: null,
        })
      ) as typeof fetch

    const approved = await api.approveAgentAnalysisItem('item-1', {
      review_note: 'Looks good',
      edited_snapshot: {
        status: 'pass',
        summary: 'Safe to pursue',
        reasons: ['Reward and deadline are clear'],
      },
    })
    const rejected = await api.rejectAgentAnalysisItem('item-1', {
      review_note: 'Need a human rewrite first',
    })

    expect(approved.review_action).toBe('approved')
    expect(approved.snapshot?.status).toBe('pass')
    expect(rejected.review_action).toBe('rejected')

    const approveCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const rejectCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[1]
    expect(approveCall[0]).toBe('http://localhost:8000/api/agent-analysis/items/item-1/approve')
    expect(approveCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        review_note: 'Looks good',
        edited_snapshot: {
          status: 'pass',
          summary: 'Safe to pursue',
          reasons: ['Reward and deadline are clear'],
        },
      }),
    })
    expect(rejectCall[0]).toBe('http://localhost:8000/api/agent-analysis/items/item-1/reject')
    expect(rejectCall[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        review_note: 'Need a human rewrite first',
      }),
    })
  })

  it('fans out batch agent-analysis review actions through per-item endpoints', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          review_action: 'approved',
          item_id: 'item-1',
          activity_id: 'activity-1',
          review_note: 'Batch approved',
          snapshot: { status: 'pass', summary: 'Approved', reasons: [], risk_flags: [], structured: {} },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          review_action: 'approved',
          item_id: 'item-2',
          activity_id: 'activity-2',
          review_note: 'Batch approved',
          snapshot: { status: 'watch', summary: 'Approved with watch', reasons: [], risk_flags: [], structured: {} },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          review_action: 'rejected',
          item_id: 'item-3',
          activity_id: 'activity-3',
          review_note: 'Batch rejected',
          snapshot: null,
        })
      ) as typeof fetch

    const approved = await api.approveAgentAnalysisBatch(['item-1', 'item-2'], {
      review_note: 'Batch approved',
    })
    const rejected = await api.rejectAgentAnalysisBatch(['item-3'], {
      review_note: 'Batch rejected',
    })

    expect(approved).toHaveLength(2)
    expect(approved[1].item_id).toBe('item-2')
    expect(rejected[0].review_action).toBe('rejected')

    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls
    expect(calls[0][0]).toBe('http://localhost:8000/api/agent-analysis/items/item-1/approve')
    expect(calls[1][0]).toBe('http://localhost:8000/api/agent-analysis/items/item-2/approve')
    expect(calls[2][0]).toBe('http://localhost:8000/api/agent-analysis/items/item-3/reject')
  })

  it('posts AI filter requests for opportunities', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        query: '只保留适合独立开发者的机会',
        parsed_intent_summary: '筛选适合单人开发的机会',
        candidate_count: 2,
        matched_count: 1,
        discarded_count: 1,
        items: [],
      })
    ) as typeof fetch

    const result = await api.aiFilterActivities({
      base_filters: { category: 'hackathon', prize_range: '500-2000' },
      query: '只保留适合独立开发者的机会',
    })

    const [requestUrl, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(requestUrl).toBe('http://localhost:8000/api/activities/ai-filter')
    expect(requestInit).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        base_filters: { category: 'hackathon', prize_range: '500-2000' },
        query: '只保留适合独立开发者的机会',
      }),
    })
    expect(result.matched_count).toBe(1)
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
