/**
 * 日期格式化工具
 * 将ISO 8601日期字符串转换为用户友好格式
 */

/**
 * 格式化日期为 YYYY-MM-DD HH:mm 格式
 * @param dateString ISO 8601日期字符串
 * @returns 格式化后的日期字符串，如果输入无效则返回空字符串
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) {
    return ''
  }

  try {
    const date = new Date(dateString)
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return ''
    }

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch {
    return ''
  }
}

/**
 * 格式化日期时间为 YYYY-MM-DD HH:mm 格式
 * @param dateString ISO 8601日期字符串
 * @returns 格式化后的日期时间字符串
 */
export function formatDateTime(dateString: string | null | undefined): string {
  return formatDate(dateString)
}

/**
 * 格式化日期为 YYYY-MM-DD 格式（仅日期）
 * @param dateString ISO 8601日期字符串
 * @returns 格式化后的日期字符串
 */
export function formatDateOnly(dateString: string | null | undefined): string {
  if (!dateString) {
    return ''
  }

  try {
    const date = new Date(dateString)
    
    if (isNaN(date.getTime())) {
      return ''
    }

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  } catch {
    return ''
  }
}

/**
 * 格式化相对时间（如"3小时前"）
 * @param dateString ISO 8601日期字符串
 * @returns 相对时间字符串
 */
export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) {
    return ''
  }

  try {
    const date = new Date(dateString)
    
    if (isNaN(date.getTime())) {
      return ''
    }

    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffSeconds < 60) {
      return '刚刚'
    } else if (diffMinutes < 60) {
      return `${diffMinutes}分钟前`
    } else if (diffHours < 24) {
      return `${diffHours}小时前`
    } else if (diffDays < 30) {
      return `${diffDays}天前`
    } else {
      return formatDateOnly(dateString)
    }
  } catch {
    return ''
  }
}

/**
 * 检查日期是否已过期
 * @param dateString ISO 8601日期字符串
 * @returns 是否已过期
 */
export function isExpired(dateString: string | null | undefined): boolean {
  if (!dateString) {
    return false
  }

  try {
    const date = new Date(dateString)
    
    if (isNaN(date.getTime())) {
      return false
    }

    return date.getTime() < Date.now()
  } catch {
    return false
  }
}

/**
 * 计算距离截止日期的天数
 * @param dateString ISO 8601日期字符串
 * @returns 天数（负数表示已过期）
 */
export function daysUntil(dateString: string | null | undefined): number | null {
  if (!dateString) {
    return null
  }

  try {
    const date = new Date(dateString)
    
    if (isNaN(date.getTime())) {
      return null
    }

    const now = new Date()
    const diffMs = date.getTime() - now.getTime()
    return Math.ceil(diffMs / (1000 * 60 * 60 * 24))
  } catch {
    return null
  }
}
