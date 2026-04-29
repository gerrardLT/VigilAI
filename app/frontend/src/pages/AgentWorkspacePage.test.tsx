import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AgentWorkspacePage from './AgentWorkspacePage'

const agentApiMocks = vi.hoisted(() => ({
  createSession: vi.fn(),
  getSession: vi.fn(),
  listArtifacts: vi.fn(),
  listSessions: vi.fn(),
  listTurns: vi.fn(),
  postTurn: vi.fn(),
}))

vi.mock('../services/agentPlatformApi', () => ({
  agentPlatformApi: agentApiMocks,
}))

describe('AgentWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()

    agentApiMocks.listSessions.mockResolvedValue([])
    agentApiMocks.getSession.mockImplementation(async (sessionId: string) => ({
      id: sessionId,
      domain_type: sessionId.includes('selection') ? 'product_selection' : 'opportunity',
      entry_mode: 'chat',
      status: 'active',
      title: sessionId.includes('selection') ? 'Selection history' : 'Opportunity history',
      created_at: '2026-04-25T10:00:00Z',
      updated_at: '2026-04-25T10:00:00Z',
      last_turn_at: '2026-04-25T10:00:00Z',
    }))
    agentApiMocks.listTurns.mockResolvedValue([])
    agentApiMocks.listArtifacts.mockResolvedValue([])

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
            content: '我已经开始做一轮选品筛选。告诉我你更看重利润空间、出单速度，还是售后风险。',
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
              title: '选品输入清单',
              content: '补充目标平台、预算区间、货源模式和预期利润。',
              payload: { domain_type: 'product_selection' },
              created_at: '2026-04-25T10:00:02Z',
            },
            {
              id: 'artifact-selection-2',
              session_id: 'session-selection',
              artifact_type: 'comparison',
              title: '跨平台对比',
              content: '跨平台对比如下：',
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
              content: '我已经开始做一轮选品筛选。告诉我你更看重利润空间、出单速度，还是售后风险。',
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
          content: '我已经先做了一轮机会筛选。告诉我你更看重奖励规模、截止时间，还是个人可执行性。',
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
            title: '机会输入清单',
            content: '补充预算、时间窗口、目标类别和执行约束。',
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
            content: '我已经先做了一轮机会筛选。告诉我你更看重奖励规模、截止时间，还是个人可执行性。',
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

    fireEvent.change(screen.getByRole('textbox', { name: '机会输入' }), {
      target: { value: 'Find solo-friendly grants worth following up' },
    })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

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

    expect(await screen.findByText(/奖励规模、截止时间，还是个人可执行性/)).toBeInTheDocument()
    expect(screen.getByText('机会输入清单')).toBeInTheDocument()
  })

  it('restores a recent session from history', async () => {
    agentApiMocks.listSessions.mockResolvedValueOnce([
      {
        id: 'session-opportunity-history',
        domain_type: 'opportunity',
        entry_mode: 'chat',
        status: 'active',
        title: 'History session',
        created_at: '2026-04-24T10:00:00Z',
        updated_at: '2026-04-24T11:00:00Z',
        last_turn_at: '2026-04-24T11:00:00Z',
        turn_count: 4,
        last_turn_preview: 'Last assistant reply',
      },
    ])
    agentApiMocks.listTurns.mockResolvedValueOnce([
      {
        id: 'turn-history-1',
        session_id: 'session-opportunity-history',
        role: 'assistant',
        content: 'Restored conversation',
        sequence_no: 1,
        tool_name: null,
        tool_payload: {},
        created_at: '2026-04-24T11:00:00Z',
      },
    ])
    agentApiMocks.listArtifacts.mockResolvedValueOnce([
      {
        id: 'artifact-history-1',
        session_id: 'session-opportunity-history',
        artifact_type: 'checklist',
        title: 'History checklist',
        content: 'Restored artifact',
        payload: {},
        created_at: '2026-04-24T11:00:00Z',
      },
    ])

    render(
      <MemoryRouter>
        <AgentWorkspacePage />
      </MemoryRouter>
    )

    expect(await screen.findByText('History session')).toBeInTheDocument()
    expect(screen.getByText('Restored conversation')).toBeInTheDocument()
    expect(screen.getByText('History checklist')).toBeInTheDocument()
  })

  it('switches domains, clears prior state, and creates a product-selection session', async () => {
    render(
      <MemoryRouter>
        <AgentWorkspacePage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByRole('textbox', { name: '机会输入' }), {
      target: { value: 'Find solo-friendly grants worth following up' },
    })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('机会输入清单')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /商品选品/i }))

    await waitFor(() => {
      expect(screen.queryByText('机会输入清单')).not.toBeInTheDocument()
    })
    expect(screen.getByText('还没有对话，你可以随时切换领域开始新的会话。')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox', { name: '选品输入' }), {
      target: { value: 'Compare Taobao and Xianyu pet water fountain opportunities' },
    })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

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

    expect(await screen.findByText('选品输入清单')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '打开候选清单' })).toHaveAttribute(
      'href',
      '/selection/opportunities?query_id=job-selection'
    )
    expect(screen.getByRole('link', { name: '打开对比视图' })).toHaveAttribute(
      'href',
      '/selection/compare?ids=sel-1&ids=sel-2'
    )
  })
})
