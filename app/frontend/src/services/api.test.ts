import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import fc from 'fast-check'
import { ApiService, ApiError } from './api'

/**
 * Property 2: API错误处理一致性
 * Validates: Requirements 2.2, 2.3
 * 
 * For any HTTP error response (status >= 400), 
 * the API service SHALL throw an ApiError containing the status code and error message.
 */

// 声明全局fetch类型
declare const globalThis: {
  fetch: typeof fetch
}

describe('API错误处理一致性', () => {
  let apiService: ApiService
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    apiService = new ApiService('http://localhost:8000')
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  // Feature: vigilai-frontend, Property 2: API错误处理一致性
  it('对于任何HTTP错误状态码(>=400)，应抛出包含状态码的ApiError', () => {
    fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 400, max: 599 }),
        fc.string({ minLength: 1 }),
        async (statusCode, errorMessage) => {
          // Mock fetch返回错误响应
          globalThis.fetch = vi.fn().mockResolvedValue({
            ok: false,
            status: statusCode,
            statusText: 'Error',
            text: () => Promise.resolve(errorMessage),
          }) as typeof fetch

          try {
            await apiService.getActivities()
            // 如果没有抛出错误，测试失败
            expect.fail('Should have thrown an error')
          } catch (error) {
            expect(error).toBeInstanceOf(ApiError)
            expect((error as ApiError).statusCode).toBe(statusCode)
            expect((error as ApiError).message).toContain(String(statusCode))
          }
        }
      ),
      { numRuns: 100 }
    )
  })

  it('对于网络错误，应抛出状态码为0的ApiError', () => {
    fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1 }),
        async (errorMessage) => {
          // Mock fetch抛出网络错误
          globalThis.fetch = vi.fn().mockRejectedValue(new Error(errorMessage)) as typeof fetch

          try {
            await apiService.getActivities()
            expect.fail('Should have thrown an error')
          } catch (error) {
            expect(error).toBeInstanceOf(ApiError)
            expect((error as ApiError).statusCode).toBe(0)
            expect((error as ApiError).message).toContain(errorMessage)
          }
        }
      ),
      { numRuns: 100 }
    )
  })

  it('对于成功响应，应返回解析后的JSON数据', async () => {
    const mockData = {
      total: 10,
      page: 1,
      page_size: 20,
      items: [],
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
    }) as typeof fetch

    const result = await apiService.getActivities()
    expect(result).toEqual(mockData)
  })

  it('getActivity应正确处理404错误', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Activity not found'),
    }) as typeof fetch

    try {
      await apiService.getActivity('non-existent-id')
      expect.fail('Should have thrown an error')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).statusCode).toBe(404)
    }
  })

  it('refreshSource应正确处理500错误', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    }) as typeof fetch

    try {
      await apiService.refreshSource('test-source')
      expect.fail('Should have thrown an error')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).statusCode).toBe(500)
    }
  })

  it('应支持请求取消', async () => {
    const controller = new AbortController()
    
    globalThis.fetch = vi.fn().mockImplementation(() => {
      return new Promise((_, reject) => {
        controller.signal.addEventListener('abort', () => {
          const error = new Error('Aborted')
          error.name = 'AbortError'
          reject(error)
        })
      })
    }) as typeof fetch

    const promise = apiService.getActivities({}, controller.signal)
    controller.abort()

    await expect(promise).rejects.toThrow()
  })
})
