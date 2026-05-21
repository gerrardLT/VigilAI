import { useState, useCallback, useRef } from 'react'

interface StreamEvent {
  type: 'start' | 'tool_start' | 'tool_done' | 'text' | 'done' | 'error'
  content?: string
  tool?: string
  session_id?: string
  message?: string
}

interface StreamState {
  streaming: boolean
  fullText: string
  toolStatus: Record<string, 'running' | 'done'>
  error: string | null
  sessionId: string | null
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useStreamingTurn() {
  const [state, setState] = useState<StreamState>({
    streaming: false,
    fullText: '',
    toolStatus: {},
    error: null,
    sessionId: null,
  })
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (sessionId: string, content: string) => {
    abortRef.current = new AbortController()
    setState({ streaming: true, fullText: '', toolStatus: {}, error: null, sessionId })

    try {
      const response = await fetch(
        `${API_BASE}/api/agent/sessions/${sessionId}/turns/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
          signal: abortRef.current.signal,
        }
      )

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event: StreamEvent = JSON.parse(line.slice(6))
            handleEvent(event, setState)
          } catch {
            /* skip malformed events */
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setState(s => ({ ...s, error: err instanceof Error ? err.message : 'Unknown error', streaming: false }))
      }
    } finally {
      setState(s => ({ ...s, streaming: false }))
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    setState(s => ({ ...s, streaming: false }))
  }, [])

  return { ...state, sendMessage, cancel }
}

function handleEvent(
  event: StreamEvent,
  setState: React.Dispatch<React.SetStateAction<StreamState>>
) {
  switch (event.type) {
    case 'tool_start':
      setState(s => ({
        ...s,
        toolStatus: { ...s.toolStatus, [event.tool!]: 'running' },
      }))
      break
    case 'tool_done':
      setState(s => ({
        ...s,
        toolStatus: { ...s.toolStatus, [event.tool!]: 'done' },
      }))
      break
    case 'text':
      setState(s => ({
        ...s,
        fullText: s.fullText + (event.content || ''),
      }))
      break
    case 'done':
      setState(s => ({
        ...s,
        sessionId: event.session_id || s.sessionId,
      }))
      break
    case 'error':
      setState(s => ({
        ...s,
        error: event.message || 'Stream error',
      }))
      break
  }
}

export default useStreamingTurn
