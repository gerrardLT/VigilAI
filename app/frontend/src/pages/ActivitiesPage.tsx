import { useSearchParams } from 'react-router-dom'
import { useCallback, useEffect } from 'react'
import { useActivities } from '../hooks/useActivities'
import { FilterBar } from '../components/FilterBar'
import { SearchBox } from '../components/SearchBox'
import { SortSelect } from '../components/SortSelect'
import { ActivityCard } from '../components/ActivityCard'
import { Pagination } from '../components/Pagination'
import { Loading } from '../components/Loading'
import { ErrorMessage } from '../components/ErrorMessage'
import { DEFAULT_SORT_BY, DEFAULT_SORT_ORDER } from '../utils/constants'

/**
 * 活动列表页面
 * 集成筛选、搜索、排序、分页功能
 */
export function ActivitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // 从URL参数初始化筛选条件
  const initialFilters = {
    category: searchParams.get('category') || '',
    source_id: searchParams.get('source_id') || '',
    search: searchParams.get('search') || '',
    sort_by: searchParams.get('sort_by') || DEFAULT_SORT_BY,
    sort_order: (searchParams.get('sort_order') as 'asc' | 'desc') || DEFAULT_SORT_ORDER,
    page: parseInt(searchParams.get('page') || '1', 10),
  }

  const {
    activities,
    total,
    page,
    totalPages,
    loading,
    error,
    filters,
    setFilters,
    setPage,
    refetch,
  } = useActivities(initialFilters)

  // 同步筛选条件到URL
  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.category) params.set('category', filters.category)
    if (filters.source_id) params.set('source_id', filters.source_id)
    if (filters.search) params.set('search', filters.search)
    if (filters.sort_by && filters.sort_by !== DEFAULT_SORT_BY) {
      params.set('sort_by', filters.sort_by)
    }
    if (filters.sort_order && filters.sort_order !== DEFAULT_SORT_ORDER) {
      params.set('sort_order', filters.sort_order)
    }
    if (filters.page && filters.page > 1) {
      params.set('page', String(filters.page))
    }
    setSearchParams(params, { replace: true })
  }, [filters, setSearchParams])

  // 处理类别变化
  const handleCategoryChange = useCallback((category: string) => {
    setFilters({ category })
  }, [setFilters])

  // 处理信息源变化
  const handleSourceChange = useCallback((source_id: string) => {
    setFilters({ source_id })
  }, [setFilters])

  // 处理搜索变化
  const handleSearchChange = useCallback((search: string) => {
    setFilters({ search })
  }, [setFilters])

  // 处理排序字段变化
  const handleSortByChange = useCallback((sort_by: string) => {
    setFilters({ sort_by })
  }, [setFilters])

  // 处理排序方向变化
  const handleSortOrderChange = useCallback((sort_order: 'asc' | 'desc') => {
    setFilters({ sort_order })
  }, [setFilters])

  // 清除所有筛选
  const handleClearFilters = useCallback(() => {
    setFilters({
      category: '',
      source_id: '',
      search: '',
      sort_by: DEFAULT_SORT_BY,
      sort_order: DEFAULT_SORT_ORDER,
    })
  }, [setFilters])

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">活动列表</h1>
        <span className="text-sm text-gray-500">共 {total} 个活动</span>
      </div>

      {/* 筛选和搜索栏 */}
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        {/* 搜索和排序 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3">
          <SearchBox
            value={filters.search || ''}
            onChange={handleSearchChange}
          />
          <SortSelect
            sortBy={filters.sort_by || DEFAULT_SORT_BY}
            sortOrder={filters.sort_order || DEFAULT_SORT_ORDER}
            onSortByChange={handleSortByChange}
            onSortOrderChange={handleSortOrderChange}
          />
        </div>

        {/* Tab筛选器 */}
        <FilterBar
          category={filters.category || ''}
          sourceId={filters.source_id || ''}
          onCategoryChange={handleCategoryChange}
          onSourceChange={handleSourceChange}
          onClear={handleClearFilters}
        />
      </div>

      {/* 内容区域 */}
      {loading ? (
        <Loading text="加载活动中..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={refetch} />
      ) : activities.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-5xl mb-4">📭</div>
          <p className="text-gray-500">暂无活动</p>
          {(filters.category || filters.source_id || filters.search) && (
            <button
              onClick={handleClearFilters}
              className="mt-4 text-primary-600 hover:text-primary-700 underline"
            >
              清除筛选条件
            </button>
          )}
        </div>
      ) : (
        <>
          {/* 活动卡片网格 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activities.map(activity => (
              <ActivityCard key={activity.id} activity={activity} />
            ))}
          </div>

          {/* 分页 */}
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  )
}

export default ActivitiesPage
