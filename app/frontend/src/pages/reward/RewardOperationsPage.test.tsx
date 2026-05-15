import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RewardOperationsPage from './RewardOperationsPage'

const rewardApiMocks = vi.hoisted(() => ({
  getOperations: vi.fn(),
  getSourceDiscovery: vi.fn(),
  importDiscoveredSource: vi.fn(),
  syncSources: vi.fn(),
  syncSingleSource: vi.fn(),
  pauseSource: vi.fn(),
  resumeSource: vi.fn(),
  updateScoutSettings: vi.fn(),
}))

vi.mock('../../services/rewardOpportunityApi', () => ({
  rewardOpportunityApi: rewardApiMocks,
}))

describe('RewardOperationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rewardApiMocks.getOperations.mockResolvedValue({
      sources: [
        {
          id: 'source-risky',
          name: 'Risky Feed',
          source_type: 'web',
          status: 'error',
          health_score: 20,
          health_level: 'cold',
          cold_start_status: 'cold_start_failed',
          is_paused: false,
          current_failure_category: 'timeout',
          recent_failure_categories: ['timeout'],
          recent_failure_reasons: ['timeout'],
          failure_advice: '建议降低抓取深度，减少 follow-up 链接数量，优先保留入口页和规则页。',
          recommended_action: 'reduce_depth',
          recent_job_stats: {
            total_runs: 2,
            success_runs: 0,
            failed_runs: 2,
            avg_documents: 0,
          },
          last_crawled_at: '2026-05-01T10:00:00Z',
          last_success_at: null,
          last_error_message: 'timeout',
          created_at: '2026-05-01T09:00:00Z',
          updated_at: '2026-05-01T10:10:00Z',
        },
        {
          id: 'source-paused',
          name: 'Paused Feed',
          source_type: 'web',
          status: 'idle',
          health_score: 80,
          health_level: 'watch',
          cold_start_status: null,
          is_paused: true,
          current_failure_category: null,
          recent_failure_categories: [],
          recent_failure_reasons: [],
          failure_advice: null,
          recommended_action: null,
          recent_job_stats: {
            total_runs: 1,
            success_runs: 1,
            failed_runs: 0,
            avg_documents: 3,
          },
          last_crawled_at: '2026-05-01T10:00:00Z',
          last_success_at: '2026-05-01T10:10:00Z',
          last_error_message: null,
          created_at: '2026-05-01T09:10:00Z',
          updated_at: '2026-05-01T10:10:00Z',
        },
      ],
      recent_jobs: [
        {
          id: 'job-1',
          source_feed_id: 'source-risky',
          status: 'completed',
          mode: 'scheduled',
          document_count: 3,
          candidate_count: 2,
          opportunity_count: 1,
          created_at: '2026-05-01T10:00:00Z',
          completed_at: '2026-05-01T10:10:00Z',
        },
      ],
      failed_jobs: [
        {
          id: 'job-fail-1',
          source_feed_id: 'source-risky',
          status: 'failed',
          mode: 'scheduled',
          document_count: 0,
          candidate_count: 0,
          opportunity_count: 0,
          error_message: 'timeout',
          failure_category: 'timeout',
          failure_advice: '建议降低抓取深度，减少 follow-up 链接数量，优先保留入口页和规则页。',
          recommended_action: 'reduce_depth',
          created_at: '2026-05-01T10:00:00Z',
          completed_at: '2026-05-01T10:10:00Z',
        },
      ],
    })
    rewardApiMocks.getSourceDiscovery.mockResolvedValue({
      items: [
        {
          name: 'reddit.com / r',
          entry_url: 'https://reddit.com/r/airdrops',
          source_platform: 'reddit',
          source_type: 'social',
          discovery_queries: ['reward program referral'],
          reasons: ['matched scout query'],
          score: 6,
          dedupe_key: 'reddit.com|r/airdrops',
          matched_urls: ['https://reddit.com/r/airdrops', 'https://reddit.com/r/airdrops/new'],
        },
      ],
      total: 1,
      query_templates: ['reward program referral'],
    })
    rewardApiMocks.importDiscoveredSource.mockResolvedValue({
      id: 'source-2',
      name: 'reddit.com / r',
      source_type: 'social',
      source_platform: 'reddit',
      entry_url: 'https://reddit.com/r/airdrops',
      status: 'idle',
      config: {},
      import_preview: {
        source_feed_id: 'source-2',
        job_id: 'preview-job-1',
        document_count: 2,
        candidate_count: 1,
        opportunity_count: 1,
        error: null,
      },
      created_at: '2026-05-01T09:00:00Z',
      updated_at: '2026-05-01T09:00:00Z',
    })
    rewardApiMocks.syncSources.mockResolvedValue({
      source_count: 1,
      document_count: 3,
      candidate_count: 2,
      opportunity_count: 1,
      job_ids: ['job-1'],
      failures: [],
    })
    rewardApiMocks.syncSingleSource.mockResolvedValue({
      source_feed_id: 'source-risky',
      job_id: 'job-rerun-1',
      document_count: 4,
      candidate_count: 2,
      opportunity_count: 1,
      error: null,
    })
    rewardApiMocks.pauseSource.mockResolvedValue({
      id: 'source-risky',
      is_paused: true,
      status: 'error',
      updated_at: '2026-05-01T10:10:00Z',
    })
    rewardApiMocks.resumeSource.mockResolvedValue({
      id: 'source-paused',
      is_paused: false,
      status: 'idle',
      updated_at: '2026-05-01T10:10:00Z',
    })
    rewardApiMocks.updateScoutSettings.mockResolvedValue({
      id: 'default',
      query_templates: ['reward program referral'],
      updated_at: '2026-05-01T10:00:00Z',
    })
  })

  it('renders source controls, classification, and advice', async () => {
    render(
      <MemoryRouter>
        <RewardOperationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(rewardApiMocks.getOperations).toHaveBeenCalled()
      expect(rewardApiMocks.getSourceDiscovery).toHaveBeenCalled()
    })

    expect(await screen.findByTestId('reward-operations-page')).toBeInTheDocument()
    expect(screen.getByText('停用来源')).toBeInTheDocument()
    expect(screen.getByText('恢复来源')).toBeInTheDocument()
    expect(screen.getByText('已停用')).toBeInTheDocument()
    expect(screen.getAllByText('失败分类：超时')).toHaveLength(1)
    expect(screen.getByText('当前失败分类：超时')).toBeInTheDocument()
    expect(screen.getByText('近期失败分类：超时')).toBeInTheDocument()
    expect(screen.getAllByText('建议动作：降低抓取深度')).toHaveLength(2)
    expect(screen.getAllByText(/处理建议：建议降低抓取深度/)).toHaveLength(2)

    const sourceTitles = screen.getAllByText(/Feed$/)
    expect(sourceTitles[0]).toHaveTextContent('Risky Feed')
    expect(sourceTitles[1]).toHaveTextContent('Paused Feed')
  })
})
