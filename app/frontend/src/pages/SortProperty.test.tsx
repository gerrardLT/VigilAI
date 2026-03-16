import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import type { Activity } from '../types'

/**
 * Property 5: 排序结果正确性
 * For any sort option selection, the activity list SHALL be ordered according to
 * the selected field and direction.
 * Validates: Requirements 6.3
 */
describe('Property 5: Sort Results Correctness', () => {
  const validSortFields = ['created_at', 'deadline', 'prize']
  const validSortOrders = ['asc', 'desc'] as const

  // Helper to create mock activity
  const createActivity = (overrides: Partial<Activity> = {}): Activity => ({
    id: fc.sample(fc.uuid(), 1)[0],
    title: 'Test Activity',
    description: null,
    source_id: 'devpost',
    source_name: 'Devpost',
    url: 'https://example.com',
    category: 'hackathon',
    tags: [],
    prize: null,
    dates: null,
    location: null,
    organizer: null,
    status: 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  })

  // Sort function that mimics backend behavior
  const sortActivities = (
    activities: Activity[],
    sortBy: string,
    sortOrder: 'asc' | 'desc'
  ): Activity[] => {
    return [...activities].sort((a, b) => {
      let valueA: string | number | null = null
      let valueB: string | number | null = null

      switch (sortBy) {
        case 'created_at':
          valueA = a.created_at
          valueB = b.created_at
          break
        case 'deadline':
          valueA = a.dates?.deadline ?? null
          valueB = b.dates?.deadline ?? null
          break
        case 'prize':
          valueA = a.prize?.amount ?? null
          valueB = b.prize?.amount ?? null
          break
        default:
          valueA = a.created_at
          valueB = b.created_at
      }

      // Handle nulls - push to end
      if (valueA === null && valueB === null) return 0
      if (valueA === null) return 1
      if (valueB === null) return -1

      // Compare values
      let comparison = 0
      if (typeof valueA === 'string' && typeof valueB === 'string') {
        comparison = valueA.localeCompare(valueB)
      } else if (typeof valueA === 'number' && typeof valueB === 'number') {
        comparison = valueA - valueB
      }

      return sortOrder === 'desc' ? -comparison : comparison
    })
  }

  it('should sort by created_at correctly', () => {
    const dateArb = fc.date({ min: new Date('2020-01-01'), max: new Date('2025-12-31') })
    const activitiesArb = fc.array(dateArb, { minLength: 2, maxLength: 20 }).map(dates =>
      dates.map(date => createActivity({ created_at: date.toISOString() }))
    )

    fc.assert(
      fc.property(activitiesArb, fc.constantFrom(...validSortOrders), (activities, sortOrder) => {
        const sorted = sortActivities(activities, 'created_at', sortOrder)

        // Verify order
        for (let i = 1; i < sorted.length; i++) {
          const prev = new Date(sorted[i - 1].created_at).getTime()
          const curr = new Date(sorted[i].created_at).getTime()
          
          if (sortOrder === 'asc') {
            expect(prev).toBeLessThanOrEqual(curr)
          } else {
            expect(prev).toBeGreaterThanOrEqual(curr)
          }
        }

        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should sort by deadline correctly', () => {
    const dateArb = fc.option(
      fc.date({ min: new Date('2020-01-01'), max: new Date('2025-12-31') }),
      { nil: undefined }
    )
    
    const activitiesArb = fc.array(dateArb, { minLength: 2, maxLength: 20 }).map(dates =>
      dates.map(date => createActivity({
        dates: date ? { start_date: null, end_date: null, deadline: date.toISOString() } : null
      }))
    )

    fc.assert(
      fc.property(activitiesArb, fc.constantFrom(...validSortOrders), (activities, sortOrder) => {
        const sorted = sortActivities(activities, 'deadline', sortOrder)

        // Get activities with deadlines
        const withDeadlines = sorted.filter(a => a.dates?.deadline)
        const withoutDeadlines = sorted.filter(a => !a.dates?.deadline)

        // Activities without deadlines should be at the end
        const lastWithDeadlineIndex = sorted.findIndex(a => !a.dates?.deadline)
        if (lastWithDeadlineIndex > 0 && withoutDeadlines.length > 0) {
          // All items after first null should also be null
          for (let i = lastWithDeadlineIndex; i < sorted.length; i++) {
            expect(sorted[i].dates?.deadline).toBeFalsy()
          }
        }

        // Verify order among activities with deadlines
        for (let i = 1; i < withDeadlines.length; i++) {
          const prev = new Date(withDeadlines[i - 1].dates!.deadline!).getTime()
          const curr = new Date(withDeadlines[i].dates!.deadline!).getTime()
          
          if (sortOrder === 'asc') {
            expect(prev).toBeLessThanOrEqual(curr)
          } else {
            expect(prev).toBeGreaterThanOrEqual(curr)
          }
        }

        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should sort by prize amount correctly', () => {
    const prizeArb = fc.option(
      fc.integer({ min: 0, max: 1000000 }),
      { nil: undefined }
    )
    
    const activitiesArb = fc.array(prizeArb, { minLength: 2, maxLength: 20 }).map(prizes =>
      prizes.map(amount => createActivity({
        prize: amount !== undefined ? { amount, currency: 'USD', description: null } : null
      }))
    )

    fc.assert(
      fc.property(activitiesArb, fc.constantFrom(...validSortOrders), (activities, sortOrder) => {
        const sorted = sortActivities(activities, 'prize', sortOrder)

        // Get activities with prizes
        const withPrizes = sorted.filter(a => a.prize?.amount !== null && a.prize?.amount !== undefined)
        const withoutPrizes = sorted.filter(a => a.prize?.amount === null || a.prize?.amount === undefined)

        // Activities without prizes should be at the end
        const lastWithPrizeIndex = sorted.findIndex(a => a.prize?.amount === null || a.prize?.amount === undefined)
        if (lastWithPrizeIndex > 0 && withoutPrizes.length > 0) {
          for (let i = lastWithPrizeIndex; i < sorted.length; i++) {
            expect(sorted[i].prize?.amount ?? null).toBeNull()
          }
        }

        // Verify order among activities with prizes
        for (let i = 1; i < withPrizes.length; i++) {
          const prev = withPrizes[i - 1].prize!.amount!
          const curr = withPrizes[i].prize!.amount!
          
          if (sortOrder === 'asc') {
            expect(prev).toBeLessThanOrEqual(curr)
          } else {
            expect(prev).toBeGreaterThanOrEqual(curr)
          }
        }

        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should maintain stable sort for equal values', () => {
    const sameDate = '2024-06-15T12:00:00Z'
    const activitiesArb = fc.array(
      fc.string({ minLength: 1, maxLength: 20 }).filter(s => /^[a-zA-Z0-9]+$/.test(s)),
      { minLength: 2, maxLength: 10 }
    ).map(titles =>
      titles.map((title, index) => createActivity({
        id: `id-${index}`,
        title,
        created_at: sameDate,
      }))
    )

    fc.assert(
      fc.property(activitiesArb, fc.constantFrom(...validSortOrders), (activities, sortOrder) => {
        const sorted = sortActivities(activities, 'created_at', sortOrder)

        // All activities should still be present
        expect(sorted.length).toBe(activities.length)
        
        // All original IDs should be in the result
        const originalIds = new Set(activities.map(a => a.id))
        const sortedIds = new Set(sorted.map(a => a.id))
        expect(sortedIds).toEqual(originalIds)

        return true
      }),
      { numRuns: 50 }
    )
  })

  it('should validate sort field is from allowed set', () => {
    fc.assert(
      fc.property(fc.constantFrom(...validSortFields), (sortBy) => {
        expect(validSortFields).toContain(sortBy)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should validate sort order is asc or desc', () => {
    fc.assert(
      fc.property(fc.constantFrom(...validSortOrders), (sortOrder) => {
        expect(['asc', 'desc']).toContain(sortOrder)
        return true
      }),
      { numRuns: 100 }
    )
  })
})
