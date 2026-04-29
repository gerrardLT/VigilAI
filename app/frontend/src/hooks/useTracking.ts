import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { TrackingItem, TrackingState, TrackingStatus, TrackingUpsertRequest } from '../types'
import { notifyTrackingUpdated, TRACKING_UPDATED_EVENT } from '../utils/trackingSync'

interface UseTrackingResult {
  items: TrackingItem[]
  loading: boolean
  error: string | null
  statusFilter: TrackingStatus | undefined
  setStatusFilter: (status: TrackingStatus | undefined) => void
  refetch: () => Promise<void>
  createTracking: (activityId: string, payload: TrackingUpsertRequest) => Promise<TrackingState | null>
  updateTracking: (activityId: string, payload: TrackingUpsertRequest) => Promise<TrackingState | null>
  batchUpdateTracking: (activityIds: string[], payload: TrackingUpsertRequest) => Promise<boolean>
  deleteTracking: (activityId: string) => Promise<boolean>
}

export function useTracking(initialStatus?: TrackingStatus): UseTrackingResult {
  const [items, setItems] = useState<TrackingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<TrackingStatus | undefined>(initialStatus)
  const skipNextSyncRef = useRef(false)

  const fetchTracking = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await api.getTracking(statusFilter)
      setItems(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载跟进列表失败'
      setError(message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchTracking()
  }, [fetchTracking])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined
    }

    const handleTrackingUpdated = () => {
      if (skipNextSyncRef.current) {
        skipNextSyncRef.current = false
        return
      }
      void fetchTracking()
    }

    window.addEventListener(TRACKING_UPDATED_EVENT, handleTrackingUpdated)

    return () => {
      window.removeEventListener(TRACKING_UPDATED_EVENT, handleTrackingUpdated)
    }
  }, [fetchTracking])

  const createTracking = useCallback(
    async (activityId: string, payload: TrackingUpsertRequest): Promise<TrackingState | null> => {
      setError(null)
      try {
        const tracking = await api.createTracking(activityId, payload)
        skipNextSyncRef.current = true
        notifyTrackingUpdated()
        await fetchTracking()
        return tracking
      } catch (err) {
        const message = err instanceof Error ? err.message : '创建跟进记录失败'
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
        skipNextSyncRef.current = true
        notifyTrackingUpdated()
        await fetchTracking()
        return tracking
      } catch (err) {
        const message = err instanceof Error ? err.message : '更新跟进记录失败'
        setError(message)
        return null
      }
    },
    [fetchTracking]
  )

  const batchUpdateTracking = useCallback(
    async (activityIds: string[], payload: TrackingUpsertRequest): Promise<boolean> => {
      if (activityIds.length === 0) {
        return true
      }

      setError(null)
      try {
        await Promise.all(activityIds.map(activityId => api.updateTracking(activityId, payload)))
        skipNextSyncRef.current = true
        notifyTrackingUpdated()
        await fetchTracking()
        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : '批量更新跟进记录失败'
        setError(message)
        return false
      }
    },
    [fetchTracking]
  )

  const deleteTracking = useCallback(
    async (activityId: string): Promise<boolean> => {
      setError(null)
      try {
        const result = await api.deleteTracking(activityId)
        skipNextSyncRef.current = true
        notifyTrackingUpdated()
        await fetchTracking()
        return result.success
      } catch (err) {
        const message = err instanceof Error ? err.message : '删除跟进记录失败'
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
    batchUpdateTracking,
    deleteTracking,
  }
}

export default useTracking
