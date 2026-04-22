import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type {
  AgentAnalysisJobCreateRequest,
  AgentAnalysisJobDetail,
  AgentAnalysisJobSummary,
} from '../types'

interface UseAgentAnalysisJobsResult {
  jobs: AgentAnalysisJobSummary[]
  total: number
  activeJob: AgentAnalysisJobDetail | null
  loading: boolean
  refreshing: boolean
  error: string | null
  refetch: () => Promise<void>
  loadJob: (jobId: string) => Promise<AgentAnalysisJobDetail | null>
  createJob: (payload: AgentAnalysisJobCreateRequest) => Promise<AgentAnalysisJobDetail | null>
}

function summarizeJob(job: AgentAnalysisJobDetail): AgentAnalysisJobSummary {
  return {
    id: job.id,
    trigger_type: job.trigger_type,
    scope_type: job.scope_type,
    template_id: job.template_id ?? null,
    route_policy: job.route_policy,
    budget_policy: job.budget_policy,
    status: job.status,
    requested_by: job.requested_by ?? null,
    created_at: job.created_at,
    finished_at: job.finished_at ?? null,
    item_count: job.item_count,
    completed_items: job.items.filter(item => item.status === 'completed').length,
    failed_items: job.items.filter(item => item.status === 'failed').length,
    needs_research_count: job.items.filter(item => item.needs_research).length,
  }
}

export function useAgentAnalysisJobs(): UseAgentAnalysisJobsResult {
  const hasLoadedRef = useRef(false)
  const [jobs, setJobs] = useState<AgentAnalysisJobSummary[]>([])
  const [total, setTotal] = useState(0)
  const [activeJob, setActiveJob] = useState<AgentAnalysisJobDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (hasLoadedRef.current) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)

    try {
      const response = await api.getAgentAnalysisJobs()
      hasLoadedRef.current = true
      setJobs(response.items)
      setTotal(response.total)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load agent analysis jobs'
      setError(message)
      setJobs([])
      setTotal(0)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const loadJob = useCallback(async (jobId: string): Promise<AgentAnalysisJobDetail | null> => {
    setError(null)
    try {
      const detail = await api.getAgentAnalysisJob(jobId)
      setActiveJob(detail)
      return detail
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load agent analysis job'
      setError(message)
      return null
    }
  }, [])

  const createJob = useCallback(
    async (payload: AgentAnalysisJobCreateRequest): Promise<AgentAnalysisJobDetail | null> => {
      setError(null)
      try {
        const created = await api.createAgentAnalysisJob(payload)
        setActiveJob(created)
        setJobs(current => {
          const existed = current.some(job => job.id === created.id)
          if (!existed) {
            setTotal(total => total + 1)
          }
          return [summarizeJob(created), ...current.filter(job => job.id !== created.id)]
        })
        return created
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create agent analysis job'
        setError(message)
        return null
      }
    },
    []
  )

  return {
    jobs,
    total,
    activeJob,
    loading,
    refreshing,
    error,
    refetch: refresh,
    loadJob,
    createJob,
  }
}

export default useAgentAnalysisJobs
