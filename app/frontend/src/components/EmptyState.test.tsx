import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('should render title', () => {
    render(<EmptyState title="暂无数据" />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('should render description when provided', () => {
    render(<EmptyState title="暂无数据" description="请稍后再试" />)
    expect(screen.getByText('请稍后再试')).toBeInTheDocument()
  })

  it('should not render description when not provided', () => {
    render(<EmptyState title="暂无数据" />)
    const container = screen.getByRole('status')
    expect(container.querySelectorAll('p')).toHaveLength(0)
  })

  it('should render icon when provided', () => {
    render(<EmptyState title="暂无数据" icon={<span data-testid="icon">📭</span>} />)
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('should mark icon as aria-hidden', () => {
    render(<EmptyState title="暂无数据" icon={<span>📭</span>} />)
    const iconContainer = screen.getByText('📭').parentElement
    expect(iconContainer).toHaveAttribute('aria-hidden', 'true')
  })

  it('should render action button when action provided', () => {
    const onClick = vi.fn()
    render(<EmptyState title="暂无数据" action={{ label: '刷新', onClick }} />)
    expect(screen.getByText('刷新')).toBeInTheDocument()
  })

  it('should call action onClick when button is clicked', () => {
    const onClick = vi.fn()
    render(<EmptyState title="暂无数据" action={{ label: '刷新', onClick }} />)
    fireEvent.click(screen.getByText('刷新'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('should not render action button when action not provided', () => {
    render(<EmptyState title="暂无数据" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('should have centered layout with py-12', () => {
    render(<EmptyState title="暂无数据" />)
    const container = screen.getByRole('status')
    expect(container).toHaveClass('py-12', 'text-center')
  })

  it('should have role=status for accessibility', () => {
    render(<EmptyState title="暂无数据" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
