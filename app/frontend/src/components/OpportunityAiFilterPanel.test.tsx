import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { OpportunityAiFilterPanel } from './OpportunityAiFilterPanel'

describe('OpportunityAiFilterPanel', () => {
  it('renders Chinese placeholder, actions, and summary', () => {
    const onChange = vi.fn()
    const onSubmit = vi.fn()
    const onClear = vi.fn()

    render(
      <OpportunityAiFilterPanel
        value="只保留适合独立开发者的机会"
        loading={false}
        error={null}
        summary={{
          query: '只保留适合独立开发者的机会',
          parsed_intent_summary: '筛选适合单人开发的机会',
          reason_summary: '优先保留单人友好的机会',
          candidate_count: 2,
          matched_count: 1,
          discarded_count: 1,
          items: [],
        }}
        onChange={onChange}
        onSubmit={onSubmit}
        onClear={onClear}
      />
    )

    expect(
      screen.getByPlaceholderText('例如：只保留适合独立开发者、奖金明确、两周内截止的线上机会')
    ).toBeInTheDocument()
    expect(screen.getByText('筛选适合单人开发的机会')).toBeInTheDocument()
    expect(screen.getByText('保留 1 个')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '开始 AI 精筛' }))
    expect(onSubmit).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '清除 AI 条件' }))
    expect(onClear).toHaveBeenCalled()
  })
})
