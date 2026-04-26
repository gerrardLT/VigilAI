import { useEffect, useRef, useState } from 'react'
import { agentPlatformApi } from '../services/agentPlatformApi'
import type { AgentArtifact, AgentDomainType, AgentSession, AgentTurn } from '../types'

interface UseAgentSessionResult {
  session: AgentSession | null
  turns: AgentTurn[]
  artifacts: AgentArtifact[]
  loading: boolean
  sending: boolean
  error: string | null
  createSession: () => Promise<AgentSession>
  sendTurn: (content: string) => Promise<void>
}

export function useAgentSession(domainType: AgentDomainType): UseAgentSessionResult {
  const [session, setSession] = useState<AgentSession | null>(null)
  const [turns, setTurns] = useState<AgentTurn[]>([])
  const [artifacts, setArtifacts] = useState<AgentArtifact[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestScopeRef = useRef(0)

  useEffect(() => {
    requestScopeRef.current += 1
    setSession(null)
    setTurns([])
    setArtifacts([])
    setLoading(false)
    setSending(false)
    setError(null)
  }, [domainType])

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
      if (requestScope === requestScopeRef.current) {
        setSession(reply.session)
        setTurns(reply.turns)
        setArtifacts(reply.artifacts)
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
    loading,
    sending,
    error,
    createSession,
    sendTurn,
  }
}

export default useAgentSession
