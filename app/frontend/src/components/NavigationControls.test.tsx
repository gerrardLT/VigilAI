import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Pagination } from './Pagination'
import { SearchBox } from './SearchBox'
import { SortSelect } from './SortSelect'

describe('navigation controls accessibility', () => {
  it('exposes Chinese labels for search and sort controls', () => {
    const onSearchChange = vi.fn()
    const onSortByChange = vi.fn()
    const onSortOrderChange = vi.fn()

    render(
      <div>
        <SearchBox value="" onChange={onSearchChange} />
        <SortSelect
          sortBy="score"
          sortOrder="desc"
          onSortByChange={onSortByChange}
          onSortOrderChange={onSortOrderChange}
        />
      </div>
    )

    expect(screen.getByRole('textbox', { name: '搜索活动' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: '排序字段' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '切换为升序排序' })).toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox', { name: '搜索活动' }), {
      target: { value: '黑客松' },
    })
    fireEvent.click(screen.getByRole('button', { name: '切换为升序排序' }))

    expect(onSortOrderChange).toHaveBeenCalledWith('asc')
  })

  it('marks the current page in the pagination nav', () => {
    const onPageChange = vi.fn()

    render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />)

    expect(screen.getByRole('navigation', { name: '分页导航' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '第 3 页' })).toHaveAttribute('aria-current', 'page')

    fireEvent.click(screen.getByRole('button', { name: '下一页' }))

    expect(onPageChange).toHaveBeenCalledWith(4)
  })
})
