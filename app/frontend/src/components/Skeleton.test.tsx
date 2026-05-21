import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skeleton } from './Skeleton'

describe('Skeleton', () => {
  it('should render with default text variant', () => {
    render(<Skeleton />)
    const el = screen.getByRole('status')
    expect(el).toHaveClass('animate-pulse', 'bg-slate-200', 'rounded-md', 'h-4')
  })

  it('should render circular variant', () => {
    render(<Skeleton variant="circular" />)
    const el = screen.getByRole('status')
    expect(el).toHaveClass('animate-pulse', 'bg-slate-200', 'rounded-full')
  })

  it('should render rectangular variant', () => {
    render(<Skeleton variant="rectangular" />)
    const el = screen.getByRole('status')
    expect(el).toHaveClass('animate-pulse', 'bg-slate-200', 'rounded-lg')
  })

  it('should apply custom width and height as numbers', () => {
    render(<Skeleton width={200} height={40} />)
    const el = screen.getByRole('status')
    expect(el).toHaveStyle({ width: '200px', height: '40px' })
  })

  it('should apply custom width and height as strings', () => {
    render(<Skeleton width="100%" height="2rem" />)
    const el = screen.getByRole('status')
    expect(el).toHaveStyle({ width: '100%', height: '2rem' })
  })

  it('should apply custom className', () => {
    render(<Skeleton className="mt-4" />)
    const el = screen.getByRole('status')
    expect(el).toHaveClass('mt-4')
  })

  it('should have aria-label for accessibility', () => {
    render(<Skeleton />)
    const el = screen.getByRole('status')
    expect(el).toHaveAttribute('aria-label', '加载中')
  })

  it('should have aria-busy attribute', () => {
    render(<Skeleton />)
    const el = screen.getByRole('status')
    expect(el).toHaveAttribute('aria-busy', 'true')
  })

  it('should have screen reader text', () => {
    render(<Skeleton />)
    expect(screen.getByText('加载中...')).toHaveClass('sr-only')
  })
})
