import { useCallback, useEffect, useState } from 'react'
import { productSelectionApi } from '../services/productSelectionApi'
import type {
  ProductSelectionTrackingItem,
  ProductSelectionTrackingState,
  ProductSelectionTrackingStatus,
  ProductSelectionTrackingUpsertRequest,
} from '../types'

interface UseProductSelectionTrackingResult {
  items: ProductSelectionTrackingItem[]
  loading: boolean
  error: string | null
  statusFilter: ProductSelectionTrackingStatus | undefined
  setStatusFilter: (status: ProductSelectionTrackingStatus | undefined) => void
  refetch: () => Promise<void>
  createTracking: (
    opportunityId: string,
    payload: ProductSelectionTrackingUpsertRequest
  ) => Promise<ProductSelectionTrackingState | null>
  updateTracking: (
    opportunityId: string,
    payload: ProductSelectionTrackingUpsertRequest
  ) => Promise<ProductSelectionTrackingState | null>
  deleteTracking: (opportunityId: string) => Promise<boolean>
}

export function useProductSelectionTracking(
  initialStatus?: ProductSelectionTrackingStatus
): UseProductSelectionTrackingResult {
  const [items, setItems] = useState<ProductSelectionTrackingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ProductSelectionTrackingStatus | undefined>(
    initialStatus
  )

  const fetchTracking = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await productSelectionApi.getTracking(statusFilter)
      setItems(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load selection tracking'
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
    async (
      opportunityId: string,
      payload: ProductSelectionTrackingUpsertRequest
    ): Promise<ProductSelectionTrackingState | null> => {
      setError(null)
      try {
        const tracking = await productSelectionApi.createTracking(opportunityId, payload)
        await fetchTracking()
        return tracking
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create selection tracking'
        setError(message)
        return null
      }
    },
    [fetchTracking]
  )

  const updateTracking = useCallback(
    async (
      opportunityId: string,
      payload: ProductSelectionTrackingUpsertRequest
    ): Promise<ProductSelectionTrackingState | null> => {
      setError(null)
      try {
        const tracking = await productSelectionApi.updateTracking(opportunityId, payload)
        await fetchTracking()
        return tracking
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update selection tracking'
        setError(message)
        return null
      }
    },
    [fetchTracking]
  )

  const deleteTracking = useCallback(
    async (opportunityId: string): Promise<boolean> => {
      setError(null)
      try {
        const result = await productSelectionApi.deleteTracking(opportunityId)
        await fetchTracking()
        return result.success
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete selection tracking'
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

export default useProductSelectionTracking
