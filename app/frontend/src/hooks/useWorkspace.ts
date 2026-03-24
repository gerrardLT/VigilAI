import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { WorkspaceResponse } from '../types'

interface UseWorkspaceResult {
  workspace: WorkspaceResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export function useWorkspace(): UseWorkspaceResult {
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchWorkspace = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await api.getWorkspace()
      setWorkspace(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load workspace'
      setError(message)
      setWorkspace(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchWorkspace()
  }, [fetchWorkspace])

  return {
    workspace,
    loading,
    error,
    refetch: fetchWorkspace,
  }
}

export default useWorkspace
