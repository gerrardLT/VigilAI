import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DigestsPage from './DigestsPage'

const generateDigest = vi.fn()
const getDigest = vi.fn()
const sendDigest = vi.fn()
const removeDigestCandidate = vi.fn()
const writeText = vi.fn()

vi.mock('../hooks/useDigests', () => ({
  useDigests: () => ({
    digests: [
      {
        id: 'digest-1',
        digest_date: '2026-03-23',
        title: 'Today Digest',
        summary: 'Top picks',
        content: '- AI Hackathon',
        item_ids: ['activity-1'],
        status: 'draft',
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:05:00Z',
        last_sent_at: null,
        send_channel: null,
      },
    ],
    candidates: [
      {
        id: 'activity-1',
        title: 'AI Hackathon',
        description: 'Build an AI app.',
        source_id: 'devpost',
        source_name: 'Devpost',
        url: 'https://example.com/ai-hackathon',
        category: 'hackathon',
        tags: ['ai'],
        prize: null,
        dates: null,
        location: null,
        organizer: null,
        image_url: null,
        summary: 'Recommended for AI builders',
        score: 8.9,
        score_reason: 'Urgent and high trust',
        deadline_level: 'urgent',
        trust_level: 'high',
        updated_fields: [],
        is_tracking: true,
        is_favorited: false,
        is_digest_candidate: true,
        status: 'upcoming',
        created_at: '2026-03-23T08:00:00Z',
        updated_at: '2026-03-23T08:00:00Z',
      },
    ],
    loading: false,
    error: null,
    refetch: vi.fn(),
    getDigest,
    generateDigest,
    sendDigest,
    removeDigestCandidate,
  }),
}))

beforeEach(() => {
  generateDigest.mockResolvedValue(null)
  getDigest.mockResolvedValue(null)
  sendDigest.mockResolvedValue(null)
  removeDigestCandidate.mockResolvedValue({ success: true })
  writeText.mockResolvedValue(undefined)
  Object.defineProperty(window.navigator, 'clipboard', {
    configurable: true,
    value: {
      writeText,
    },
  })
})

describe('DigestsPage', () => {
  it('renders digest list and supports generating a digest', () => {
    render(
      <MemoryRouter>
        <DigestsPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('digests-page')).toBeInTheDocument()
    expect(screen.getAllByText('今日日报').length).toBeGreaterThan(0)
    expect(screen.getByText('1 分钟简报')).toBeInTheDocument()
    expect(screen.queryByText('1 Minute Brief')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('generate-digest-button'))
    fireEvent.click(screen.getByTestId('digest-row-digest-1'))

    expect(generateDigest).toHaveBeenCalled()
    expect(getDigest).toHaveBeenCalledWith('digest-1')
  })

  it('copies the digest summary to the clipboard', async () => {
    render(
      <MemoryRouter>
        <DigestsPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('digest-copy-button'))

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expect.stringContaining('今日日报'))
    })
  })

  it('shows digest candidates and supports removing one', async () => {
    render(
      <MemoryRouter>
        <DigestsPage />
      </MemoryRouter>
    )

    const candidateCard = screen.getByTestId('digest-candidate-activity-1')

    expect(candidateCard).toBeInTheDocument()
    expect(within(candidateCard).getByText('AI 黑客松')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('digest-candidate-remove-activity-1'))

    await waitFor(() => {
      expect(removeDigestCandidate).toHaveBeenCalledWith('activity-1', { digest_date: '2026-03-23' })
    })
  })
})
