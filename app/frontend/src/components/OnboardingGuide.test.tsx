import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { OnboardingGuide } from './OnboardingGuide'

describe('OnboardingGuide', () => {
  it('renders prompt cards for opportunity domain', () => {
    render(<OnboardingGuide domainType="opportunity" onSelectPrompt={() => {}} />)

    expect(screen.getByText('发现机会')).toBeInTheDocument()
    expect(screen.getByText('分析机会')).toBeInTheDocument()
    expect(screen.getByText('跟进管理')).toBeInTheDocument()
    expect(screen.getByText('系统状态')).toBeInTheDocument()
  })

  it('renders prompt cards for product_selection domain', () => {
    render(<OnboardingGuide domainType="product_selection" onSelectPrompt={() => {}} />)

    expect(screen.getByText('选品研究')).toBeInTheDocument()
    expect(screen.getByText('对比分析')).toBeInTheDocument()
    expect(screen.getByText('市场趋势')).toBeInTheDocument()
    expect(screen.getByText('跟进提醒')).toBeInTheDocument()
  })

  it('calls onSelectPrompt with correct prompt text when card is clicked', () => {
    const onSelectPrompt = vi.fn()
    render(<OnboardingGuide domainType="opportunity" onSelectPrompt={onSelectPrompt} />)

    fireEvent.click(screen.getByText('发现机会'))
    expect(onSelectPrompt).toHaveBeenCalledWith('帮我找最近的黑客松和赏金机会')

    fireEvent.click(screen.getByText('分析机会'))
    expect(onSelectPrompt).toHaveBeenCalledWith('分析这个机会值不值得参加')
  })

  it('displays capability description text', () => {
    const { rerender } = render(
      <OnboardingGuide domainType="opportunity" onSelectPrompt={() => {}} />
    )
    expect(
      screen.getByText(/帮你发现黑客松、赏金、Grant 等开发者赚钱机会/)
    ).toBeInTheDocument()

    rerender(<OnboardingGuide domainType="product_selection" onSelectPrompt={() => {}} />)
    expect(
      screen.getByText(/帮你研究淘宝和闲鱼的选品机会/)
    ).toBeInTheDocument()
  })

  it('has at least 4 prompt cards per domain', () => {
    const { container, rerender } = render(
      <OnboardingGuide domainType="opportunity" onSelectPrompt={() => {}} />
    )
    const opportunityButtons = container.querySelectorAll('button')
    expect(opportunityButtons.length).toBeGreaterThanOrEqual(4)

    rerender(<OnboardingGuide domainType="product_selection" onSelectPrompt={() => {}} />)
    const selectionButtons = container.querySelectorAll('button')
    expect(selectionButtons.length).toBeGreaterThanOrEqual(4)
  })
})
