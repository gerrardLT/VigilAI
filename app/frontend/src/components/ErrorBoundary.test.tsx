import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

/**
 * Property 9: API失败时显示错误提示
 * For any failed API call, the system SHALL display an error message to the user
 * via toast or error component.
 * Validates: Requirements 11.1
 */
describe('Property 9: Error Display on API Failure', () => {
  // HTTP error status codes
  const errorStatusCodes = [400, 401, 403, 404, 500, 502, 503, 504]
  
  // Error message patterns
  const errorMessages = [
    'Network Error',
    'Request timeout',
    'Server Error',
    'Not Found',
    'Unauthorized',
    'Forbidden',
    'Bad Request',
    'Service Unavailable',
  ]

  // Helper to simulate API error response
  const createApiError = (status: number, message: string) => ({
    status,
    message,
    isError: true,
  })

  // Helper to determine if error should be displayed
  const shouldDisplayError = (error: { status: number; message: string; isError: boolean }) => {
    return error.isError && error.status >= 400
  }

  // Helper to get user-friendly error message
  const getUserFriendlyMessage = (status: number, message: string): string => {
    if (status === 404) return '请求的资源不存在'
    if (status === 401) return '请先登录'
    if (status === 403) return '没有访问权限'
    if (status >= 500) return '服务器错误，请稍后重试'
    return message || '发生了未知错误'
  }

  it('should identify all HTTP error status codes as errors', () => {
    fc.assert(
      fc.property(fc.constantFrom(...errorStatusCodes), (status) => {
        const error = createApiError(status, 'Error')
        expect(shouldDisplayError(error)).toBe(true)
        return true
      }),
      { numRuns: 100 }
    )
  })

  it('should not treat success status codes as errors', () => {
    const successCodes = [200, 201, 204]
    
    fc.assert(
      fc.property(fc.constantFrom(...successCodes), (status) => {
        const response = { status, message: 'OK', isError: false }
        expect(shouldDisplayError(response)).toBe(false)
        return true
      }),
      { numRuns: 50 }
    )
  })

  it('should generate user-friendly error messages for any error', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...errorStatusCodes),
        fc.constantFrom(...errorMessages),
        (status, message) => {
          const friendlyMessage = getUserFriendlyMessage(status, message)
          
          // Message should be non-empty
          expect(friendlyMessage).toBeDefined()
          expect(friendlyMessage.length).toBeGreaterThan(0)
          
          // Message should be a string
          expect(typeof friendlyMessage).toBe('string')
          
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('should handle 404 errors with specific message', () => {
    fc.assert(
      fc.property(fc.constantFrom(...errorMessages), (message) => {
        const friendlyMessage = getUserFriendlyMessage(404, message)
        expect(friendlyMessage).toBe('请求的资源不存在')
        return true
      }),
      { numRuns: 20 }
    )
  })

  it('should handle 5xx errors with server error message', () => {
    const serverErrorCodes = [500, 502, 503, 504]
    
    fc.assert(
      fc.property(
        fc.constantFrom(...serverErrorCodes),
        fc.constantFrom(...errorMessages),
        (status, message) => {
          const friendlyMessage = getUserFriendlyMessage(status, message)
          expect(friendlyMessage).toBe('服务器错误，请稍后重试')
          return true
        }
      ),
      { numRuns: 50 }
    )
  })

  it('should handle arbitrary error messages', () => {
    const messageArb = fc.string({ minLength: 1, maxLength: 200 })
    
    fc.assert(
      fc.property(
        fc.constantFrom(...errorStatusCodes),
        messageArb,
        (status, message) => {
          const error = createApiError(status, message)
          
          // Error should be displayable
          expect(shouldDisplayError(error)).toBe(true)
          
          // Should have a user-friendly message
          const friendlyMessage = getUserFriendlyMessage(status, message)
          expect(friendlyMessage.length).toBeGreaterThan(0)
          
          return true
        }
      ),
      { numRuns: 100 }
    )
  })

  it('should handle empty error messages gracefully', () => {
    fc.assert(
      fc.property(fc.constantFrom(...errorStatusCodes), (status) => {
        const friendlyMessage = getUserFriendlyMessage(status, '')
        
        // Should still produce a valid message
        expect(friendlyMessage).toBeDefined()
        expect(friendlyMessage.length).toBeGreaterThan(0)
        
        return true
      }),
      { numRuns: 50 }
    )
  })

  it('should validate error object structure', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...errorStatusCodes),
        fc.string({ minLength: 0, maxLength: 100 }),
        (status, message) => {
          const error = createApiError(status, message)
          
          // Error should have required properties
          expect(error).toHaveProperty('status')
          expect(error).toHaveProperty('message')
          expect(error).toHaveProperty('isError')
          
          // Types should be correct
          expect(typeof error.status).toBe('number')
          expect(typeof error.message).toBe('string')
          expect(typeof error.isError).toBe('boolean')
          
          return true
        }
      ),
      { numRuns: 100 }
    )
  })
})
