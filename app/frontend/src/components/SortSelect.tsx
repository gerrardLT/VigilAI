import { SORT_OPTIONS } from '../utils/constants'

interface SortSelectProps {
  sortBy: string
  sortOrder: 'asc' | 'desc'
  onSortByChange: (sortBy: string) => void
  onSortOrderChange: (sortOrder: 'asc' | 'desc') => void
}

/**
 * 排序选择组件
 */
export function SortSelect({
  sortBy,
  sortOrder,
  onSortByChange,
  onSortOrderChange,
}: SortSelectProps) {
  const nextSortOrderLabel = sortOrder === 'asc' ? '切换为降序排序' : '切换为升序排序'

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500">排序：</span>
      
      {/* 排序字段 */}
      <select
        aria-label="排序字段"
        value={sortBy}
        onChange={e => onSortByChange(e.target.value)}
        className="select text-sm"
      >
        {SORT_OPTIONS.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* 排序方向 */}
      <button
        type="button"
        aria-label={nextSortOrderLabel}
        onClick={() => onSortOrderChange(sortOrder === 'asc' ? 'desc' : 'asc')}
        className="min-h-[44px] min-w-[44px] rounded-lg p-2 hover:bg-gray-100 transition-colors"
        title={sortOrder === 'asc' ? '升序' : '降序'}
      >
        {sortOrder === 'asc' ? (
          <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" />
          </svg>
        )}
      </button>
    </div>
  )
}

export default SortSelect
