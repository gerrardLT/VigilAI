/**
 * 应用常量定义
 */

// 分页配置
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// 自动刷新间隔（毫秒）
export const STATS_REFRESH_INTERVAL = 60000

// 搜索防抖延迟（毫秒）
export const SEARCH_DEBOUNCE_DELAY = 300

// 排序选项
export const SORT_OPTIONS = [
  { value: 'score', label: '推荐优先级' },
  { value: 'deadline', label: '截止日期' },
  { value: 'trust_level', label: '来源可信度' },
  { value: 'created_at', label: '最新发布' },
  { value: 'prize', label: '奖金金额' },
] as const

// 排序方向
export const SORT_ORDERS = [
  { value: 'desc', label: '降序' },
  { value: 'asc', label: '升序' },
] as const

// 默认排序
export const DEFAULT_SORT_BY = 'score'
export const DEFAULT_SORT_ORDER = 'desc'

// 类别选项
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

// 类别图标映射
export const CATEGORY_ICON_MAP = {
  hackathon: '🏁',
  data_competition: '📊',
  coding_competition: '💻',
  other_competition: '🎯',
  airdrop: '🪂',
  bounty: '💰',
  grant: '🏦',
  dev_event: '📅',
  news: '📰',
} as const

export const DEADLINE_OPTIONS = [
  { value: '', label: '全部时效' },
  { value: 'urgent', label: '紧急截止' },
  { value: 'soon', label: '即将截止' },
  { value: 'upcoming', label: '近期开放' },
  { value: 'later', label: '较晚截止' },
] as const

export const PRIZE_RANGE_OPTIONS = [
  { value: '', label: '全部奖金' },
  { value: 'unknown', label: '奖金未知' },
  { value: '0-500', label: '0 - 500' },
  { value: '500-2000', label: '500 - 2000' },
  { value: '2000-10000', label: '2000 - 10000' },
  { value: '10000+', label: '10000 以上' },
] as const

export const SOLO_FRIENDLINESS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'solo_friendly', label: '适合单人' },
  { value: 'team_required', label: '需要团队' },
  { value: 'unclear', label: '暂不明确' },
] as const

export const REWARD_CLARITY_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'high', label: '奖励明确' },
  { value: 'medium', label: '奖励一般' },
  { value: 'low', label: '奖励不清晰' },
] as const

export const EFFORT_LEVEL_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'low', label: '低投入' },
  { value: 'medium', label: '中投入' },
  { value: 'high', label: '高投入' },
] as const

export const TRUST_LEVEL_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'high', label: '高可信' },
  { value: 'medium', label: '中可信' },
  { value: 'low', label: '低可信' },
] as const

export const REMOTE_MODE_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'remote', label: '线上/远程' },
  { value: 'offline', label: '线下/本地' },
  { value: 'hybrid', label: '混合' },
  { value: 'unknown', label: '未明确' },
] as const

export const TRACKING_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'tracked', label: '已追踪' },
  { value: 'favorited', label: '已收藏' },
  { value: 'untracked', label: '待处理' },
] as const

export const APP_VERSION = '1.0.0'

// 应用名称
export const APP_NAME = 'VigilAI'
export const APP_DESCRIPTION = '开发者搞钱机会监控系统'
