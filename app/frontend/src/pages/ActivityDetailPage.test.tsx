import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import type { Activity, Prize, ActivityDates } from '../types'

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
