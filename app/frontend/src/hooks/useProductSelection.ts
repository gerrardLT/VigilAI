import { useCallback, useEffect, useState } from 'react'
import { productSelectionApi } from '../services/productSelectionApi'
import type {
  ProductSelectionOpportunity,
  ProductSelectionOpportunityFilters,
  ProductSelectionResearchJobCreateRequest,
  ProductSelectionResearchJobResponse,
} from '../types'

const DEFAULT_FILTERS: ProductSelectionOpportunityFilters = {
  platform: '',
  search: '',
  risk_tag: '',
  sort_by: 'opportunity_score',
  sort_order: 'desc',
  page: 1,
  page_size: 20,
}

interface UseProductSelectionResult {
  opportunities: ProductSelectionOpportunity[]
  total: number
  page: number
  totalPages: number
  filters: ProductSelectionOpportunityFilters
  loading: boolean
  error: string | null
  latestJob: ProductSelectionResearchJobResponse | null
  setFilters: (nextFilters: Partial<ProductSelectionOpportunityFilters>) => void
  setPage: (page: number) => void
  refetch: () => Promise<void>
  createResearchJob: (
    payload: ProductSelectionResearchJobCreateRequest
  ) => Promise<ProductSelectionResearchJobResponse | null>
}

export function useProductSelection(
  initialFilters: ProductSelectionOpportunityFilters = {}
): UseProductSelectionResult {
  const [opportunities, setOpportunities] = useState<ProductSelectionOpportunity[]>([])
  const [total, setTotal] = useState(0)
  const [filters, setFiltersState] = useState<ProductSelectionOpportunityFilters>({
    ...DEFAULT_FILTERS,
    ...initialFilters,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [latestJob, setLatestJob] = useState<ProductSelectionResearchJobResponse | null>(null)

  const fetchOpportunities = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await productSelectionApi.getOpportunities(filters)
      setOpportunities(response.items)
      setTotal(response.total)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load selection opportunities'
      setError(message)
      setOpportunities([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchOpportunities()
  }, [fetchOpportunities])

  const setFilters = useCallback((nextFilters: Partial<ProductSelectionOpportunityFilters>) => {
    setFiltersState(current => ({
      ...current,
      ...nextFilters,
      page: nextFilters.page ?? 1,
    }))
  }, [])

  const setPage = useCallback((page: number) => {
    setFiltersState(current => ({ ...current, page }))
  }, [])

  const createResearchJob = useCallback(
    async (
      payload: ProductSelectionResearchJobCreateRequest
    ): Promise<ProductSelectionResearchJobResponse | null> => {
      setLoading(true)
      setError(null)

      try {
        const job = await productSelectionApi.createResearchJob(payload)
        setLatestJob(job)
        setFiltersState(current => ({
          ...current,
          query_id: job.job.id,
          page: 1,
        }))
        setOpportunities(job.items)
        setTotal(job.total)
        return job
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create research job'
        setError(message)
        return null
      } finally {
        setLoading(false)
      }
    },
    []
  )

  return {
    opportunities,
    total,
    page: filters.page ?? 1,
    totalPages: Math.max(1, Math.ceil(total / (filters.page_size || 20))),
    filters,
    loading,
    error,
    latestJob,
    setFilters,
    setPage,
    refetch: fetchOpportunities,
    createResearchJob,
  }
}

export default useProductSelection
