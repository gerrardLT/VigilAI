import { useState, useEffect } from 'react'
import { useDebounce } from '../hooks/useDebounce'
import { SEARCH_DEBOUNCE_DELAY } from '../utils/constants'

interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

/**
 * 搜索框组件
 * 支持防抖搜索
 */
export function SearchBox({
  value,
  onChange,
  placeholder = '搜索活动...',
}: SearchBoxProps) {
  const [inputValue, setInputValue] = useState(value)
  const debouncedValue = useDebounce(inputValue, SEARCH_DEBOUNCE_DELAY)

  // 同步外部value变化
  useEffect(() => {
    setInputValue(value)
  }, [value])

  // 防抖后触发onChange
  useEffect(() => {
    if (debouncedValue !== value) {
      onChange(debouncedValue)
    }
  }, [debouncedValue, onChange, value])

  const handleClear = () => {
    setInputValue('')
    onChange('')
  }

  return (
    <div className="relative">
      {/* 搜索图标 */}
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <svg
          className="w-5 h-5 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      {/* 输入框 */}
      <input
        type="text"
        value={inputValue}
        onChange={e => setInputValue(e.target.value)}
        placeholder={placeholder}
        className="input pl-10 pr-10"
      />

      {/* 清除按钮 */}
      {inputValue && (
        <button
          onClick={handleClear}
          className="absolute inset-y-0 right-0 pr-3 flex items-center"
        >
          <svg
            className="w-5 h-5 text-gray-400 hover:text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  )
}

export default SearchBox
