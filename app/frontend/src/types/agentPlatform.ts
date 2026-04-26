export type AgentDomainType = 'opportunity' | 'product_selection' | (string & {})
export type AgentTurnRole = 'system' | 'user' | 'assistant' | 'tool'

export interface AgentSession {
  id: string
  domain_type: AgentDomainType
  entry_mode: string
  status: string
  title: string | null
  created_at: string
  updated_at: string
  last_turn_at: string | null
}

export interface AgentTurn {
  id: string
  session_id: string
  role: AgentTurnRole
  content: string
  sequence_no: number
  tool_name: string | null
  tool_payload: Record<string, unknown>
  created_at: string
}

export interface AgentArtifact {
  id: string
  session_id: string
  artifact_type: string
  title: string | null
  content: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface AgentToolCall {
  tool_name: string
  status: string
}

export interface AgentSessionCreateRequest {
  domain_type: AgentDomainType
  entry_mode: string
}

export interface AgentTurnCreateRequest {
  content: string
}

export interface AgentTurnReply {
  session: AgentSession
  user_turn: AgentTurn
  assistant_turn: AgentTurn
  artifacts: AgentArtifact[]
  tool_calls: AgentToolCall[]
  turns: AgentTurn[]
}
