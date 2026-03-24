import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ActivityCard } from '../components/ActivityCard'
import { ErrorMessage } from '../components/ErrorMessage'
import { FilterBar } from '../components/FilterBar'
import { Loading } from '../components/Loading'
import { Pagination } from '../components/Pagination'
import { SearchBox } from '../components/SearchBox'
import { SortSelect } from '../components/SortSelect'
import { useActivities } from '../hooks/useActivities'
import { api } from '../services/api'
import type { Activity, ActivityFilters } from '../types'
import { DEFAULT_SORT_BY, DEFAULT_SORT_ORDER } from '../utils/constants'

function buildTrackingFilters(trackingState: string): Pick<ActivityFilters, 'tracking_state' | 'is_tracking' | 'is_favorited'> {
  if (trackingState === 'tracked') {
    return { tracking_state: trackingState, is_tracking: true, is_favorited: undefined }
  }
  if (trackingState === 'favorited') {
    return { tracking_state: trackingState, is_tracking: true, is_favorited: true }
  }
  if (trackingState === 'untracked') {
    return { tracking_state: trackingState, is_tracking: false, is_favorited: undefined }
  }
  return { tracking_state: '', is_tracking: undefined, is_favorited: undefined }
}

async function runBatchTrackingAction(activities: Activity[]) {
  await Promise.all(
    activities.map(activity =>
      activity.is_tracking
        ? api.updateTracking(activity.id, { status: 'tracking' })
        : api.createTracking(activity.id, { status: 'tracking' })
    )
  )
}

async function runBatchFavoriteAction(activities: Activity[]) {
  await Promise.all(
    activities.map(activity =>
      activity.is_tracking
        ? api.updateTracking(activity.id, { is_favorited: true })
        : api.createTracking(activity.id, { status: 'saved', is_favorited: true })
    )
  )
}

export function ActivitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [isApplyingBatch, setIsApplyingBatch] = useState(false)

  const initialFilters: ActivityFilters = {
    category: searchParams.get('category') || '',
    source_id: searchParams.get('source_id') || '',
    search: searchParams.get('search') || '',
    deadline_level: searchParams.get('deadline_level') || '',
    tracking_state: searchParams.get('tracking_state') || '',
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
  } = useActivities({
    ...initialFilters,
    ...buildTrackingFilters(initialFilters.tracking_state || ''),
  })

  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.category) params.set('category', filters.category)
    if (filters.source_id) params.set('source_id', filters.source_id)
    if (filters.search) params.set('search', filters.search)
    if (filters.deadline_level) params.set('deadline_level', filters.deadline_level)
    if (filters.tracking_state) params.set('tracking_state', filters.tracking_state)
    if (filters.sort_by && filters.sort_by !== DEFAULT_SORT_BY) {
      params.set('sort_by', filters.sort_by)
    }
    if (filters.sort_order && filters.sort_order !== DEFAULT_SORT_ORDER) {
      params.set('sort_order', filters.sort_order)
    }
    if (filters.page && filters.page > 1) {
      params.set('page', String(filters.page))
    }
    if (params.toString() !== searchParams.toString()) {
      setSearchParams(params, { replace: true })
    }
  }, [filters, searchParams, setSearchParams])

  useEffect(() => {
    setSelectedIds(current => {
      const next = current.filter(id => activities.some(activity => activity.id === id))
      const unchanged =
        next.length === current.length && next.every((id, index) => id === current[index])
      return unchanged ? current : next
    })
  }, [activities])

  const selectedActivities = useMemo(
    () => activities.filter(activity => selectedIds.includes(activity.id)),
    [activities, selectedIds]
  )

  const handleCategoryChange = useCallback((category: string) => {
    setFilters({ category })
  }, [setFilters])

  const handleSourceChange = useCallback((source_id: string) => {
    setFilters({ source_id })
  }, [setFilters])

  const handleSearchChange = useCallback((search: string) => {
    setFilters({ search })
  }, [setFilters])

  const handleSortByChange = useCallback((sort_by: string) => {
    setFilters({ sort_by })
  }, [setFilters])

  const handleSortOrderChange = useCallback((sort_order: 'asc' | 'desc') => {
    setFilters({ sort_order })
  }, [setFilters])

  const handleDeadlineLevelChange = useCallback((deadline_level: string) => {
    setFilters({ deadline_level })
  }, [setFilters])

  const handleTrackingStateChange = useCallback((tracking_state: string) => {
    setFilters(buildTrackingFilters(tracking_state))
  }, [setFilters])

  const handleClearFilters = useCallback(() => {
    setFilters({
      category: '',
      source_id: '',
      search: '',
      deadline_level: '',
      tracking_state: '',
      is_tracking: undefined,
      is_favorited: undefined,
      sort_by: DEFAULT_SORT_BY,
      sort_order: DEFAULT_SORT_ORDER,
    })
  }, [setFilters])

  const toggleSelection = useCallback((activityId: string) => {
    setSelectedIds(current =>
      current.includes(activityId)
        ? current.filter(id => id !== activityId)
        : [...current, activityId]
    )
  }, [])

  const applyBatchAction = useCallback(async (
    action: 'track' | 'favorite'
  ) => {
    if (selectedActivities.length === 0) {
      return
    }

    setIsApplyingBatch(true)
    try {
      if (action === 'track') {
        await runBatchTrackingAction(selectedActivities)
      } else {
        await runBatchFavoriteAction(selectedActivities)
      }
      await refetch()
    } catch (batchError) {
      console.error(batchError)
    } finally {
      setIsApplyingBatch(false)
    }
  }, [refetch, selectedActivities])

  const hasActiveFilters = Boolean(
    filters.category ||
      filters.source_id ||
      filters.search ||
      filters.deadline_level ||
      filters.tracking_state
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">机会池</h1>
          <p className="mt-2 text-sm text-gray-600">
            按推荐优先级筛选、批量处理并推进机会。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
          <span>{total} 个机会</span>
          <span>{selectedIds.length} 个已选</span>
        </div>
      </div>

      <div className="space-y-4 rounded-xl bg-white p-4 shadow">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
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

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="batch-track-button"
              disabled={selectedIds.length === 0 || isApplyingBatch}
              onClick={() => void applyBatchAction('track')}
              className="rounded-full bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              批量加入跟进
            </button>
            <button
              type="button"
              data-testid="batch-favorite-button"
              disabled={selectedIds.length === 0 || isApplyingBatch}
              onClick={() => void applyBatchAction('favorite')}
              className="rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
            >
              批量收藏
            </button>
          </div>
        </div>

        <FilterBar
          category={filters.category || ''}
          sourceId={filters.source_id || ''}
          deadlineLevel={filters.deadline_level || ''}
          trackingState={filters.tracking_state || ''}
          onCategoryChange={handleCategoryChange}
          onSourceChange={handleSourceChange}
          onDeadlineLevelChange={handleDeadlineLevelChange}
          onTrackingStateChange={handleTrackingStateChange}
          onClear={handleClearFilters}
        />
      </div>

      {loading ? (
        <Loading text="加载机会池中..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={refetch} />
      ) : activities.length === 0 ? (
        <div className="rounded-xl bg-white py-14 text-center shadow">
          <div className="mb-4 text-5xl text-gray-300">◌</div>
          <p className="text-gray-500">当前筛选条件下还没有机会</p>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="mt-4 text-sm text-primary-600 underline hover:text-primary-700"
            >
              清除筛选
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {activities.map(activity => (
              <div key={activity.id} className="relative">
                <label className="absolute right-3 top-3 z-10 flex items-center gap-2 rounded-full bg-white/95 px-3 py-1 text-xs font-medium text-gray-700 shadow">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(activity.id)}
                    onChange={() => toggleSelection(activity.id)}
                    data-testid={`select-activity-${activity.id.split('-').pop() || activity.id}`}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  选择
                </label>
                <ActivityCard activity={activity} />
              </div>
            ))}
          </div>

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
