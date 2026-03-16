import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import { formatDate, formatDateOnly, isExpired, daysUntil } from './formatDate'

/**
 * Property 7: 日期格式化一致性
 * Validates: Requirements 7.4
 * 
 * For any ISO 8601 date string from the backend, 
 * the formatDate utility SHALL convert it to a user-friendly format (e.g., "2024-01-15 14:30").
 */

describe('日期格式化一致性', () => {
  // Feature: vigilai-frontend, Property 7: 日期格式化一致性
  it('对于任何有效的ISO日期字符串，formatDate应返回YYYY-MM-DD HH:mm格式', () => {
    fc.assert(
      fc.property(
        fc.date({ min: new Date('1970-01-01'), max: new Date('2100-12-31') }),
        (date) => {
          const isoString = date.toISOString()
          const formatted = formatDate(isoString)
          
          // 验证格式为 YYYY-MM-DD HH:mm
          expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
          
          // 验证年份正确
          expect(formatted.substring(0, 4)).toBe(String(date.getFullYear()))
          
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('对于任何有效的ISO日期字符串，formatDateOnly应返回YYYY-MM-DD格式', () => {
    fc.assert(
      fc.property(
        fc.date({ min: new Date('1970-01-01'), max: new Date('2100-12-31') }),
        (date) => {
          const isoString = date.toISOString()
          const formatted = formatDateOnly(isoString)
          
          // 验证格式为 YYYY-MM-DD
          expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2}$/)
          
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('对于null或undefined输入，formatDate应返回空字符串', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate(undefined)).toBe('')
    expect(formatDate('')).toBe('')
  })

  it('对于无效的日期字符串，formatDate应返回空字符串', () => {
    fc.assert(
      fc.property(
        fc.string().filter(s => isNaN(new Date(s).getTime())),
        (invalidDateString) => {
          const formatted = formatDate(invalidDateString)
          expect(formatted).toBe('')
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('isExpired对于过去的日期应返回true', () => {
    fc.assert(
      fc.property(
        fc.date({ min: new Date('1970-01-01'), max: new Date(Date.now() - 86400000) }), // 至少1天前
        (pastDate) => {
          const isoString = pastDate.toISOString()
          expect(isExpired(isoString)).toBe(true)
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('isExpired对于未来的日期应返回false', () => {
    fc.assert(
      fc.property(
        fc.date({ min: new Date(Date.now() + 86400000), max: new Date('2100-12-31') }), // 至少1天后
        (futureDate) => {
          const isoString = futureDate.toISOString()
          expect(isExpired(isoString)).toBe(false)
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('daysUntil对于未来日期应返回正数', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 365 }),
        (daysInFuture) => {
          const futureDate = new Date(Date.now() + daysInFuture * 86400000)
          const isoString = futureDate.toISOString()
          const days = daysUntil(isoString)
          
          expect(days).not.toBeNull()
          expect(days).toBeGreaterThan(0)
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('daysUntil对于过去日期应返回负数', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 365 }),
        (daysInPast) => {
          const pastDate = new Date(Date.now() - daysInPast * 86400000)
          const isoString = pastDate.toISOString()
          const days = daysUntil(isoString)
          
          expect(days).not.toBeNull()
          expect(days).toBeLessThan(0)
          return true
        }
      ),
      { numRuns: 100 }
    )
  })
})
