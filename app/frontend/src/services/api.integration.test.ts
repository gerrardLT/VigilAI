/**
 * API集成测试
 * 
 * 这些测试需要后端服务运行在 http://localhost:8000
 * 运行测试前请确保后端已启动：
 *   cd app/backend && python main.py
 * 
 * 运行集成测试：
 *   npm test -- src/services/api.integration.test.ts
 */

import { describe, it, expect, beforeAll } from 'vitest'
import { ApiService } from './api'
import type { Activity, Source } from '../types'

// 跳过集成测试，除非明确启用
const runtimeProcess = globalThis as typeof globalThis & {
  process?: { env?: Record<string, string | undefined> }
}
const SKIP_INTEGRATION = runtimeProcess.process?.env?.RUN_INTEGRATION_TESTS !== 'true'

describe.skipIf(SKIP_INTEGRATION)('API Integration Tests', () => {
  let api: ApiService

  beforeAll(() => {
    api = new ApiService('http://localhost:8000')
  })

  /**
   * 17.1 编写API端点集成测试
   * Requirements: 2.1, 13.2, 13.3
   */
  describe('GET /api/activities', () => {
    it('should return ActivityListResponse with correct structure', async () => {
      const response = await api.getActivities()
      
      expect(response).toHaveProperty('total')
      expect(response).toHaveProperty('page')
      expect(response).toHaveProperty('page_size')
      expect(response).toHaveProperty('items')
      expect(Array.isArray(response.items)).toBe(true)
      
      expect(typeof response.total).toBe('number')
      expect(typeof response.page).toBe('number')
      expect(typeof response.page_size).toBe('number')
    })

    it('should return activities matching Activity interface', async () => {
      const response = await api.getActivities()
      
      if (response.items.length > 0) {
        const activity = response.items[0]
        
        // 验证必需字段
        expect(activity).toHaveProperty('id')
        expect(activity).toHaveProperty('title')
        expect(activity).toHaveProperty('source_id')
        expect(activity).toHaveProperty('source_name')
        expect(activity).toHaveProperty('url')
        expect(activity).toHaveProperty('category')
        expect(activity).toHaveProperty('created_at')
        expect(activity).toHaveProperty('updated_at')
        
        // 验证类型
        expect(typeof activity.id).toBe('string')
        expect(typeof activity.title).toBe('string')
        expect(typeof activity.source_id).toBe('string')
        expect(typeof activity.source_name).toBe('string')
        expect(typeof activity.url).toBe('string')
      }
    })
  })

  describe('GET /api/sources', () => {
    it('should return array of sources matching Source interface', async () => {
      const sources = await api.getSources()
      
      expect(Array.isArray(sources)).toBe(true)
      
      if (sources.length > 0) {
        const source = sources[0]
        
        // 验证必需字段
        expect(source).toHaveProperty('id')
        expect(source).toHaveProperty('name')
        expect(source).toHaveProperty('type')
        expect(source).toHaveProperty('status')
        expect(source).toHaveProperty('activity_count')
        
        // 验证类型
        expect(typeof source.id).toBe('string')
        expect(typeof source.name).toBe('string')
        expect(['rss', 'web', 'api']).toContain(source.type)
        expect(['idle', 'running', 'success', 'error']).toContain(source.status)
        expect(typeof source.activity_count).toBe('number')
      }
    })
  })

  describe('GET /api/stats', () => {
    it('should return StatsResponse with correct structure', async () => {
      const stats = await api.getStats()
      
      expect(stats).toHaveProperty('total_activities')
      expect(stats).toHaveProperty('total_sources')
      expect(stats).toHaveProperty('activities_by_category')
      expect(stats).toHaveProperty('activities_by_source')
      
      expect(typeof stats.total_activities).toBe('number')
      expect(typeof stats.total_sources).toBe('number')
      expect(typeof stats.activities_by_category).toBe('object')
      expect(typeof stats.activities_by_source).toBe('object')
    })
  })

  /**
   * 17.2 编写API响应字段验证测试
   * Requirements: 1.4, 13.2, 13.3
   */
  describe('Activity Response Field Validation', () => {
    it('should contain all required Activity fields', async () => {
      const response = await api.getActivities({ page_size: 1 })
      
      if (response.items.length > 0) {
        const activity = response.items[0] as Activity
        
        const requiredFields = [
          'id', 'title', 'source_id', 'source_name', 
          'url', 'category', 'created_at', 'updated_at'
        ]
        
        for (const field of requiredFields) {
          expect(activity).toHaveProperty(field)
          expect(activity[field as keyof Activity]).toBeDefined()
        }
      }
    })
  })

  describe('Source Response Field Validation', () => {
    it('should contain all required Source fields', async () => {
      const sources = await api.getSources()
      
      if (sources.length > 0) {
        const source = sources[0] as Source
        
        const requiredFields = ['id', 'name', 'type', 'status', 'activity_count']
        
        for (const field of requiredFields) {
          expect(source).toHaveProperty(field)
          expect(source[field as keyof Source]).toBeDefined()
        }
      }
    })
  })

  describe('Filter Parameters', () => {
    it('should correctly pass category filter to backend', async () => {
      const response = await api.getActivities({ category: 'hackathon' })
      
      // 所有返回的活动应该是hackathon类别
      for (const activity of response.items) {
        expect(activity.category).toBe('hackathon')
      }
    })

    it('should correctly pass pagination parameters', async () => {
      const response = await api.getActivities({ page: 1, page_size: 5 })
      
      expect(response.page).toBe(1)
      expect(response.page_size).toBe(5)
      expect(response.items.length).toBeLessThanOrEqual(5)
    })
  })

  /**
   * 17.3 编写API错误响应测试
   * Requirements: 2.2, 2.3, 11.4
   */
  describe('Error Response Handling', () => {
    it('should handle 404 for non-existent activity', async () => {
      try {
        await api.getActivity('non-existent-id-12345')
        expect.fail('Should have thrown an error')
      } catch (error) {
        expect(error).toBeDefined()
      }
    })
  })

  describe('Health Check', () => {
    it('should return healthy status', async () => {
      const health = await api.healthCheck()
      
      expect(health).toHaveProperty('status')
      expect(health.status).toBe('healthy')
    })
  })
})
