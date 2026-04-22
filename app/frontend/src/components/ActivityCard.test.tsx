import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import fc from 'fast-check'
import ActivityCard from './ActivityCard'
import type { Activity, Category } from '../types'

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

const alphanumericString = (minLength: number, maxLength: number) =>
  fc.string({ minLength, maxLength }).filter(s => /^[a-zA-Z0-9]+$/.test(s) && s.length >= minLength)

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
        fc.date({ min: new Date(), max: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000) }).map(d =>
          d.toISOString()
        ),
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

describe('ActivityCard', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders title for any valid activity', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        cleanup()
        const { container } = renderWithRouter(<ActivityCard activity={activity} />)
        expect(container.textContent).toContain(activity.title)
      }),
      { numRuns: 50 }
    )
  })

  it('renders source name for any valid activity', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        cleanup()
        const { container } = renderWithRouter(<ActivityCard activity={activity} />)
        expect(container.textContent).toContain(activity.source_name)
      }),
      { numRuns: 50 }
    )
  })

  it('renders a category badge for any valid activity', () => {
    fc.assert(
      fc.property(activityArbitrary, (activity: Activity) => {
        cleanup()
        const { container } = renderWithRouter(<ActivityCard activity={activity} />)
        const categoryBadge = container.querySelector('.rounded-full')
        expect(categoryBadge).toBeInTheDocument()
      }),
      { numRuns: 50 }
    )
  })

  it('renders prize info when prize amount is present', () => {
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

  it('does not render prize info when no prize exists', () => {
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

  it('renders deadline info when a deadline exists', () => {
    const futureDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
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
    expect(screen.getByText(/天后截止/)).toBeInTheDocument()
  })

  it('links to the activity detail page', () => {
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

  it('renders analysis verdict and folded reasons when AI analysis is available', () => {
    const activity: Activity = {
      id: 'test-analysis',
      title: 'AI Ranked Opportunity',
      description: 'Fast-turnaround challenge.',
      source_id: 'test-source',
      source_name: 'Test Source',
      url: 'https://example.com',
      category: 'hackathon',
      tags: [],
      prize: null,
      dates: null,
      location: null,
      organizer: null,
      analysis_fields: {
        roi_level: 'high',
      },
      analysis_status: 'passed',
      analysis_failed_layer: null,
      analysis_summary_reasons: ['Reward clarity passed', 'ROI score passed'],
      status: 'upcoming',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    renderWithRouter(<ActivityCard activity={activity} />)

    expect(screen.getByTestId('activity-card-analysis-status')).toHaveTextContent('通过')
    expect(screen.getByText('Reward clarity passed')).toBeInTheDocument()
    expect(screen.getByText('ROI score passed')).toBeInTheDocument()
  })
})
