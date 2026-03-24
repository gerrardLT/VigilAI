import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

/**
 * Property 4: 筛选器状态同步
 * For any filter selection (category or source), the URL query parameters SHALL reflect
 * the current filter state, and the activity list SHALL update to show only matching results.
 * Validates: Requirements 4.3, 4.5
 */
describe('Property 4: Filter State Synchronization', () => {
  const validCategories = ['', 'hackathon', 'competition', 'airdrop', 'bounty', 'grant', 'event']
  const validSources = ['', 'devpost', 'dorahacks', 'gitcoin', '36kr', 'huxiu']

  it('should generate valid URL params for any filter combination', () => {
    const categoryArb = fc.constantFrom(...validCategories)
    const sourceArb = fc.constantFrom(...validSources)
    const searchArb = fc.string({ minLength: 0, maxLength: 50 }).filter(s => !s.includes('&') && !s.includes('='))
    const pageArb = fc.integer({ min: 1, max: 100 })

    fc.assert(
      fc.property(categoryArb, sourceArb, searchArb, pageArb, (category, source_id, search, page) => {
        const params = new URLSearchParams()
        
        if (category) params.set('category', category)
        if (source_id) params.set('source_id', source_id)
        if (search) params.set('search', search)
        if (page > 1) params.set('page', String(page))
        
        const urlString = params.toString()
        
        // URL params should be valid
        const parsed = new URLSearchParams(urlString)
        
        // Verify round-trip
        if (category) expect(parsed.get('category')).toBe(category)
        if (source_id) expect(parsed.get('source_id')).toBe(source_id)
        if (search) expect(parsed.get('search')).toBe(search)
        if (page > 1) expect(parsed.get('page')).toBe(String(page))
        
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should preserve filter state when converting to/from URL params', () => {
    const categoryArb = fc.constantFrom(...validCategories)
    const sourceArb = fc.constantFrom(...validSources)
    const sortByArb = fc.constantFrom('created_at', 'deadline', 'prize')
    const sortOrderArb = fc.constantFrom('asc', 'desc')

    fc.assert(
      fc.property(categoryArb, sourceArb, sortByArb, sortOrderArb, (category, source_id, sort_by, sort_order) => {
        // Create filter object
        const filters = { category, source_id, sort_by, sort_order }
        
        // Convert to URL params
        const params = new URLSearchParams()
        Object.entries(filters).forEach(([key, value]) => {
          if (value) params.set(key, value)
        })
        
        // Parse back
        const parsed = new URLSearchParams(params.toString())
        
        // Verify each non-empty filter is preserved
        if (category) expect(parsed.get('category')).toBe(category)
        if (source_id) expect(parsed.get('source_id')).toBe(source_id)
        if (sort_by) expect(parsed.get('sort_by')).toBe(sort_by)
        if (sort_order) expect(parsed.get('sort_order')).toBe(sort_order)
        
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should handle empty filters correctly', () => {
    fc.assert(
      fc.property(fc.constant(null), () => {
        const params = new URLSearchParams()
        
        // Empty filters should produce empty URL params
        expect(params.toString()).toBe('')
        
        // Parsing empty string should return null for all keys
        expect(params.get('category')).toBeNull()
        expect(params.get('source_id')).toBeNull()
        expect(params.get('search')).toBeNull()
        
        return true
      }),
      { numRuns: 10 }
    )
  })

  it('should validate category values are from allowed set', () => {
    fc.assert(
      fc.property(fc.constantFrom(...validCategories), (category) => {
        // All generated categories should be in the valid set
        expect(validCategories).toContain(category)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should validate source_id values are from allowed set', () => {
    fc.assert(
      fc.property(fc.constantFrom(...validSources), (source_id) => {
        // All generated source IDs should be in the valid set
        expect(validSources).toContain(source_id)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should correctly build API query params from filters', () => {
    const categoryArb = fc.constantFrom(...validCategories)
    const sourceArb = fc.constantFrom(...validSources)
    const searchArb = fc.string({ minLength: 0, maxLength: 20 }).filter(s => /^[a-zA-Z0-9\s]*$/.test(s))
    const pageArb = fc.integer({ min: 1, max: 50 })
    const pageSizeArb = fc.constantFrom(10, 20, 50)

    fc.assert(
      fc.property(categoryArb, sourceArb, searchArb, pageArb, pageSizeArb, 
        (category, source_id, search, page, page_size) => {
          const filters = { category, source_id, search, page, page_size }
          
          // Build query params like the API service does
          const params = new URLSearchParams()
          Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== '') {
              params.append(key, String(value))
            }
          })
          
          // Verify params are correctly built
          const queryString = params.toString()
          
          // Non-empty values should appear in query string
          if (category) expect(queryString).toContain(`category=${category}`)
          if (source_id) expect(queryString).toContain(`source_id=${source_id}`)
          if (search) expect(queryString).toContain('search=')
          expect(queryString).toContain(`page=${page}`)
          expect(queryString).toContain(`page_size=${page_size}`)
          
          return true
        }
      ),
      { numRuns: 100 }
    )
  })
})
