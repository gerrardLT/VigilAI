import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import fc from 'fast-check'
import ActivityCard from './ActivityCard'
import type { Activity, Category } from '../types'

/**
 * Property 3: 活动卡片字段显示完整性
 * Validates: Requirements 3.3
 * 
 * For any Activity with non-null fields, the ActivityCard component SHALL render 
 * the title, source_name, and category; and SHALL conditionally render prize and deadline when available.
 */

const VALID_CATEGORIES: Category[] = [
  'hackathon',
  'data_competition',
  'coding_competition',
  'other_competition',
  'airdrop',
  'bounty',
  'grant',
  'dev_event',
  'news',
]

// 使用字母数字字符串避免特殊字符导致的测试问题
const alphanumericString = (minLength: number, maxLength: number) =>
  fc.string({ minLength, maxLength }).filter(s => /^[a-zA-Z0-9]+$/.test(s) && s.length >= minLength)

// 生成有效的Activity对象
const activityArbitrary = fc.record({
  id: alphanumericString(1, 20),
  title: alphanumericString(3, 50),
  description: fc.option(alphanumericString(5, 100), { nil: null }),
  source_id: alphanumericString(1, 20),
  source_name: alphanumericString(3, 30),
  url: fc.webUrl(),
  category: fc.constantFrom(...VALID_CATEGORIES),
  tags: fc.array(alphanumericString(2, 10), { maxLength: 3 }),
  prize: fc.option(
    fc.record({
      amount: fc.option(fc.float({ min: 100, max: 1000000 }), { nil: null }),
      currency: fc.constantFrom('USD', 'ETH', 'CNY'),
      description: fc.option(fc.string(), { nil: null }),
    }),
    { nil: null }
  ),
  dates: fc.option(
    fc.record({
      start_date: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
      end_date: fc.option(fc.date().map(d => d.toISOString()), { nil: null }),
      deadline: fc.option(
        fc.date({ min: new Date(), max: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000) })
          .map(d => d.toISOString()),
        { nil: null }
      ),
    }),
    { nil: null }
  ),
  location: fc.option(fc.string(), { nil: null }),
  organizer: fc.option(fc.string(), { nil: null }),
  status: alphanumericString(1, 20),
  created_at: fc.date().map(d => d.toISOString()),
  updated_at: fc.date().map(d => d.toISOString()),
})

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('ActivityCard字段显示完整性', () => {
  afterEach(() => {
    cleanup()
  })

  // Feature: vigilai-frontend, Property 3: 活动卡片字段显示完整性
  it('对于任何Activity，应显示title', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        cleanup()
        const { container } = renderWithRouter(<ActivityCard activity={activity} />)
        expect(container.textContent).toContain(activity.title)
      }),
      { numRuns: 50 }
    )
  })

  it('对于任何Activity，应显示source_name', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        cleanup()
        const { container } = renderWithRouter(<ActivityCard activity={activity} />)
        expect(container.textContent).toContain(activity.source_name)
      }),
      { numRuns: 50 }
    )
  })

  it('对于任何Activity，应显示category标签', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        cleanup()
        const { container } = renderWithRouter(<ActivityCard activity={activity} />)
        // 验证类别标签存在（通过类别颜色类名）
        const categoryBadge = container.querySelector('.rounded-full')
        expect(categoryBadge).toBeInTheDocument()
      }),
      { numRuns: 50 }
    )
  })

  it('当Activity有prize.amount时，应显示奖金信息', () => {
    const activityWithPrize: Activity = {
      id: 'test-1',
      title: 'Test Activity',
      description: null,
      source_id: 'test-source',
      source_name: 'Test Source',
      url: 'https://example.com',
      category: 'hackathon',
      tags: [],
      prize: { amount: 10000, currency: 'USD', description: null },
      dates: null,
      location: null,
      organizer: null,
      status: 'upcoming',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    renderWithRouter(<ActivityCard activity={activityWithPrize} />)
    expect(screen.getByText(/USD/)).toBeInTheDocument()
    expect(screen.getByText(/10,000/)).toBeInTheDocument()
  })

  it('当Activity没有prize时，不应显示奖金信息', () => {
    const activityWithoutPrize: Activity = {
      id: 'test-2',
      title: 'Test Activity No Prize',
      description: null,
      source_id: 'test-source',
      source_name: 'Test Source',
      url: 'https://example.com',
      category: 'hackathon',
      tags: [],
      prize: null,
      dates: null,
      location: null,
      organizer: null,
      status: 'upcoming',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    renderWithRouter(<ActivityCard activity={activityWithoutPrize} />)
    expect(screen.queryByText(/USD/)).not.toBeInTheDocument()
  })

  it('当Activity有deadline时，应显示截止日期信息', () => {
    const futureDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7天后
    const activityWithDeadline: Activity = {
      id: 'test-3',
      title: 'Test Activity With Deadline',
      description: null,
      source_id: 'test-source',
      source_name: 'Test Source',
      url: 'https://example.com',
      category: 'hackathon',
      tags: [],
      prize: null,
      dates: { start_date: null, end_date: null, deadline: futureDate.toISOString() },
      location: null,
      organizer: null,
      status: 'upcoming',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    renderWithRouter(<ActivityCard activity={activityWithDeadline} />)
    // 应显示"X天后截止"
    expect(screen.getByText(/天后截止/)).toBeInTheDocument()
  })

  it('卡片应该是可点击的链接', () => {
    const activity: Activity = {
      id: 'test-link',
      title: 'Clickable Activity',
      description: null,
      source_id: 'test-source',
      source_name: 'Test Source',
      url: 'https://example.com',
      category: 'hackathon',
      tags: [],
      prize: null,
      dates: null,
      location: null,
      organizer: null,
      status: 'upcoming',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    renderWithRouter(<ActivityCard activity={activity} />)
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', `/activities/${activity.id}`)
  })
})
