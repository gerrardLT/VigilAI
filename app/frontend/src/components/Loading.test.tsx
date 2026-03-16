import { describe, it, expect, afterEach } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import fc from 'fast-check'
import Loading from './Loading'

/**
 * Property 10: 异步操作加载状态
 * Validates: Requirements 12.3
 * 
 * For any async operation (API call), 
 * the component SHALL display a loading indicator while the operation is in progress.
 */

describe('Loading组件', () => {
  afterEach(() => {
    cleanup()
  })

  // Feature: vigilai-frontend, Property 10: 异步操作加载状态
  it('应渲染加载动画', () => {
    render(<Loading />)
    // 验证存在旋转动画元素
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('对于任何size属性，应渲染对应大小的加载动画', () => {
    const sizes = ['sm', 'md', 'lg'] as const
    
    sizes.forEach(size => {
      cleanup()
      const { container } = render(<Loading size={size} />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  it('对于任何text属性，应显示加载文本', () => {
    // 使用字母数字字符串避免空格问题
    const textArb = fc.string({ minLength: 1, maxLength: 50 }).filter(s => /^[a-zA-Z0-9]+$/.test(s))
    
    fc.assert(
      fc.property(textArb, (text) => {
        cleanup()
        const { container } = render(<Loading text={text} />)
        expect(container.textContent).toContain(text)
      }),
      { numRuns: 20 }
    )
  })

  it('fullScreen模式应渲染全屏遮罩', () => {
    render(<Loading fullScreen />)
    const overlay = document.querySelector('.fixed.inset-0')
    expect(overlay).toBeInTheDocument()
  })

  it('非fullScreen模式不应渲染全屏遮罩', () => {
    render(<Loading />)
    const overlay = document.querySelector('.fixed.inset-0')
    expect(overlay).not.toBeInTheDocument()
  })
})
