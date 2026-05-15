export type AgentDomainType = 'opportunity' | 'product_selection' | (string & {})
export type AgentTurnRole = 'system' | 'user' | 'assistant' | 'tool'
export type AgentPolicyMode = 'standard' | 'strict'
export type AgentMemoryScope = 'session_only' | 'domain' | 'global'

export interface AgentSession {
  id: string
  domain_type: AgentDomainType
  entry_mode: string
  status: string
  policy_mode: AgentPolicyMode
  memory_scope: AgentMemoryScope
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

export interface AgentExecutionPlanStep {
  tool_name: string
  intent: string
  rationale: string
  priority: number
  stage: string
  access_mode: string
  policy_decision: string
  metadata: Record<string, unknown>
}

export interface AgentExecutionPlan {
  id: string
  session_id: string
  source_turn_id: string | null
  mode: string
  summary: string
  requested_steps: AgentExecutionPlanStep[]
  runnable_tools: string[]
  blocked_tools: string[]
  risk_flags: string[]
  reasoning: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface AgentSessionState {
  session_id: string
  goal: string | null
  constraints: string[]
  preferences: string[]
  working_memory: string[]
  current_focus: string | null
  next_question: string | null
  next_action: string | null
  summary: string | null
  last_tool_names: string[]
  state_payload: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AgentInsight {
  id: string
  session_id: string
  source_turn_id: string | null
  insight_type: string
  content: string
  importance: number
  payload: Record<string, unknown>
  created_at: string
}

export interface AgentThinkingStep {
  id: string
  session_id: string
  source_turn_id: string | null
  phase: string
  summary: string
  tool_name: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface AgentMemory {
  id: string
  session_id: string
  source_turn_id: string | null
  memory_type: string
  content: string
  importance: number
  payload: Record<string, unknown>
  created_at: string
}

export interface AgentReflection {
  id: string
  session_id: string
  source_turn_id: string | null
  reflection_type: string
  summary: string
  action_item: string | null
  score: number
  payload: Record<string, unknown>
  created_at: string
}

export interface AgentSessionCreateRequest {
  domain_type: AgentDomainType
  entry_mode: string
  policy_mode: AgentPolicyMode
  memory_scope: AgentMemoryScope
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
  execution_plan: AgentExecutionPlan
  recalled_memories: AgentMemory[]
  recalled_reflections: AgentReflection[]
  session_state: AgentSessionState | null
  insights: AgentInsight[]
  thinking_steps: AgentThinkingStep[]
  memories: AgentMemory[]
  reflections: AgentReflection[]
  turns: AgentTurn[]
}

export interface AgentSessionContext {
  session: AgentSession
  state: AgentSessionState | null
  turns: AgentTurn[]
  execution_plans: AgentExecutionPlan[]
  insights: AgentInsight[]
  thinking_steps: AgentThinkingStep[]
  memories: AgentMemory[]
  reflections: AgentReflection[]
  recalled_memories: AgentMemory[]
  recalled_reflections: AgentReflection[]
}
