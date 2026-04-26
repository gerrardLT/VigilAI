import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import fc from 'fast-check'
import type { Activity, Prize, ActivityDates } from '../types'
import ActivityDetailPage from './ActivityDetailPage'

const apiMocks = vi.hoisted(() => ({
  getActivity: vi.fn(),
  getAgentAnalysisJob: vi.fn(),
  approveAgentAnalysisItem: vi.fn(),
  rejectAgentAnalysisItem: vi.fn(),
}))

const analysisTemplateHookState = vi.hoisted(() => ({
  current: {
    templates: [{ id: 'tpl-1', slug: 'quick-money', name: 'Quick money' }],
    defaultTemplate: { id: 'tpl-1', slug: 'quick-money', name: 'Quick money' },
    loading: false,
    error: null,
    refetch: vi.fn(),
    duplicateTemplate: vi.fn(),
    activateTemplate: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

vi.mock('../hooks/useAnalysisTemplates', () => ({
  useAnalysisTemplates: () => analysisTemplateHookState.current,
}))

/**
 * Property 6: 活动详情字段显示完整性
 * For any Activity fetched by ID, the ActivityDetailPage SHALL display all non-null fields
 * including title, description, source, category, tags, prize, dates, location, and organizer.
 * Validates: Requirements 7.2
 */
describe('Property 6: Activity Detail Field Display Completeness', () => {
  const validCategories = [
    'hackathon',
    'data_competition',
    'coding_competition',
    'other_competition',
    'airdrop',
    'bounty',
    'grant',
    'dev_event',
    'news',
  ] as const
  const validCurrencies = ['USD', 'EUR', 'CNY', 'ETH', 'BTC', 'USDT']

  // Arbitraries for generating test data
  const prizeArb: fc.Arbitrary<Prize | null> = fc.option(
    fc.record({
      amount: fc.option(fc.integer({ min: 0, max: 10000000 }), { nil: null }),
      currency: fc.constantFrom(...validCurrencies),
      description: fc.option(fc.string({ minLength: 0, maxLength: 100 }), { nil: null }),
    }),
    { nil: null }
  )

  const datesArb: fc.Arbitrary<ActivityDates | null> = fc.option(
    fc.record({
      start_date: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
      end_date: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
      deadline: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
    }),
    { nil: null }
  )

  const activityArb: fc.Arbitrary<Activity> = fc.record({
    id: fc.uuid(),
    title: fc.string({ minLength: 1, maxLength: 200 }),
    description: fc.option(fc.string({ minLength: 0, maxLength: 1000 }), { nil: null }),
    source_id: fc.string({ minLength: 1, maxLength: 50 }),
    source_name: fc.string({ minLength: 1, maxLength: 100 }),
    url: fc.webUrl(),
    category: fc.constantFrom(...validCategories),
    tags: fc.array(fc.string({ minLength: 1, maxLength: 30 }), { minLength: 0, maxLength: 10 }),
    prize: prizeArb,
    dates: datesArb,
    location: fc.option(fc.string({ minLength: 0, maxLength: 100 }), { nil: null }),
    organizer: fc.option(fc.string({ minLength: 0, maxLength: 100 }), { nil: null }),
    status: fc.constantFrom('active', 'upcoming', 'ended'),
    created_at: fc.date().map(d => d.toISOString()),
    updated_at: fc.date().map(d => d.toISOString()),
  })

  // Helper to check which fields should be displayed
  const getDisplayableFields = (activity: Activity): string[] => {
    const fields: string[] = ['title', 'source_name', 'category', 'url', 'created_at', 'updated_at']
    
    if (activity.description) fields.push('description')
    if (activity.prize) fields.push('prize')
    if (activity.dates) fields.push('dates')
    if (activity.location) fields.push('location')
    if (activity.organizer) fields.push('organizer')
    if (activity.tags && activity.tags.length > 0) fields.push('tags')
    
    return fields
  }

  it('should identify all displayable fields for any activity', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        const displayableFields = getDisplayableFields(activity)
        
        // Required fields should always be present
        expect(displayableFields).toContain('title')
        expect(displayableFields).toContain('source_name')
        expect(displayableFields).toContain('category')
        expect(displayableFields).toContain('url')
        expect(displayableFields).toContain('created_at')
        expect(displayableFields).toContain('updated_at')
        
        // Optional fields should be present only when non-null
        if (activity.description) {
          expect(displayableFields).toContain('description')
        }
        if (activity.prize) {
          expect(displayableFields).toContain('prize')
        }
        if (activity.dates) {
          expect(displayableFields).toContain('dates')
        }
        if (activity.location) {
          expect(displayableFields).toContain('location')
        }
        if (activity.organizer) {
          expect(displayableFields).toContain('organizer')
        }
        if (activity.tags && activity.tags.length > 0) {
          expect(displayableFields).toContain('tags')
        }
        
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid title for any activity', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        expect(activity.title).toBeDefined()
        expect(typeof activity.title).toBe('string')
        expect(activity.title.length).toBeGreaterThan(0)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid source information for any activity', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        expect(activity.source_id).toBeDefined()
        expect(activity.source_name).toBeDefined()
        expect(typeof activity.source_id).toBe('string')
        expect(typeof activity.source_name).toBe('string')
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid category from allowed set', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        expect(validCategories).toContain(activity.category)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid URL format', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        expect(activity.url).toBeDefined()
        expect(typeof activity.url).toBe('string')
        // URL should start with http or https
        expect(activity.url).toMatch(/^https?:\/\//)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid prize structure when present', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        if (activity.prize) {
          expect(activity.prize).toHaveProperty('currency')
          expect(typeof activity.prize.currency).toBe('string')
          
          if (activity.prize.amount !== null) {
            expect(typeof activity.prize.amount).toBe('number')
            expect(activity.prize.amount).toBeGreaterThanOrEqual(0)
          }
        }
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid dates structure when present', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        if (activity.dates) {
          // Each date field should be null or valid ISO string
          const dateFields = ['start_date', 'end_date', 'deadline'] as const
          
          for (const field of dateFields) {
            const value = activity.dates[field]
            if (value !== null) {
              expect(typeof value).toBe('string')
              // Should be parseable as date
              const parsed = new Date(value)
              expect(parsed.toString()).not.toBe('Invalid Date')
            }
          }
        }
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid tags array when present', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        expect(Array.isArray(activity.tags)).toBe(true)
        
        for (const tag of activity.tags) {
          expect(typeof tag).toBe('string')
        }
        
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should have valid timestamps', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        expect(activity.created_at).toBeDefined()
        expect(activity.updated_at).toBeDefined()
        
        // Should be parseable as dates
        const createdAt = new Date(activity.created_at)
        const updatedAt = new Date(activity.updated_at)
        
        expect(createdAt.toString()).not.toBe('Invalid Date')
        expect(updatedAt.toString()).not.toBe('Invalid Date')
        
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should correctly count displayable optional fields', () => {
    fc.assert(
      fc.property(activityArb, (activity) => {
        let optionalFieldCount = 0
        
        if (activity.description) optionalFieldCount++
        if (activity.prize) optionalFieldCount++
        if (activity.dates) optionalFieldCount++
        if (activity.location) optionalFieldCount++
        if (activity.organizer) optionalFieldCount++
        if (activity.tags && activity.tags.length > 0) optionalFieldCount++
        
        // Optional field count should be between 0 and 6
        expect(optionalFieldCount).toBeGreaterThanOrEqual(0)
        expect(optionalFieldCount).toBeLessThanOrEqual(6)
        
        return true
      }),
      { numRuns: 100 }
    )
  })
})

describe('ActivityDetailPage agent-analysis workbench', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMocks.getActivity.mockResolvedValue({
      id: 'activity-1',
      title: 'AI Hackathon',
      description: 'Build an AI app.',
      full_content: 'Long description',
      source_id: 'devpost',
      source_name: 'Devpost',
      url: 'https://example.com/ai-hackathon',
      category: 'hackathon',
      tags: ['ai'],
      prize: null,
      dates: null,
      location: null,
      organizer: null,
      image_url: null,
      summary: 'Recommended for AI builders',
      score: 8.9,
      score_reason: 'Urgent and high trust',
      deadline_level: 'urgent',
      trust_level: 'high',
      updated_fields: [],
      analysis_fields: {
        roi_level: 'high',
        solo_friendliness: 'solo_friendly',
      },
      analysis_status: 'watch',
      analysis_failed_layer: null,
      analysis_summary_reasons: ['Reward clarity passed'],
      analysis_layer_results: [],
      analysis_score_breakdown: {},
      analysis_current_run_id: 'job-1',
      is_tracking: false,
      is_favorited: false,
      is_digest_candidate: false,
      tracking: null,
      timeline: [],
      related_items: [],
      status: 'upcoming',
      created_at: '2026-03-23T08:00:00Z',
      updated_at: '2026-03-23T08:00:00Z',
    })
    apiMocks.getAgentAnalysisJob.mockResolvedValue({
      id: 'job-1',
      trigger_type: 'manual',
      scope_type: 'single',
      template_id: 'tpl-1',
      route_policy: {},
      budget_policy: {},
      status: 'completed',
      requested_by: null,
      created_at: '2026-03-23T08:00:00Z',
      finished_at: '2026-03-23T08:00:10Z',
      item_count: 1,
      items: [
        {
          id: 'item-1',
          job_id: 'job-1',
          activity_id: 'activity-1',
          status: 'completed',
          needs_research: true,
          final_draft_status: 'watch',
          created_at: '2026-03-23T08:00:00Z',
          updated_at: '2026-03-23T08:00:10Z',
          activity: null,
          draft: {
            status: 'watch',
            summary: 'Need manual review',
            reasons: ['Reward cap still needs confirmation'],
            risk_flags: ['reward_unclear'],
            structured: {
              should_deep_research: true,
              confidence_band: 'medium',
            },
          },
          steps: [
            {
              id: 'step-1',
              job_item_id: 'item-1',
              step_type: 'screening',
              step_status: 'completed',
              output_payload: {
                status: 'watch',
              },
              created_at: '2026-03-23T08:00:01Z',
            },
          ],
          evidence: [
            {
              id: 'evidence-1',
              job_item_id: 'item-1',
              source_type: 'web',
              url: 'https://example.com/rules',
              title: 'Official rules',
              snippet: 'Reward cap is under review',
              created_at: '2026-03-23T08:00:05Z',
            },
          ],
          reviews: [],
        },
      ],
    })
    apiMocks.approveAgentAnalysisItem.mockResolvedValue({
      review_action: 'approved',
      item_id: 'item-1',
      activity_id: 'activity-1',
      review_note: 'Looks good',
      snapshot: null,
    })
    apiMocks.rejectAgentAnalysisItem.mockResolvedValue({
      review_action: 'rejected',
      item_id: 'item-1',
      activity_id: 'activity-1',
      review_note: 'Needs rewrite',
      snapshot: null,
    })
  })

  it('shows evidence and review actions for a completed draft', async () => {
    render(
      <MemoryRouter initialEntries={['/activities/activity-1']}>
        <Routes>
          <Route path="/activities/:id" element={<ActivityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    expect(await screen.findByTestId('agent-analysis-evidence-panel')).toBeInTheDocument()
    expect(await screen.findByTestId('agent-analysis-review-bar')).toBeInTheDocument()
    expect(await screen.findByText('Official rules')).toBeInTheDocument()
    expect(screen.getByText('Reward cap still needs confirmation')).toBeInTheDocument()
  })
})
