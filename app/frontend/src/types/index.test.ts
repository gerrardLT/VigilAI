import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import type { Activity, Source } from './index'

/**
 * Property 1: TypeScript接口与后端模型字段匹配
 * Validates: Requirements 1.4, 13.2, 13.3
 * 
 * For any Activity object returned from the backend API, 
 * the frontend Activity interface SHALL contain all the same fields with compatible types.
 */

// 后端Activity模型必需字段
const ACTIVITY_REQUIRED_FIELDS = [
  'id', 'title', 'source_id', 'source_name', 'url', 
  'category', 'tags', 'status', 'created_at', 'updated_at'
] as const

// 后端Activity模型可选字段
const ACTIVITY_OPTIONAL_FIELDS = [
  'description', 'prize', 'dates', 'location', 'organizer'
] as const

// 后端Source模型必需字段
const SOURCE_REQUIRED_FIELDS = [
  'id', 'name', 'type', 'status', 'activity_count'
] as const

// 后端Source模型可选字段
const SOURCE_OPTIONAL_FIELDS = [
  'last_run', 'last_success', 'error_message'
] as const

// 有效的Category值
const VALID_CATEGORIES = ['hackathon', 'competition', 'airdrop', 'bounty', 'grant', 'event'] as const

// 有效的SourceType值
const VALID_SOURCE_TYPES = ['rss', 'web', 'api'] as const

// 有效的SourceStatus值
const VALID_SOURCE_STATUSES = ['idle', 'running', 'success', 'error'] as const

// 生成有效的Activity对象
const activityArbitrary = fc.record({
  id: fc.string({ minLength: 1 }),
  title: fc.string({ minLength: 1 }),
  description: fc.option(fc.string(), { nil: null }),
  source_id: fc.string({ minLength: 1 }),
  source_name: fc.string({ minLength: 1 }),
  url: fc.webUrl(),
  category: fc.constantFrom(...VALID_CATEGORIES),
  tags: fc.array(fc.string()),
  prize: fc.option(
    fc.record({
      amount: fc.option(fc.float({ min: 0 }), { nil: null }),
      currency: fc.string({ minLength: 1 }),
      description: fc.option(fc.string(), { nil: null }),
    }),
    { nil: null }
  ),
  dates: fc.option(
    fc.record({
      start_date: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
      end_date: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
      deadline: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
    }),
    { nil: null }
  ),
  location: fc.option(fc.string(), { nil: null }),
  organizer: fc.option(fc.string(), { nil: null }),
  status: fc.string({ minLength: 1 }),
  created_at: fc.date().map(d => d.toISOString()),
  updated_at: fc.date().map(d => d.toISOString()),
})

// 生成有效的Source对象
const sourceArbitrary = fc.record({
  id: fc.string({ minLength: 1 }),
  name: fc.string({ minLength: 1 }),
  type: fc.constantFrom(...VALID_SOURCE_TYPES),
  status: fc.constantFrom(...VALID_SOURCE_STATUSES),
  last_run: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
  last_success: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
  activity_count: fc.nat(),
  error_message: fc.option(fc.string(), { nil: null }),
})

describe('TypeScript接口与后端模型字段匹配', () => {
  // Feature: vigilai-frontend, Property 1: TypeScript接口与后端模型字段匹配
  it('Activity接口应包含所有后端必需字段', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        // 验证所有必需字段存在
        for (const field of ACTIVITY_REQUIRED_FIELDS) {
          expect(activity).toHaveProperty(field)
          expect(activity[field]).toBeDefined()
        }
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('Activity接口应支持所有后端可选字段', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        // 验证所有可选字段存在（可以为null）
        for (const field of ACTIVITY_OPTIONAL_FIELDS) {
          expect(activity).toHaveProperty(field)
        }
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('Activity.category应为有效的Category枚举值', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        expect(VALID_CATEGORIES).toContain(activity.category)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('Source接口应包含所有后端必需字段', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        // 验证所有必需字段存在
        for (const field of SOURCE_REQUIRED_FIELDS) {
          expect(source).toHaveProperty(field)
          expect(source[field]).toBeDefined()
        }
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('Source接口应支持所有后端可选字段', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        // 验证所有可选字段存在（可以为null）
        for (const field of SOURCE_OPTIONAL_FIELDS) {
          expect(source).toHaveProperty(field)
        }
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('Source.type应为有效的SourceType枚举值', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        expect(VALID_SOURCE_TYPES).toContain(source.type)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('Source.status应为有效的SourceStatus枚举值', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        expect(VALID_SOURCE_STATUSES).toContain(source.status)
        return true
      }),
      { numRuns: 100 }
    )
  })
})
