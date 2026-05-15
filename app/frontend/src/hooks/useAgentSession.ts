import { useEffect, useRef, useState } from 'react'
import { agentPlatformApi } from '../services/agentPlatformApi'
import type {
  AgentArtifact,
  AgentDomainType,
  AgentMemoryScope,
  AgentPolicyMode,
  AgentSession,
  AgentSessionContext,
  AgentTurn,
} from '../types'

interface AgentSessionConfig {
  policyMode: AgentPolicyMode
  memoryScope: AgentMemoryScope
}

interface UseAgentSessionResult {
  session: AgentSession | null
  turns: AgentTurn[]
  artifacts: AgentArtifact[]
  context: AgentSessionContext | null
  loading: boolean
  sending: boolean
  error: string | null
  createSession: () => Promise<AgentSession>
  refreshContext: () => Promise<AgentSessionContext | null>
  sendTurn: (content: string) => Promise<void>
}

export function useAgentSession(
  domainType: AgentDomainType,
  config: AgentSessionConfig
): UseAgentSessionResult {
  const [session, setSession] = useState<AgentSession | null>(null)
  const [turns, setTurns] = useState<AgentTurn[]>([])
  const [artifacts, setArtifacts] = useState<AgentArtifact[]>([])
  const [context, setContext] = useState<AgentSessionContext | null>(null)
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestScopeRef = useRef(0)

  useEffect(() => {
    requestScopeRef.current += 1
    setSession(null)
    setTurns([])
    setArtifacts([])
    setContext(null)
    setLoading(false)
    setSending(false)
    setError(null)
  }, [domainType, config.memoryScope, config.policyMode])

  const refreshContext = async () => {
    if (!session) {
      return null
    }

    const requestScope = requestScopeRef.current
    setLoading(true)

    try {
      const nextContext = await agentPlatformApi.getSessionContext(session.id)
      if (requestScope === requestScopeRef.current) {
        setContext(nextContext)
        setTurns(nextContext.turns)
      }
      return nextContext
    } catch (err) {
      if (requestScope === requestScopeRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to load agent session context'
        setError(message)
      }
      throw err
    } finally {
      if (requestScope === requestScopeRef.current) {
        setLoading(false)
      }
    }
  }

  const createSession = async () => {
    if (session?.domain_type === domainType) {
      return session
    }

    const requestScope = requestScopeRef.current
    setLoading(true)
    setError(null)

    try {
      const createdSession = await agentPlatformApi.createSession({
        domain_type: domainType,
        entry_mode: 'chat',
        policy_mode: config.policyMode,
        memory_scope: config.memoryScope,
      })
      if (requestScope === requestScopeRef.current) {
        setSession(createdSession)
      }
      return createdSession
    } catch (err) {
      if (requestScope === requestScopeRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to create agent session'
        setError(message)
      }
      throw err
    } finally {
      if (requestScope === requestScopeRef.current) {
        setLoading(false)
      }
    }
  }

  const sendTurn = async (content: string) => {
    const trimmed = content.trim()
    if (!trimmed) {
      return
    }

    const requestScope = requestScopeRef.current
    setSending(true)
    setError(null)

    try {
      const currentSession = session ?? (await createSession())
      const reply = await agentPlatformApi.postTurn(currentSession.id, { content: trimmed })
      const nextContext = await agentPlatformApi.getSessionContext(currentSession.id)
      if (requestScope === requestScopeRef.current) {
        setSession(reply.session)
        setTurns(reply.turns)
        setArtifacts(reply.artifacts)
        setContext(nextContext)
      }
    } catch (err) {
      if (requestScope === requestScopeRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to send agent message'
        setError(message)
      }
      throw err
    } finally {
      if (requestScope === requestScopeRef.current) {
        setSending(false)
      }
    }
  }

  return {
    session,
    turns,
    artifacts,
    context,
    loading,
    sending,
    error,
    createSession,
    refreshContext,
    sendTurn,
  }
}

export default useAgentSession
