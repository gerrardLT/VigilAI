import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AgentWorkspacePage from './AgentWorkspacePage'

const agentApiMocks = vi.hoisted(() => ({
  createSession: vi.fn(),
  postTurn: vi.fn(),
  getSessionContext: vi.fn(),
}))

vi.mock('../services/agentPlatformApi', () => ({
  agentPlatformApi: agentApiMocks,
}))

describe('AgentWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    agentApiMocks.createSession.mockImplementation(async (payload: { domain_type: string }) => ({
      id: payload.domain_type === 'product_selection' ? 'session-selection' : 'session-opportunity',
      domain_type: payload.domain_type,
      entry_mode: 'chat',
      status: 'active',
      policy_mode: 'standard',
      memory_scope: 'domain',
      title: null,
      created_at: '2026-04-25T10:00:00Z',
      updated_at: '2026-04-25T10:00:00Z',
      last_turn_at: null,
    }))

    agentApiMocks.postTurn.mockImplementation(async (sessionId: string, payload: { content: string }) => {
      if (sessionId === 'session-selection') {
        return {
          session: {
            id: 'session-selection',
            domain_type: 'product_selection',
            entry_mode: 'chat',
            status: 'active',
            policy_mode: 'standard',
            memory_scope: 'domain',
            title: null,
            created_at: '2026-04-25T10:00:00Z',
            updated_at: '2026-04-25T10:00:02Z',
            last_turn_at: '2026-04-25T10:00:02Z',
          },
          user_turn: {
            id: 'turn-selection-1',
            session_id: 'session-selection',
            role: 'user',
            content: payload.content,
            sequence_no: 1,
            tool_name: null,
            tool_payload: {},
            created_at: '2026-04-25T10:00:01Z',
          },
          assistant_turn: {
            id: 'turn-selection-2',
            session_id: 'session-selection',
            role: 'assistant',
            content:
              'I started a product-selection pass. Tell me whether margin, sell-through speed, or after-sales risk matters most.',
            sequence_no: 2,
            tool_name: null,
            tool_payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
          artifacts: [
            {
              id: 'artifact-selection-1',
              session_id: 'session-selection',
              artifact_type: 'checklist',
              title: 'Selection Intake Checklist',
              content: 'Add target platform, budget range, sourcing model, and expected margin.',
              payload: { domain_type: 'product_selection' },
              created_at: '2026-04-25T10:00:02Z',
            },
            {
              id: 'artifact-selection-2',
              session_id: 'session-selection',
              artifact_type: 'comparison',
              title: 'Cross-Platform Comparison',
              content: 'Cross-platform comparison:',
              payload: {
                job: { id: 'job-selection' },
                compare_rows: [{ id: 'sel-1' }, { id: 'sel-2' }],
              },
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          tool_calls: [{ tool_name: 'selection_compare', status: 'completed' }],
          execution_plan: {
            id: 'plan-selection-1',
            session_id: 'session-selection',
            source_turn_id: 'turn-selection-1',
            mode: 'allow',
            summary: 'Prepared orchestration plan for product_selection: selection_compare.',
            requested_steps: [
              {
                tool_name: 'selection_compare',
                intent: 'cross_platform_comparison',
                rationale: 'The message asks for cross-platform comparison or references both Taobao and Xianyu.',
                priority: 1,
                stage: 'analysis',
                access_mode: 'read_only',
                policy_decision: 'allow',
                metadata: { domain_type: 'product_selection' },
              },
            ],
            runnable_tools: ['selection_compare'],
            blocked_tools: [],
            risk_flags: [],
            reasoning:
              'The product_selection session produced the following tool route: selection_compare -> cross_platform_comparison (allow).',
            payload: { requested_tool_count: 1 },
            created_at: '2026-04-25T10:00:02Z',
          },
          recalled_memories: [],
          recalled_reflections: [],
          session_state: null,
          insights: [],
          thinking_steps: [],
          memories: [],
          reflections: [],
          turns: [
            {
              id: 'turn-selection-1',
              session_id: 'session-selection',
              role: 'user',
              content: payload.content,
              sequence_no: 1,
              tool_name: null,
              tool_payload: {},
              created_at: '2026-04-25T10:00:01Z',
            },
            {
              id: 'turn-selection-2',
              session_id: 'session-selection',
              role: 'assistant',
              content:
                'I started a product-selection pass. Tell me whether margin, sell-through speed, or after-sales risk matters most.',
              sequence_no: 2,
              tool_name: null,
              tool_payload: {},
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
        }
      }

      return {
        session: {
          id: 'session-opportunity',
          domain_type: 'opportunity',
          entry_mode: 'chat',
          status: 'active',
          policy_mode: 'standard',
          memory_scope: 'domain',
          title: null,
          created_at: '2026-04-25T10:00:00Z',
          updated_at: '2026-04-25T10:00:02Z',
          last_turn_at: '2026-04-25T10:00:02Z',
        },
        user_turn: {
          id: 'turn-opportunity-1',
          session_id: 'session-opportunity',
          role: 'user',
          content: payload.content,
          sequence_no: 1,
          tool_name: null,
          tool_payload: {},
          created_at: '2026-04-25T10:00:01Z',
        },
        assistant_turn: {
          id: 'turn-opportunity-2',
          session_id: 'session-opportunity',
          role: 'assistant',
          content:
            'I scoped an initial opportunity pass. Tell me whether you care most about reward size, deadline, or solo execution.',
          sequence_no: 2,
          tool_name: null,
          tool_payload: {},
          created_at: '2026-04-25T10:00:02Z',
        },
        artifacts: [
          {
            id: 'artifact-opportunity-1',
            session_id: 'session-opportunity',
            artifact_type: 'checklist',
            title: 'Opportunity Intake Checklist',
            content: 'Add budget, time window, target category, and execution constraints.',
            payload: { domain_type: 'opportunity' },
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        tool_calls: [{ tool_name: 'opportunity_search', status: 'completed' }],
        execution_plan: {
          id: 'plan-opportunity-1',
          session_id: 'session-opportunity',
          source_turn_id: 'turn-opportunity-1',
          mode: 'allow',
          summary: 'Prepared orchestration plan for opportunity: opportunity_search.',
          requested_steps: [
            {
              tool_name: 'opportunity_search',
              intent: 'discovery',
              rationale: 'The message asks for finding or filtering opportunity candidates.',
              priority: 1,
              stage: 'discovery',
              access_mode: 'read_only',
              policy_decision: 'allow',
              metadata: { domain_type: 'opportunity' },
            },
          ],
          runnable_tools: ['opportunity_search'],
          blocked_tools: [],
          risk_flags: [],
          reasoning:
            'The opportunity session produced the following tool route: opportunity_search -> discovery (allow).',
          payload: { requested_tool_count: 1 },
          created_at: '2026-04-25T10:00:02Z',
        },
        recalled_memories: [],
        recalled_reflections: [],
        session_state: null,
        insights: [],
        thinking_steps: [],
        memories: [],
        reflections: [],
        turns: [
          {
            id: 'turn-opportunity-1',
            session_id: 'session-opportunity',
            role: 'user',
            content: payload.content,
            sequence_no: 1,
            tool_name: null,
            tool_payload: {},
            created_at: '2026-04-25T10:00:01Z',
          },
          {
            id: 'turn-opportunity-2',
            session_id: 'session-opportunity',
            role: 'assistant',
            content:
              'I scoped an initial opportunity pass. Tell me whether you care most about reward size, deadline, or solo execution.',
            sequence_no: 2,
            tool_name: null,
            tool_payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
      }
    })

    agentApiMocks.getSessionContext.mockImplementation(async (sessionId: string) => {
      if (sessionId === 'session-selection') {
        return {
          session: {
            id: 'session-selection',
            domain_type: 'product_selection',
            entry_mode: 'chat',
            status: 'active',
            policy_mode: 'standard',
            memory_scope: 'domain',
            title: null,
            created_at: '2026-04-25T10:00:00Z',
            updated_at: '2026-04-25T10:00:02Z',
            last_turn_at: '2026-04-25T10:00:02Z',
          },
          state: {
            session_id: 'session-selection',
            goal: 'Compare product ideas across platforms',
            constraints: ['Prefer low return risk'],
            preferences: ['Prioritize margin'],
            working_memory: ['Pet fountain demand appears steady'],
            current_focus: 'Cross-platform comparison',
            next_question: 'Should we prioritize sell-through speed or margin?',
            next_action: 'Validate sourcing and after-sales risk',
            summary: 'Selection session is focused on comparing stable pet accessory demand.',
            last_tool_names: ['selection_compare'],
            state_payload: {},
            created_at: '2026-04-25T10:00:02Z',
            updated_at: '2026-04-25T10:00:02Z',
          },
          turns: [
            {
              id: 'turn-selection-1',
              session_id: 'session-selection',
              role: 'user',
              content: 'Compare Taobao and Xianyu pet water fountain opportunities',
              sequence_no: 1,
              tool_name: null,
              tool_payload: {},
              created_at: '2026-04-25T10:00:01Z',
            },
            {
              id: 'turn-selection-2',
              session_id: 'session-selection',
              role: 'assistant',
              content:
                'I started a product-selection pass. Tell me whether margin, sell-through speed, or after-sales risk matters most.',
              sequence_no: 2,
              tool_name: null,
              tool_payload: {},
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          execution_plans: [
            {
              id: 'plan-selection-1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-1',
              mode: 'allow',
              summary: 'Prepared orchestration plan for product_selection: selection_compare.',
              requested_steps: [
                {
                  tool_name: 'selection_compare',
                  intent: 'cross_platform_comparison',
                  rationale:
                    'The message asks for cross-platform comparison or references both Taobao and Xianyu.',
                  priority: 1,
                  stage: 'analysis',
                  access_mode: 'read_only',
                  policy_decision: 'allow',
                  metadata: { domain_type: 'product_selection' },
                },
              ],
              runnable_tools: ['selection_compare'],
              blocked_tools: [],
              risk_flags: [],
              reasoning:
                'The product_selection session produced the following tool route: selection_compare -> cross_platform_comparison (allow).',
              payload: { requested_tool_count: 1 },
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          insights: [
            {
              id: 'insight-selection-1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-1',
              insight_type: 'preference',
              content: 'The user is comparing platform-specific product opportunities.',
              importance: 0.82,
              payload: {},
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          thinking_steps: [
            {
              id: 'thinking-selection-1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-1',
              phase: 'tool-routing',
              summary: 'Selected comparison tooling before composing the reply.',
              tool_name: 'selection_compare',
              payload: {},
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          memories: [
            {
              id: 'memory-selection-1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-1',
              memory_type: 'preference',
              content: 'This workflow values platform comparison over single-source research.',
              importance: 0.74,
              payload: {},
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          reflections: [
            {
              id: 'reflection-selection-1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-1',
              reflection_type: 'turn_review',
              summary: 'The assistant should keep prompting for margin and risk tradeoffs.',
              action_item: 'Ask for the deciding metric before expanding the shortlist.',
              score: 0.68,
              payload: {},
              created_at: '2026-04-25T10:00:02Z',
            },
          ],
          recalled_memories: [
            {
              id: 'memory-selection-r1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-0',
              memory_type: 'domain',
              content: 'Previous selection sessions preferred stable demand over hype categories.',
              importance: 0.8,
              payload: {},
              created_at: '2026-04-24T10:00:02Z',
            },
          ],
          recalled_reflections: [
            {
              id: 'reflection-selection-r1',
              session_id: 'session-selection',
              source_turn_id: 'turn-selection-0',
              reflection_type: 'playbook',
              summary: 'Bring in sourcing-risk checks before recommending any tracked item.',
              action_item: 'Review the top shortlisted SKUs for returns and warranty load.',
              score: 0.72,
              payload: {},
              created_at: '2026-04-24T10:00:02Z',
            },
          ],
        }
      }

      return {
        session: {
          id: 'session-opportunity',
          domain_type: 'opportunity',
          entry_mode: 'chat',
          status: 'active',
          policy_mode: 'standard',
          memory_scope: 'domain',
          title: null,
          created_at: '2026-04-25T10:00:00Z',
          updated_at: '2026-04-25T10:00:02Z',
          last_turn_at: '2026-04-25T10:00:02Z',
        },
        state: {
          session_id: 'session-opportunity',
          goal: 'Find grant opportunities',
          constraints: ['Solo-friendly only'],
          preferences: ['Clear rewards'],
          working_memory: ['Looking for near-term grants'],
          current_focus: 'Initial opportunity qualification',
          next_question: 'Do you prefer larger rewards or shorter deadlines?',
          next_action: 'Filter for solo-friendly grants and compare deadlines',
          summary: 'Opportunity session is scoped around clear-reward grants with solo execution.',
          last_tool_names: ['opportunity_search'],
          state_payload: {},
          created_at: '2026-04-25T10:00:02Z',
          updated_at: '2026-04-25T10:00:02Z',
        },
        turns: [
          {
            id: 'turn-opportunity-1',
            session_id: 'session-opportunity',
            role: 'user',
            content: 'Find solo-friendly grants worth following up',
            sequence_no: 1,
            tool_name: null,
            tool_payload: {},
            created_at: '2026-04-25T10:00:01Z',
          },
          {
            id: 'turn-opportunity-2',
            session_id: 'session-opportunity',
            role: 'assistant',
            content:
              'I scoped an initial opportunity pass. Tell me whether you care most about reward size, deadline, or solo execution.',
            sequence_no: 2,
            tool_name: null,
            tool_payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        execution_plans: [
          {
            id: 'plan-opportunity-1',
            session_id: 'session-opportunity',
            source_turn_id: 'turn-opportunity-1',
            mode: 'allow',
            summary: 'Prepared orchestration plan for opportunity: opportunity_search.',
            requested_steps: [
              {
                tool_name: 'opportunity_search',
                intent: 'discovery',
                rationale: 'The message asks for finding or filtering opportunity candidates.',
                priority: 1,
                stage: 'discovery',
                access_mode: 'read_only',
                policy_decision: 'allow',
                metadata: { domain_type: 'opportunity' },
              },
            ],
            runnable_tools: ['opportunity_search'],
            blocked_tools: [],
            risk_flags: [],
            reasoning:
              'The opportunity session produced the following tool route: opportunity_search -> discovery (allow).',
            payload: { requested_tool_count: 1 },
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        insights: [
          {
            id: 'insight-opportunity-1',
            session_id: 'session-opportunity',
            source_turn_id: 'turn-opportunity-1',
            insight_type: 'constraint',
            content: 'The user needs solo-friendly opportunities.',
            importance: 0.91,
            payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        thinking_steps: [
          {
            id: 'thinking-opportunity-1',
            session_id: 'session-opportunity',
            source_turn_id: 'turn-opportunity-1',
            phase: 'search',
            summary: 'Searched for grant candidates before asking for a tradeoff.',
            tool_name: 'opportunity_search',
            payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        memories: [
          {
            id: 'memory-opportunity-1',
            session_id: 'session-opportunity',
            source_turn_id: 'turn-opportunity-1',
            memory_type: 'constraint',
            content: 'Solo execution is a persistent requirement.',
            importance: 0.89,
            payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        reflections: [
          {
            id: 'reflection-opportunity-1',
            session_id: 'session-opportunity',
            source_turn_id: 'turn-opportunity-1',
            reflection_type: 'turn_review',
            summary: 'The assistant should narrow by reward and deadline on the next turn.',
            action_item: 'Ask which tradeoff matters more before proposing options.',
            score: 0.66,
            payload: {},
            created_at: '2026-04-25T10:00:02Z',
          },
        ],
        recalled_memories: [
          {
            id: 'memory-opportunity-r1',
            session_id: 'session-opportunity',
            source_turn_id: 'turn-opportunity-0',
            memory_type: 'user_preference',
            content: 'Earlier sessions also preferred solo-friendly filters.',
            importance: 0.7,
            payload: {},
            created_at: '2026-04-24T10:00:02Z',
          },
        ],
        recalled_reflections: [],
      }
    })
  })

  it('creates an opportunity session and sends a user turn', async () => {
    render(
      <MemoryRouter>
        <AgentWorkspacePage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByRole('textbox', { name: 'Opportunity Prompt' }), {
      target: { value: 'Find solo-friendly grants worth following up' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(agentApiMocks.createSession).toHaveBeenCalledWith({
        domain_type: 'opportunity',
        entry_mode: 'chat',
        policy_mode: 'standard',
        memory_scope: 'domain',
      })
    })

    await waitFor(() => {
      expect(agentApiMocks.postTurn).toHaveBeenCalledWith('session-opportunity', {
        content: 'Find solo-friendly grants worth following up',
      })
    })

    await waitFor(() => {
      expect(agentApiMocks.getSessionContext).toHaveBeenCalledWith('session-opportunity')
    })

    expect(await screen.findByText(/reward size, deadline, or solo execution/i)).toBeInTheDocument()
    expect(screen.getByText('Opportunity Intake Checklist')).toBeInTheDocument()
    expect(screen.getByText('Session Intelligence')).toBeInTheDocument()
    expect(screen.getByText('Execution Plans')).toBeInTheDocument()
    expect(screen.getByText('Prepared orchestration plan for opportunity: opportunity_search.')).toBeInTheDocument()
    expect(screen.getByText('Initial opportunity qualification')).toBeInTheDocument()
    expect(screen.getByText('The user needs solo-friendly opportunities.')).toBeInTheDocument()
    expect(screen.getByText('Earlier sessions also preferred solo-friendly filters.')).toBeInTheDocument()
  })

  it('switches domains, clears prior state, and creates a product-selection session', async () => {
    render(
      <MemoryRouter>
        <AgentWorkspacePage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByRole('textbox', { name: 'Opportunity Prompt' }), {
      target: { value: 'Find solo-friendly grants worth following up' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Opportunity Intake Checklist')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Product Selection/i }))

    await waitFor(() => {
      expect(screen.queryByText('Opportunity Intake Checklist')).not.toBeInTheDocument()
    })
    expect(
      screen.getByText('No conversation yet. Switch domains at any time to start a fresh session.')
    ).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Policy Mode'), {
      target: { value: 'strict' },
    })
    fireEvent.change(screen.getByLabelText('Memory Scope'), {
      target: { value: 'global' },
    })

    fireEvent.change(screen.getByRole('textbox', { name: 'Selection Prompt' }), {
      target: { value: 'Compare Taobao and Xianyu pet water fountain opportunities' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(agentApiMocks.createSession).toHaveBeenNthCalledWith(2, {
        domain_type: 'product_selection',
        entry_mode: 'chat',
        policy_mode: 'strict',
        memory_scope: 'global',
      })
    })

    await waitFor(() => {
      expect(agentApiMocks.postTurn).toHaveBeenCalledWith('session-selection', {
        content: 'Compare Taobao and Xianyu pet water fountain opportunities',
      })
    })

    await waitFor(() => {
      expect(agentApiMocks.getSessionContext).toHaveBeenCalledWith('session-selection')
    })

    expect(await screen.findByText('Selection Intake Checklist')).toBeInTheDocument()
    expect(screen.getByText('Cross-platform comparison')).toBeInTheDocument()
    expect(
      screen.getByText('Prepared orchestration plan for product_selection: selection_compare.')
    ).toBeInTheDocument()
    expect(
      screen.getByText('Previous selection sessions preferred stable demand over hype categories.')
    ).toBeInTheDocument()
    expect(
      screen.getByText('Bring in sourcing-risk checks before recommending any tracked item.')
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open shortlist' })).toHaveAttribute(
      'href',
      '/selection/opportunities?query_id=job-selection'
    )
    expect(screen.getByRole('link', { name: 'Open compare view' })).toHaveAttribute(
      'href',
      '/selection/compare?ids=sel-1&ids=sel-2'
    )
  })
})
