import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type {
  ActivityListItem,
  DigestCandidateRequest,
  DigestDetail,
  DigestGenerateRequest,
  DigestSendRequest,
} from '../types'

interface UseDigestsResult {
  digests: DigestDetail[]
  candidates: ActivityListItem[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  getDigest: (digestId: string) => Promise<DigestDetail | null>
  generateDigest: (payload?: DigestGenerateRequest) => Promise<DigestDetail | null>
  sendDigest: (digestId: string, payload?: DigestSendRequest) => Promise<DigestDetail | null>
  addDigestCandidate: (activityId: string, payload?: DigestCandidateRequest) => Promise<boolean>
  removeDigestCandidate: (activityId: string, payload?: DigestCandidateRequest) => Promise<boolean>
}

export function useDigests(): UseDigestsResult {
  const [digests, setDigests] = useState<DigestDetail[]>([])
  const [candidates, setCandidates] = useState<ActivityListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchCandidates = useCallback(async (digestDate?: string) => {
    const data = await api.getDigestCandidates(digestDate)
    setCandidates(data)
  }, [])

  const fetchDigests = useCallback(async () => {
    const data = await api.getDigests()
    setDigests(data)
  }, [])

  const refreshAll = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      await Promise.all([fetchDigests(), fetchCandidates()])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load digests'
      setError(message)
      setDigests([])
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }, [fetchCandidates, fetchDigests])

  useEffect(() => {
    void refreshAll()
  }, [refreshAll])

  const getDigest = useCallback(async (digestId: string): Promise<DigestDetail | null> => {
    setError(null)
    try {
      return await api.getDigest(digestId)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load digest detail'
      setError(message)
      return null
    }
  }, [])

  const generateDigest = useCallback(
    async (payload: DigestGenerateRequest = {}): Promise<DigestDetail | null> => {
      setError(null)
      try {
        const digest = await api.generateDigest(payload)
        await refreshAll()
        return digest
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to generate digest'
        setError(message)
        return null
      }
    },
    [refreshAll]
  )

  const sendDigest = useCallback(
    async (digestId: string, payload: DigestSendRequest = {}): Promise<DigestDetail | null> => {
      setError(null)
      try {
        const digest = await api.sendDigest(digestId, payload)
        await refreshAll()
        return digest
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to send digest'
        setError(message)
        return null
      }
    },
    [refreshAll]
  )

  const addDigestCandidate = useCallback(
    async (activityId: string, payload: DigestCandidateRequest = {}): Promise<boolean> => {
      setError(null)
      try {
        const result = await api.addDigestCandidate(activityId, payload)
        await fetchCandidates(payload.digest_date)
        return result.success
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to add digest candidate'
        setError(message)
        return false
      }
    },
    [fetchCandidates]
  )

  const removeDigestCandidate = useCallback(
    async (activityId: string, payload: DigestCandidateRequest = {}): Promise<boolean> => {
      setError(null)
      try {
        const result = await api.removeDigestCandidate(activityId, payload)
        await fetchCandidates(payload.digest_date)
        return result.success
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to remove digest candidate'
        setError(message)
        return false
      }
    },
    [fetchCandidates]
  )

  return {
    digests,
    candidates,
    loading,
    error,
    refetch: refreshAll,
    getDigest,
    generateDigest,
    sendDigest,
    addDigestCandidate,
    removeDigestCandidate,
  }
}

export default useDigests
