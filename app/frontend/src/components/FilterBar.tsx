import { useEffect, useState, useMemo } from 'react'
import { api } from '../services/api'
import type { Source } from '../types'
import { CATEGORY_OPTIONS } from '../utils/constants'

interface FilterBarProps {
  category: string
  sourceId: string
  onCategoryChange: (category: string) => void
  onSourceChange: (sourceId: string) => void
  onClear: () => void
}

/**
 * 筛选栏组件
 * 使用Tab形式展示类别和信息源筛选
 * 选择类别后，来源列表会根据类别进行过滤
 */
export function FilterBar({
  category,
  sourceId,
  onCategoryChange,
  onSourceChange,
  onClear,
}: FilterBarProps) {
  const [sources, setSources] = useState<Source[]>([])
  const [showAllSources, setShowAllSources] = useState(false)

  useEffect(() => {
    api.getSources().then(setSources).catch(console.error)
  }, [])

  // 根据选中的类别过滤来源
  const filteredSources = useMemo(() => {
    if (!category) {
      return sources
    }
    // 过滤出匹配类别的来源
    return sources.filter(source => source.category === category)
  }, [sources, category])

  // 当类别变化时，如果当前选中的来源不在过滤后的列表中，清除来源选择
  useEffect(() => {
    if (sourceId && category) {
      const sourceInCategory = filteredSources.some(s => s.id === sourceId)
      if (!sourceInCategory) {
        onSourceChange('')
      }
    }
  }, [category, sourceId, filteredSources, onSourceChange])

  const hasFilters = category || sourceId

  // 显示的来源数量限制
  const visibleSourceCount = showAllSources ? filteredSources.length : 8
  const visibleSources = filteredSources.slice(0, visibleSourceCount)
  const hasMoreSources = filteredSources.length > 8

  return (
    <div className="space-y-4 w-full">
      {/* 类别Tab */}
      <div>
        <div className="text-sm text-gray-500 mb-2">类别</div>
        <div className="flex flex-wrap gap-2">
          {CATEGORY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => onCategoryChange(opt.value)}
              className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                category === opt.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 来源Tab */}
      <div>
        <div className="text-sm text-gray-500 mb-2">
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
              onClick={() => setShowAllSources(!showAllSources)}
              className="px-3 py-1.5 text-sm rounded-full bg-gray-50 text-gray-500 hover:bg-gray-100 transition-colors"
            >
              {showAllSources ? '收起' : `+${filteredSources.length - 8} 更多`}
            </button>
          )}
        </div>
      </div>

      {/* 清除筛选 */}
      {hasFilters && (
        <button
          onClick={onClear}
          className="text-sm text-gray-500 hover:text-gray-700 underline"
        >
          清除筛选
        </button>
      )}
    </div>
  )
}

export default FilterBar
