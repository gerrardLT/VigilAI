import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import type { Source } from '../types'
import {
  CATEGORY_OPTIONS,
  DEADLINE_OPTIONS,
  EFFORT_LEVEL_OPTIONS,
  PRIZE_RANGE_OPTIONS,
  REMOTE_MODE_OPTIONS,
  REWARD_CLARITY_OPTIONS,
  SOLO_FRIENDLINESS_OPTIONS,
  TRACKING_OPTIONS,
  TRUST_LEVEL_OPTIONS,
} from '../utils/constants'

interface FilterBarProps {
  category: string
  sourceId: string
  deadlineLevel: string
  prizeRange: string
  soloFriendliness: string
  rewardClarity: string
  effortLevel: string
  trustLevel: string
  remoteMode: string
  trackingState: string
  onCategoryChange: (category: string) => void
  onSourceChange: (sourceId: string) => void
  onDeadlineLevelChange: (deadlineLevel: string) => void
  onPrizeRangeChange: (prizeRange: string) => void
  onSoloFriendlinessChange: (soloFriendliness: string) => void
  onRewardClarityChange: (rewardClarity: string) => void
  onEffortLevelChange: (effortLevel: string) => void
  onTrustLevelChange: (trustLevel: string) => void
  onRemoteModeChange: (remoteMode: string) => void
  onTrackingStateChange: (trackingState: string) => void
  onClear: () => void
}

function renderChipGroup(
  options: ReadonlyArray<{ value: string; label: string }>,
  activeValue: string,
  onChange: (value: string) => void
) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(option => (
        <button
          key={option.value || option.label}
          type="button"
          aria-pressed={activeValue === option.value}
          onClick={() => onChange(option.value)}
          className={`min-h-[40px] rounded-full px-3.5 py-2 text-sm transition-colors ${
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
}

function FilterSection({
  title,
  options,
  value,
  onChange,
}: {
  title: string
  options: ReadonlyArray<{ value: string; label: string }>
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium text-gray-600">{title}</div>
      {renderChipGroup(options, value, onChange)}
    </div>
  )
}

export function FilterBar({
  category,
  sourceId,
  deadlineLevel,
  prizeRange,
  soloFriendliness,
  rewardClarity,
  effortLevel,
  trustLevel,
  remoteMode,
  trackingState,
  onCategoryChange,
  onSourceChange,
  onDeadlineLevelChange,
  onPrizeRangeChange,
  onSoloFriendlinessChange,
  onRewardClarityChange,
  onEffortLevelChange,
  onTrustLevelChange,
  onRemoteModeChange,
  onTrackingStateChange,
  onClear,
}: FilterBarProps) {
  const [sources, setSources] = useState<Source[]>([])
  const [showAllSources, setShowAllSources] = useState(false)

  useEffect(() => {
    api.getSources().then(setSources).catch(() => setSources([]))
  }, [])

  const opportunitySources = useMemo(
    () => sources.filter(source => source.category !== 'news'),
    [sources]
  )

  const filteredSources = useMemo(() => {
    if (!category) {
      return opportunitySources
    }
    return opportunitySources.filter(source => source.category === category)
  }, [opportunitySources, category])

  useEffect(() => {
    if (sourceId && category) {
      const sourceInCategory = filteredSources.some(source => source.id === sourceId)
      if (!sourceInCategory) {
        onSourceChange('')
      }
    }
  }, [category, filteredSources, onSourceChange, sourceId])

  const hasFilters = Boolean(
    category ||
      sourceId ||
      deadlineLevel ||
      prizeRange ||
      soloFriendliness ||
      rewardClarity ||
      effortLevel ||
      trustLevel ||
      remoteMode ||
      trackingState
  )

  const visibleSourceCount = showAllSources ? filteredSources.length : 8
  const visibleSources = filteredSources.slice(0, visibleSourceCount)
  const hasMoreSources = filteredSources.length > 8

  return (
    <div className="space-y-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <div className="space-y-1">
        <div className="text-xs font-medium uppercase tracking-[0.24em] text-slate-500">固定筛选</div>
        <div className="text-lg font-semibold text-slate-900">先用明确条件收窄范围</div>
        <div className="text-sm text-slate-600">固定筛选负责高频、稳定、可解释的条件，AI 精筛负责进一步理解你的自然语言目标。</div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <FilterSection
          title="分类"
          options={CATEGORY_OPTIONS}
          value={category}
          onChange={onCategoryChange}
        />
        <FilterSection
          title="截止时间"
          options={DEADLINE_OPTIONS}
          value={deadlineLevel}
          onChange={onDeadlineLevelChange}
        />
        <FilterSection
          title="奖金区间"
          options={PRIZE_RANGE_OPTIONS}
          value={prizeRange}
          onChange={onPrizeRangeChange}
        />
        <FilterSection
          title="独立开发者友好"
          options={SOLO_FRIENDLINESS_OPTIONS}
          value={soloFriendliness}
          onChange={onSoloFriendlinessChange}
        />
        <FilterSection
          title="奖励明确性"
          options={REWARD_CLARITY_OPTIONS}
          value={rewardClarity}
          onChange={onRewardClarityChange}
        />
        <FilterSection
          title="投入成本"
          options={EFFORT_LEVEL_OPTIONS}
          value={effortLevel}
          onChange={onEffortLevelChange}
        />
        <FilterSection
          title="来源可信度"
          options={TRUST_LEVEL_OPTIONS}
          value={trustLevel}
          onChange={onTrustLevelChange}
        />
        <FilterSection
          title="线上/远程"
          options={REMOTE_MODE_OPTIONS}
          value={remoteMode}
          onChange={onRemoteModeChange}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <div>
          <div className="mb-2 text-sm font-medium text-gray-600">
            来源 {category && `(${filteredSources.length})`}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              aria-pressed={sourceId === ''}
              onClick={() => onSourceChange('')}
              className={`min-h-[40px] rounded-full px-3.5 py-2 text-sm transition-colors ${
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
                type="button"
                aria-pressed={sourceId === source.id}
                onClick={() => onSourceChange(source.id)}
                className={`min-h-[40px] rounded-full px-3.5 py-2 text-sm transition-colors ${
                  sourceId === source.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {source.name}
              </button>
            ))}
            {hasMoreSources ? (
              <button
                type="button"
                aria-expanded={showAllSources}
                onClick={() => setShowAllSources(current => !current)}
                className="min-h-[40px] rounded-full bg-white px-3.5 py-2 text-sm text-slate-500 transition-colors hover:bg-slate-100"
              >
                {showAllSources ? '收起' : `+${filteredSources.length - 8} 更多`}
              </button>
            ) : null}
          </div>
        </div>

        <FilterSection
          title="处理状态"
          options={TRACKING_OPTIONS}
          value={trackingState}
          onChange={onTrackingStateChange}
        />
      </div>

      {hasFilters ? (
        <button
          type="button"
          onClick={onClear}
          className="text-sm text-slate-500 underline transition hover:text-slate-700"
        >
          清除全部筛选
        </button>
      ) : null}
    </div>
  )
}

export default FilterBar
