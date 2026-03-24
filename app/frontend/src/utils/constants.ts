/**
 * 应用常量定义
 */

// 分页配置
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// 自动刷新间隔（毫秒）
export const STATS_REFRESH_INTERVAL = 60000 // 60秒

// 搜索防抖延迟（毫秒）
export const SEARCH_DEBOUNCE_DELAY = 300

// 排序选项
export const SORT_OPTIONS = [
  { value: 'created_at', label: '最新发布' },
  { value: 'deadline', label: '截止日期' },
  { value: 'prize', label: '奖金金额' },
] as const

// 排序方向
export const SORT_ORDERS = [
  { value: 'desc', label: '降序' },
  { value: 'asc', label: '升序' },
] as const

// 默认排序
export const DEFAULT_SORT_BY = 'created_at'
export const DEFAULT_SORT_ORDER = 'desc'

// 类别选项（中文标签）
export const CATEGORY_OPTIONS = [
  { value: '', label: '全部类别' },
  { value: 'hackathon', label: '黑客松' },
  { value: 'data_competition', label: '数据竞赛' },
  { value: 'coding_competition', label: '编程竞赛' },
  { value: 'other_competition', label: '其他竞赛' },
  { value: 'airdrop', label: '空投' },
  { value: 'bounty', label: '赏金' },
  { value: 'grant', label: '资助' },
  { value: 'dev_event', label: '开发者活动' },
  { value: 'news', label: '科技新闻' },
] as const

// 状态颜色映射
export const STATUS_COLOR_MAP = {
  idle: 'bg-gray-400',
  running: 'bg-blue-500 animate-pulse',
  success: 'bg-green-500',
  error: 'bg-red-500',
} as const

// 状态文本映射
export const STATUS_TEXT_MAP = {
  idle: '空闲',
  running: '运行中',
  success: '成功',
  error: '错误',
} as const

// 类别颜色映射
export const CATEGORY_COLOR_MAP = {
  hackathon: 'bg-purple-100 text-purple-800',
  data_competition: 'bg-blue-100 text-blue-800',
  coding_competition: 'bg-indigo-100 text-indigo-800',
  other_competition: 'bg-cyan-100 text-cyan-800',
  airdrop: 'bg-green-100 text-green-800',
  bounty: 'bg-orange-100 text-orange-800',
  grant: 'bg-pink-100 text-pink-800',
  dev_event: 'bg-yellow-100 text-yellow-800',
  news: 'bg-gray-100 text-gray-800',
} as const

// 类别图标映射（可选，使用emoji）
export const CATEGORY_ICON_MAP = {
  hackathon: '🏆',
  data_competition: '📊',
  coding_competition: '💻',
  other_competition: '🎯',
  airdrop: '🪂',
  bounty: '💰',
  grant: '🎁',
  dev_event: '📅',
  news: '📰',
} as const

// 应用版本
export const APP_VERSION = '1.0.0'

// 应用名称
export const APP_NAME = 'VigilAI'
export const APP_DESCRIPTION = '开发者搞钱机会监控系统'
