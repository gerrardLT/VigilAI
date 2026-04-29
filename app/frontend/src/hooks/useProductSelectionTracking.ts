import { useCallback, useEffect, useState } from 'react'
import { productSelectionApi } from '../services/productSelectionApi'
import type {
  ProductSelectionTrackingFilters,
  ProductSelectionTrackingItem,
  ProductSelectionTrackingState,
  ProductSelectionTrackingStatus,
  ProductSelectionTrackingUpsertRequest,
} from '../types'

interface UseProductSelectionTrackingResult {
  items: ProductSelectionTrackingItem[]
  loading: boolean
  error: string | null
  filters: ProductSelectionTrackingFilters
  setFilters: (next: Partial<ProductSelectionTrackingFilters>) => void
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
  initialStatus?: ProductSelectionTrackingStatus,
  initialFilters: Partial<ProductSelectionTrackingFilters> = {}
): UseProductSelectionTrackingResult {
  const [items, setItems] = useState<ProductSelectionTrackingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<ProductSelectionTrackingFilters>({
    status: initialStatus,
    source_mode: '',
    fallback_reason: '',
    ...initialFilters,
  })

  const fetchTracking = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await productSelectionApi.getTracking(filters)
      setItems(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载选品跟进失败'
      setError(message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [filters])

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
        const message = err instanceof Error ? err.message : '创建选品跟进失败'
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
        const message = err instanceof Error ? err.message : '更新选品跟进失败'
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
        const message = err instanceof Error ? err.message : '删除选品跟进失败'
        setError(message)
        return false
      }
    },
    [fetchTracking]
  )

  const setFilters = useCallback((next: Partial<ProductSelectionTrackingFilters>) => {
    setFiltersState(current => ({ ...current, ...next }))
  }, [])

  return {
    items,
    loading,
    error,
    filters,
    setFilters,
    refetch: fetchTracking,
    createTracking,
    updateTracking,
    deleteTracking,
  }
}

export default useProductSelectionTracking
