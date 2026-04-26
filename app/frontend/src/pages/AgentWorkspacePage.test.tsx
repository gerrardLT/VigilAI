import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AgentWorkspacePage from './AgentWorkspacePage'

const agentApiMocks = vi.hoisted(() => ({
  createSession: vi.fn(),
  postTurn: vi.fn(),
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
      })
    })

    await waitFor(() => {
      expect(agentApiMocks.postTurn).toHaveBeenCalledWith('session-opportunity', {
        content: 'Find solo-friendly grants worth following up',
      })
    })

    expect(await screen.findByText(/reward size, deadline, or solo execution/i)).toBeInTheDocument()
    expect(screen.getByText('Opportunity Intake Checklist')).toBeInTheDocument()
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

    fireEvent.change(screen.getByRole('textbox', { name: 'Selection Prompt' }), {
      target: { value: 'Compare Taobao and Xianyu pet water fountain opportunities' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(agentApiMocks.createSession).toHaveBeenNthCalledWith(2, {
        domain_type: 'product_selection',
        entry_mode: 'chat',
      })
    })

    await waitFor(() => {
      expect(agentApiMocks.postTurn).toHaveBeenCalledWith('session-selection', {
        content: 'Compare Taobao and Xianyu pet water fountain opportunities',
      })
    })

    expect(await screen.findByText('Selection Intake Checklist')).toBeInTheDocument()
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
