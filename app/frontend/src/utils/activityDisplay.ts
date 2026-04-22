import type { ActivityListItem } from '../types'
import { localizeAnalysisText } from './analysisI18n'

type ActivityDisplayFields = Pick<ActivityListItem, 'title' | 'summary' | 'description' | 'full_content'>

const NOISE_LINE_PATTERNS = [
  /^(?:关于我们|联系我们|原文链接|更多|下载APP|回到顶部)$/i,
  /^(?:today|yesterday)\s+\d{1,2}:\d{2}$/i,
  /^(?:今天|昨日|昨天)\s+\d{1,2}:\d{2}$/i,
  /^(?:follow us|share this|social media|copyright)$/i,
]

const LISTING_BOUNDARY_PATTERNS = [
  /(?:今天|昨日|昨天)\s+\d{1,2}:\d{2}/i,
  /\b\d+\(current\)\b/i,
  /\bHomepage recommendation\b/i,
  /\b下载APP\b/i,
  /\b回到顶部\b/i,
  /###\s+/,
]

const TITLE_BOUNDARY_PATTERNS = [
  /\s+\d{4}[-/]\d{1,2}[-/]\d{1,2}\b/,
  /\s+\d{1,2}:\d{2}\b/,
  /\s+\d+\(current\)\b/i,
  /\s+(?:线上活动|线下活动|报名中|已截止)\b/,
  /\s+ps:\/\//i,
  /\s+»\s+/,
]

const METADATA_STRONG_PATTERNS = [/\d{4}[-/]\d{1,2}[-/]\d{1,2}/, /\d{1,2}:\d{2}/, /\b\d+\(current\)\b/i, /\bps:\/\//i]

const METADATA_KEYWORD_RE = /(?:线上活动|线下活动|报名中|已截止|周[一二三四五六日天])/g
const NAVIGATION_CLOUD_RE =
  /(?:问答|博客|资讯|标签|用户|活动|热门标签|开发者社区|极客观点|项目管理|javascript|python|react|php|laravel|go|mysql|linux|ios|java|android|css|typescript)/gi

export function normalizeActivityDisplayText(text: string) {
  return text
    .replace(/\\\\/g, ' ')
    .replace(/\)\]\(|\]\(|\)\[|\]\[/g, ' ')
    .replace(/!\[[^\]]*\]\(([^)]+)\)/g, ' ')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/https?:\/\/\S+/gi, ' ')
    .replace(/\b(?:[\w-]+\.)+[a-z]{2,}\S*/gi, ' ')
    .replace(/%[0-9A-Fa-f]{2}/g, ' ')
    .replace(/\b[a-z]+=(?:[^&\s]+&){1,}[^&\s]+/gi, ' ')
    .replace(/\bresize=\d+x\d+\b/gi, ' ')
    .replace(/\bps:\/\//gi, ' ')
    .replace(/…M/g, ' ')
    .replace(/(^|\s)(?:关于我们|联系我们|原文链接|更多|下载APP|回到顶部|Homepage recommendation)(?=\s|$)/gi, ' ')
    .replace(/[`>#*_]+/g, ' ')
    .replace(/[|·]/g, ' ')
    .replace(/[\[\]]+/g, ' ')
    .replace(/(?:(?<=\s)|^)[()]+(?=\s|$)/g, ' ')
    .replace(/\(\s*\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function trimListingNoise(text: string, minOffset = 40) {
  let cutoff = text.length

  LISTING_BOUNDARY_PATTERNS.forEach(pattern => {
    const match = pattern.exec(text)
    if (match && match.index >= minOffset) {
      cutoff = Math.min(cutoff, match.index)
    }
  })

  return text.slice(0, cutoff).trim()
}

function dedupeRepeatedLead(text: string) {
  const collapsed = text.replace(/\s+/g, ' ').trim()
  const maxPrefixLength = Math.min(Math.floor(collapsed.length / 2), 40)

  for (let length = maxPrefixLength; length >= 6; length -= 1) {
    const prefix = collapsed.slice(0, length).trim()
    if (prefix.length < 6) {
      continue
    }

    const remainder = collapsed.slice(length).trim()
    if (remainder.startsWith(prefix)) {
      return `${prefix} ${remainder.slice(prefix.length).trim()}`.trim()
    }
  }

  return collapsed
}

function firstMeaningfulSentence(text: string) {
  const fragments = text.match(/[^。！？!?]+[。！？!?]?/g)
  if (!fragments || fragments.length === 0) {
    return text.trim()
  }

  return fragments[0].trim()
}

function finalizeText(text: string, maxLength: number) {
  const cleaned = text.replace(/\s{2,}/g, ' ').trim()
  if (cleaned.length <= maxLength) {
    return cleaned
  }

  return `${cleaned.slice(0, maxLength).trimEnd()}…`
}

function stripStandaloneTokens(text: string) {
  return text
    .replace(/(?:^|\s)(?:关于我们|联系我们|原文链接|更多|下载APP|回到顶部|Homepage recommendation)(?:\s|$)/gi, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function looksLikeMetadataLine(text: string) {
  const strongHits = METADATA_STRONG_PATTERNS.filter(pattern => pattern.test(text)).length
  const keywordHits = text.match(METADATA_KEYWORD_RE)?.length ?? 0

  return strongHits >= 2 || (strongHits >= 1 && keywordHits >= 2)
}

function looksLikeNavigationCloud(text: string) {
  return (text.match(NAVIGATION_CLOUD_RE)?.length ?? 0) >= 4
}

function buildDisplayTitleCandidate(activity: ActivityDisplayFields) {
  const candidates = [activity.title, activity.summary, activity.description, activity.full_content]

  for (const candidate of candidates) {
    if (!candidate) {
      continue
    }

    let cleaned = normalizeActivityDisplayText(candidate)
    cleaned = trimListingNoise(cleaned, 24)
    cleaned = dedupeRepeatedLead(cleaned)
    cleaned = stripStandaloneTokens(cleaned)

    for (const pattern of TITLE_BOUNDARY_PATTERNS) {
      const match = pattern.exec(cleaned)
      if (match && match.index >= 8) {
        cleaned = cleaned.slice(0, match.index).trim()
        break
      }
    }

    cleaned = firstMeaningfulSentence(cleaned)
    cleaned = finalizeText(cleaned, 80)

    if (cleaned.length >= 3 && !NOISE_LINE_PATTERNS.some(pattern => pattern.test(cleaned))) {
      return cleaned
    }
  }

  return stripStandaloneTokens(normalizeActivityDisplayText(activity.title))
}

export function buildActivityDisplayTitle(activity: ActivityDisplayFields) {
  return localizeAnalysisText(buildDisplayTitleCandidate(activity))
}

export function buildActivityDisplayExcerpt(activity: ActivityDisplayFields, maxLength = 140) {
  const displayTitle = buildDisplayTitleCandidate(activity)
  const candidates = [activity.summary, activity.description, activity.full_content, activity.title]

  for (const candidate of candidates) {
    if (!candidate) {
      continue
    }

    let cleaned = normalizeActivityDisplayText(candidate)
    cleaned = trimListingNoise(cleaned)
    cleaned = dedupeRepeatedLead(cleaned)
    cleaned = stripStandaloneTokens(cleaned)

    if (cleaned.startsWith(displayTitle)) {
      cleaned = cleaned.slice(displayTitle.length).trim()
    }

    cleaned = stripStandaloneTokens(
      firstMeaningfulSentence(cleaned)
        .replace(/^[-•]\s*/, '')
        .replace(/^\(\d+\/\d+\/\d+\)\s*[-»]*\s*/, '')
        .trim()
    )
    if (displayTitle && cleaned.includes(displayTitle)) {
      cleaned = cleaned.replace(displayTitle, '').trim()
    }
    cleaned = finalizeText(cleaned, maxLength)

    if (
      cleaned.length >= 6 &&
      !looksLikeMetadataLine(cleaned) &&
      !looksLikeNavigationCloud(cleaned) &&
      !NOISE_LINE_PATTERNS.some(pattern => pattern.test(cleaned))
    ) {
      return localizeAnalysisText(cleaned)
    }
  }

  return ''
}
