import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { TrackingItem, TrackingState, TrackingStatus, TrackingUpsertRequest } from '../types'

interface UseTrackingResult {
  items: TrackingItem[]
  loading: boolean
  error: string | null
  statusFilter: TrackingStatus | undefined
  setStatusFilter: (status: TrackingStatus | undefined) => void
  refetch: () => Promise<void>
  createTracking: (activityId: string, payload: TrackingUpsertRequest) => Promise<TrackingState | null>
  updateTracking: (activityId: string, payload: TrackingUpsertRequest) => Promise<TrackingState | null>
  deleteTracking: (activityId: string) => Promise<boolean>
}

export function useTracking(initialStatus?: TrackingStatus): UseTrackingResult {
  const [items, setItems] = useState<TrackingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<TrackingStatus | undefined>(initialStatus)

  const fetchTracking = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await api.getTracking(statusFilter)
      setItems(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load tracking items'
      setError(message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchTracking()
  }, [fetchTracking])

  const createTracking = useCallback(
    async (activityId: string, payload: TrackingUpsertRequest): Promise<TrackingState | null> => {
      setError(null)
      try {
        const tracking = await api.createTracking(activityId, payload)
        await fetchTracking()
        return tracking
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create tracking item'
        setError(message)
        return null
      }
    },
    [fetchTracking]
  )

  const updateTracking = useCallback(
    async (activityId: string, payload: TrackingUpsertRequest): Promise<TrackingState | null> => {
      setError(null)
      try {
        const tracking = await api.updateTracking(activityId, payload)
        await fetchTracking()
        return tracking
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update tracking item'
        setError(message)
        return null
      }
    },
    [fetchTracking]
  )

  const deleteTracking = useCallback(
    async (activityId: string): Promise<boolean> => {
      setError(null)
      try {
        const result = await api.deleteTracking(activityId)
        await fetchTracking()
        return result.success
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete tracking item'
        setError(message)
        return false
      }
    },
    [fetchTracking]
  )

  return {
    items,
    loading,
    error,
    statusFilter,
    setStatusFilter,
    refetch: fetchTracking,
    createTracking,
    updateTracking,
    deleteTracking,
  }
}

export default useTracking
