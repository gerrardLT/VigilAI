// 活动类别枚举
export type Category = 'hackathon' | 'data_competition' | 'coding_competition' | 'other_competition' | 'airdrop' | 'bounty' | 'grant' | 'dev_event' | 'news';

// 优先级枚举
export type Priority = 'high' | 'medium' | 'low';

// 信息源类型枚举
export type SourceType = 'rss' | 'web' | 'api';

// 信息源状态枚举
export type SourceStatus = 'idle' | 'running' | 'success' | 'error';

// 奖金信息
export interface Prize {
  amount: number | null;
  currency: string;
  description: string | null;
}

// 活动时间信息
export interface ActivityDates {
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
}

// 活动实体 - 与后端Activity模型完全匹配
export interface Activity {
  id: string;
  title: string;
  description: string | null;
  source_id: string;
  source_name: string;
  url: string;
  category: Category;
  tags: string[];
  prize: Prize | null;
  dates: ActivityDates | null;
  location: string | null;
  organizer: string | null;
  image_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

// 信息源实体 - 与后端Source模型完全匹配
export interface Source {
  id: string;
  name: string;
  type: SourceType;
  category: Category;
  status: SourceStatus;
  last_run: string | null;
  last_success: string | null;
  activity_count: number;
  error_message: string | null;
}

// 活动列表响应 - 与后端ActivityListResponse匹配
export interface ActivityListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Activity[];
}

// 统计信息响应 - 与后端StatsResponse匹配
export interface StatsResponse {
  total_activities: number;
  total_sources: number;
  activities_by_category: Record<string, number>;
  activities_by_source: Record<string, number>;
  last_update: string | null;
}

// 刷新响应 - 与后端RefreshResponse匹配
export interface RefreshResponse {
  success: boolean;
  message: string;
}

// 类别选项
export interface CategoryOption {
  value: string;
  label: string;
}

// 筛选参数
export interface ActivityFilters {
  category?: string;
  source_id?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

// 类别标签映射
export const CATEGORY_LABELS: Record<Category, string> = {
  hackathon: '黑客松',
  data_competition: '数据竞赛',
  coding_competition: '编程竞赛',
  other_competition: '其他竞赛',
  airdrop: '空投',
  bounty: '赏金',
  grant: '资助',
  dev_event: '开发者活动',
  news: '科技新闻',
};

// 状态颜色映射
export const STATUS_COLORS: Record<SourceStatus, string> = {
  idle: 'bg-gray-400',
  running: 'bg-blue-500',
  success: 'bg-green-500',
  error: 'bg-red-500',
};

// 状态标签映射
export const STATUS_LABELS: Record<SourceStatus, string> = {
  idle: '空闲',
  running: '运行中',
  success: '成功',
  error: '错误',
};
