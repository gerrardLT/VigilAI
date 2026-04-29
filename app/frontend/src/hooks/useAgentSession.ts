import { useEffect, useRef, useState } from 'react'
import { agentPlatformApi } from '../services/agentPlatformApi'
import type { AgentArtifact, AgentDomainType, AgentSession, AgentSessionSummary, AgentTurn } from '../types'

const MAX_SESSION_HISTORY = 12

function getStorageKey(domainType: AgentDomainType) {
  return `vigilai.agent.lastSession.${domainType}`
}

interface UseAgentSessionResult {
  session: AgentSession | null
  sessions: AgentSessionSummary[]
  turns: AgentTurn[]
  artifacts: AgentArtifact[]
  loading: boolean
  sending: boolean
  error: string | null
  createSession: () => Promise<AgentSession>
  restoreSession: (sessionId: string) => Promise<void>
  sendTurn: (content: string) => Promise<void>
}

export function useAgentSession(domainType: AgentDomainType): UseAgentSessionResult {
  const [session, setSession] = useState<AgentSession | null>(null)
  const [sessions, setSessions] = useState<AgentSessionSummary[]>([])
  const [turns, setTurns] = useState<AgentTurn[]>([])
  const [artifacts, setArtifacts] = useState<AgentArtifact[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestScopeRef = useRef(0)

  useEffect(() => {
    requestScopeRef.current += 1
    setSession(null)
    setSessions([])
    setTurns([])
    setArtifacts([])
    setLoading(false)
    setSending(false)
    setError(null)
  }, [domainType])

  useEffect(() => {
    const requestScope = requestScopeRef.current

    const loadSessions = async () => {
      setLoading(true)
      setError(null)

      try {
        const listedSessions = await agentPlatformApi.listSessions(domainType, MAX_SESSION_HISTORY)
        if (requestScope !== requestScopeRef.current) {
          return
        }

        setSessions(listedSessions)

        const storedSessionId = window.localStorage.getItem(getStorageKey(domainType))
        const preferredSession =
          listedSessions.find(item => item.id === storedSessionId) ??
          listedSessions[0] ??
          null

        if (!preferredSession) {
          return
        }

        const [restoredSession, restoredTurns, restoredArtifacts] = await Promise.all([
          agentPlatformApi.getSession(preferredSession.id),
          agentPlatformApi.listTurns(preferredSession.id),
          agentPlatformApi.listArtifacts(preferredSession.id),
        ])

        if (requestScope !== requestScopeRef.current) {
          return
        }

        window.localStorage.setItem(getStorageKey(domainType), preferredSession.id)
        setSession(restoredSession)
        setTurns(restoredTurns)
        setArtifacts(restoredArtifacts)
      } catch (err) {
        if (requestScope === requestScopeRef.current) {
          const message = err instanceof Error ? err.message : 'Failed to load agent sessions'
          setError(message)
        }
      } finally {
        if (requestScope === requestScopeRef.current) {
          setLoading(false)
        }
      }
    }

    void loadSessions()
  }, [domainType])

  const refreshSessions = async (preferredSessionId?: string) => {
    const listedSessions = await agentPlatformApi.listSessions(domainType, MAX_SESSION_HISTORY)
    setSessions(listedSessions)
    if (preferredSessionId) {
      window.localStorage.setItem(getStorageKey(domainType), preferredSessionId)
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
      })
      if (requestScope === requestScopeRef.current) {
        window.localStorage.setItem(getStorageKey(domainType), createdSession.id)
        setSession(createdSession)
        await refreshSessions(createdSession.id)
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

  const restoreSession = async (sessionId: string) => {
    const requestScope = requestScopeRef.current
    setLoading(true)
    setError(null)

    try {
      const [restoredSession, restoredTurns, restoredArtifacts] = await Promise.all([
        agentPlatformApi.getSession(sessionId),
        agentPlatformApi.listTurns(sessionId),
        agentPlatformApi.listArtifacts(sessionId),
      ])

      if (requestScope === requestScopeRef.current) {
        window.localStorage.setItem(getStorageKey(domainType), restoredSession.id)
        setSession(restoredSession)
        setTurns(restoredTurns)
        setArtifacts(restoredArtifacts)
        await refreshSessions(restoredSession.id)
      }
    } catch (err) {
      if (requestScope === requestScopeRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to restore agent session'
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
        window.localStorage.setItem(getStorageKey(domainType), reply.session.id)
        setSession(reply.session)
        setTurns(reply.turns)
        setArtifacts(reply.artifacts)
        await refreshSessions(reply.session.id)
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
    sessions,
    turns,
    artifacts,
    loading,
    sending,
    error,
    createSession,
    restoreSession,
    sendTurn,
  }
}

export default useAgentSession
