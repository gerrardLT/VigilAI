import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDigests } from './useDigests'

const apiMocks = vi.hoisted(() => ({
  getDigests: vi.fn(),
  getDigestCandidates: vi.fn(),
  getDigest: vi.fn(),
  generateDigest: vi.fn(),
  sendDigest: vi.fn(),
  addDigestCandidate: vi.fn(),
  removeDigestCandidate: vi.fn(),
}))

vi.mock('../services/api', () => ({
  api: apiMocks,
}))

const digest = {
  id: 'digest-1',
  digest_date: '2026-03-23',
  title: 'VigilAI Digest 2026-03-23',
  summary: 'Top opportunities',
  content: '- AI Hackathon',
  item_ids: ['activity-1'],
  status: 'draft',
  created_at: '2026-03-23T08:00:00Z',
  updated_at: '2026-03-23T08:05:00Z',
  last_sent_at: null,
  send_channel: null,
}

const candidate = {
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
  updated_at: '2026-03-23T08:05:00Z',
}

describe('useDigests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMocks.getDigestCandidates.mockResolvedValue([candidate])
  })

  it('loads digests on mount', async () => {
    apiMocks.getDigests.mockResolvedValue([digest])

    const { result } = renderHook(() => useDigests())

    await waitFor(() => {
      expect(result.current.digests).toHaveLength(1)
    })

    expect(result.current.candidates).toHaveLength(1)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('refreshes after generating a digest', async () => {
    apiMocks.getDigests.mockResolvedValue([digest])
    apiMocks.generateDigest.mockResolvedValue(digest)

    const { result } = renderHook(() => useDigests())

    await waitFor(() => {
      expect(result.current.digests).toHaveLength(1)
    })

    await act(async () => {
      await result.current.generateDigest({ digest_date: '2026-03-23' })
    })

    expect(apiMocks.generateDigest).toHaveBeenCalledWith({ digest_date: '2026-03-23' })
    expect(apiMocks.getDigests).toHaveBeenCalledTimes(2)
    expect(apiMocks.getDigestCandidates).toHaveBeenCalledTimes(2)
  })

  it('returns digest detail and refreshes after sending', async () => {
    apiMocks.getDigests.mockResolvedValue([digest])
    apiMocks.getDigest.mockResolvedValue(digest)
    apiMocks.sendDigest.mockResolvedValue({ ...digest, status: 'sent', send_channel: 'manual' })

    const { result } = renderHook(() => useDigests())

    await waitFor(() => {
      expect(result.current.digests).toHaveLength(1)
    })

    await expect(result.current.getDigest('digest-1')).resolves.toMatchObject({ id: 'digest-1' })

    await act(async () => {
      await result.current.sendDigest('digest-1', { send_channel: 'manual' })
    })

    expect(apiMocks.sendDigest).toHaveBeenCalledWith('digest-1', { send_channel: 'manual' })
    expect(apiMocks.getDigests).toHaveBeenCalledTimes(2)
    expect(apiMocks.getDigestCandidates).toHaveBeenCalledTimes(2)
  })

  it('refreshes candidates after adding and removing one', async () => {
    apiMocks.getDigests.mockResolvedValue([digest])
    apiMocks.addDigestCandidate.mockResolvedValue({ success: true })
    apiMocks.removeDigestCandidate.mockResolvedValue({ success: true })

    const { result } = renderHook(() => useDigests())

    await waitFor(() => {
      expect(result.current.candidates).toHaveLength(1)
    })

    await act(async () => {
      await result.current.addDigestCandidate('activity-1', { digest_date: '2026-03-23' })
    })

    await act(async () => {
      await result.current.removeDigestCandidate('activity-1', { digest_date: '2026-03-23' })
    })

    expect(apiMocks.addDigestCandidate).toHaveBeenCalledWith('activity-1', { digest_date: '2026-03-23' })
    expect(apiMocks.removeDigestCandidate).toHaveBeenCalledWith('activity-1', {
      digest_date: '2026-03-23',
    })
    expect(apiMocks.getDigestCandidates).toHaveBeenCalledTimes(3)
  })
})
