import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import fc from 'fast-check'
import SourceCard from './SourceCard'
import type { Source, SourceType, SourceStatus } from '../types'
import { STATUS_TEXT_MAP } from '../utils/constants'

/**
 * Property 8: 信息源状态显示完整性
 * Validates: Requirements 8.2, 8.3
 * 
 * For any Source object, the SourceCard SHALL display name, type, status with appropriate color indicator, 
 * last_run timestamp, and activity_count.
 */

const VALID_SOURCE_TYPES: SourceType[] = ['rss', 'web', 'api']
const VALID_SOURCE_STATUSES: SourceStatus[] = ['idle', 'running', 'success', 'error']

// 使用字母数字字符串避免特殊字符问题
const alphanumericString = (minLength: number, maxLength: number) =>
  fc.string({ minLength, maxLength }).filter(s => /^[a-zA-Z0-9]+$/.test(s) && s.length >= minLength)

// 生成有效的Source对象
const sourceArbitrary = fc.record({
  id: alphanumericString(1, 20),
  name: alphanumericString(3, 30),
  type: fc.constantFrom(...VALID_SOURCE_TYPES),
  status: fc.constantFrom(...VALID_SOURCE_STATUSES),
  last_run: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
  last_success: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
  activity_count: fc.nat({ max: 1000 }),
  error_message: fc.option(alphanumericString(5, 50), { nil: null }),
})

describe('SourceCard状态显示完整性', () => {
  const mockOnRefresh = vi.fn()

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  // Feature: vigilai-frontend, Property 8: 信息源状态显示完整性
  it('对于任何Source，应显示name', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        cleanup()
        const { container } = render(<SourceCard source={source} refreshing={false} onRefresh={mockOnRefresh} />)
        expect(container.textContent).toContain(source.name)
      }),
      { numRuns: 50 }
    )
  })

  it('对于任何Source，应显示type', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        cleanup()
        const { container } = render(<SourceCard source={source} refreshing={false} onRefresh={mockOnRefresh} />)
        expect(container.textContent).toContain(source.type.toUpperCase())
      }),
      { numRuns: 50 }
    )
  })

  it('对于任何Source，应显示status文本', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        cleanup()
        const { container } = render(<SourceCard source={source} refreshing={false} onRefresh={mockOnRefresh} />)
        const statusText = STATUS_TEXT_MAP[source.status]
        expect(container.textContent).toContain(statusText)
      }),
      { numRuns: 50 }
    )
  })

  it('对于任何Source，应显示activity_count', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        cleanup()
        const { container } = render(<SourceCard source={source} refreshing={false} onRefresh={mockOnRefresh} />)
        expect(container.textContent).toContain(String(source.activity_count))
      }),
      { numRuns: 50 }
    )
  })

  it('对于任何Source，应显示状态指示器', () => {
    fc.assert(
      fc.property(sourceArbitrary, (source: Source) => {
        cleanup()
        const { container } = render(
          <SourceCard source={source} refreshing={false} onRefresh={mockOnRefresh} />
        )
        // 验证状态指示器存在（圆形元素）
        const indicator = container.querySelector('.rounded-full.w-2.h-2')
        expect(indicator).toBeInTheDocument()
      }),
      { numRuns: 50 }
    )
  })

  it('当Source有error_message时，应显示错误信息', () => {
    const sourceWithError: Source = {
      id: 'test-error',
      name: 'Error Source',
      type: 'rss',
      status: 'error',
      last_run: new Date().toISOString(),
      last_success: null,
      activity_count: 0,
      error_message: 'Connection timeout',
    }

    render(<SourceCard source={sourceWithError} refreshing={false} onRefresh={mockOnRefresh} />)
    expect(screen.getByText(/Connection timeout/)).toBeInTheDocument()
  })

  it('当Source没有error_message时，不应显示错误区域', () => {
    const sourceWithoutError: Source = {
      id: 'test-success',
      name: 'Success Source',
      type: 'rss',
      status: 'success',
      last_run: new Date().toISOString(),
      last_success: new Date().toISOString(),
      activity_count: 10,
      error_message: null,
    }

    render(<SourceCard source={sourceWithoutError} refreshing={false} onRefresh={mockOnRefresh} />)
    expect(screen.queryByText(/错误:/)).not.toBeInTheDocument()
  })

  it('refreshing为true时，应显示加载状态', () => {
    const source: Source = {
      id: 'test-refresh',
      name: 'Refreshing Source',
      type: 'api',
      status: 'running',
      last_run: null,
      last_success: null,
      activity_count: 0,
      error_message: null,
    }

    render(<SourceCard source={source} refreshing={true} onRefresh={mockOnRefresh} />)
    expect(screen.getByText('刷新中')).toBeInTheDocument()
  })

  it('refreshing为false时，应显示刷新按钮', () => {
    const source: Source = {
      id: 'test-idle',
      name: 'Idle Source',
      type: 'web',
      status: 'idle',
      last_run: null,
      last_success: null,
      activity_count: 0,
      error_message: null,
    }

    render(<SourceCard source={source} refreshing={false} onRefresh={mockOnRefresh} />)
    expect(screen.getByText('刷新')).toBeInTheDocument()
  })
})
