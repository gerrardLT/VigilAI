import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import type { Source } from '../types'
import { CATEGORY_OPTIONS } from '../utils/constants'

interface FilterBarProps {
  category: string
  sourceId: string
  deadlineLevel: string
  trackingState: string
  onCategoryChange: (category: string) => void
  onSourceChange: (sourceId: string) => void
  onDeadlineLevelChange: (deadlineLevel: string) => void
  onTrackingStateChange: (trackingState: string) => void
  onClear: () => void
}

const DEADLINE_OPTIONS = [
  { value: '', label: '全部时效' },
  { value: 'urgent', label: '紧急截止' },
  { value: 'soon', label: '即将截止' },
  { value: 'upcoming', label: '近期开放' },
]

const TRACKING_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'tracked', label: '已跟进' },
  { value: 'favorited', label: '已收藏' },
  { value: 'untracked', label: '待处理' },
]

export function FilterBar({
  category,
  sourceId,
  deadlineLevel,
  trackingState,
  onCategoryChange,
  onSourceChange,
  onDeadlineLevelChange,
  onTrackingStateChange,
  onClear,
}: FilterBarProps) {
  const [sources, setSources] = useState<Source[]>([])
  const [showAllSources, setShowAllSources] = useState(false)

  useEffect(() => {
    api.getSources().then(setSources).catch(console.error)
  }, [])

  const filteredSources = useMemo(() => {
    if (!category) {
      return sources
    }
    return sources.filter(source => source.category === category)
  }, [sources, category])

  useEffect(() => {
    if (sourceId && category) {
      const sourceInCategory = filteredSources.some(source => source.id === sourceId)
      if (!sourceInCategory) {
        onSourceChange('')
      }
    }
  }, [category, sourceId, filteredSources, onSourceChange])

  const hasFilters = category || sourceId || deadlineLevel || trackingState
  const visibleSourceCount = showAllSources ? filteredSources.length : 8
  const visibleSources = filteredSources.slice(0, visibleSourceCount)
  const hasMoreSources = filteredSources.length > 8

  const renderChipGroup = (
    options: ReadonlyArray<{ value: string; label: string }>,
    activeValue: string,
    onChange: (value: string) => void
  ) => (
    <div className="flex flex-wrap gap-2">
      {options.map(option => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
            activeValue === option.value
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )

  return (
    <div className="space-y-4 w-full">
      <div>
        <div className="mb-2 text-sm text-gray-500">类别</div>
        {renderChipGroup(CATEGORY_OPTIONS, category, onCategoryChange)}
      </div>

      <div>
        <div className="mb-2 text-sm text-gray-500">
          来源 {category && `(${filteredSources.length})`}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => onSourceChange('')}
            className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
              sourceId === ''
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            全部来源
          </button>
          {visibleSources.map(source => (
            <button
              key={source.id}
              onClick={() => onSourceChange(source.id)}
              className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                sourceId === source.id
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {source.name}
            </button>
          ))}
          {hasMoreSources && (
            <button
              onClick={() => setShowAllSources(current => !current)}
              className="px-3 py-1.5 text-sm rounded-full bg-gray-50 text-gray-500 transition-colors hover:bg-gray-100"
            >
              {showAllSources ? '收起' : `+${filteredSources.length - 8} 更多`}
            </button>
          )}
        </div>
      </div>

      <div>
        <div className="mb-2 text-sm text-gray-500">截止优先级</div>
        {renderChipGroup(DEADLINE_OPTIONS, deadlineLevel, onDeadlineLevelChange)}
      </div>

      <div>
        <div className="mb-2 text-sm text-gray-500">处理状态</div>
        {renderChipGroup(TRACKING_OPTIONS, trackingState, onTrackingStateChange)}
      </div>

      {hasFilters && (
        <button
          onClick={onClear}
          className="text-sm text-gray-500 underline hover:text-gray-700"
        >
          清除筛选
        </button>
      )}
    </div>
  )
}

export default FilterBar
