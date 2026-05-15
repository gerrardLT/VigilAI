import { Link } from 'react-router-dom'
import DomainHeader from '../../components/app/DomainHeader'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'
import { useRewardSourceFeeds } from '../../hooks/useRewardSourceFeeds'
import { rewardPaths } from '../../routes/domainPaths'

const navLinks = [
  { path: rewardPaths.overview, label: '总览' },
  { path: rewardPaths.opportunities, label: '机会库' },
  { path: rewardPaths.operations, label: '运行面板' },
]

const healthStyles: Record<string, string> = {
  healthy: 'bg-emerald-100 text-emerald-800',
  watch: 'bg-amber-100 text-amber-800',
  risky: 'bg-orange-100 text-orange-800',
  cold: 'bg-rose-100 text-rose-800',
}

const failureCategoryLabels: Record<string, string> = {
  timeout: '超时',
  auth_or_permission: '鉴权/权限',
  not_found: '资源不存在',
  rate_limited: '限流',
  blocked_or_anti_bot: '反爬/封禁',
  network: '网络',
  invalid_content_shape: '内容形态异常',
  parsing: '解析',
  unknown: '未知',
}

const actionLabels: Record<string, string> = {
  reduce_depth: '降低抓取深度',
  switch_to_authenticated_source: '改成登录态来源',
  refresh_entry_url: '更新入口 URL',
  slow_down_schedule: '降低同步频率',
  retry_later: '稍后重试',
  review_extractor: '检查解析规则',
  rerun_and_inspect: '重跑并检查日志',
}

function formatFailureCategory(category?: string | null): string {
  if (!category) return '未分类'
  return failureCategoryLabels[category] ?? category
}

function formatAction(action?: string | null): string {
  if (!action) return '无'
  return actionLabels[action] ?? action
}

export default function RewardOperationsPage() {
  const {
    sources,
    recentJobs,
    failedJobs,
    discoveredSources,
    ignoredItems,
    failureCategoryCounts,
    recommendedActionCounts,
    queryTemplateDraft,
    setQueryTemplateDraft,
    failureFilter,
    setFailureFilter,
    actionFilter,
    setActionFilter,
    discovering,
    importingUrl,
    rerunningSourceId,
    togglingSourceId,
    actionSourceId,
    savingTemplates,
    syncing,
    lastSyncResult,
    lastSingleSyncResult,
    loading,
    error,
    reload,
    reloadDiscovery,
    syncSources,
    rerunSource,
    toggleSourcePaused,
    executeRecommendedAction,
    importDiscoveredSource,
    ignoreDiscoveredSource,
    unignoreDiscoveredSource,
    saveQueryTemplates,
  } = useRewardSourceFeeds()

  if (loading && sources.length === 0 && recentJobs.length === 0) {
    return <Loading text="加载奖励活动运行面板中..." />
  }

  if (error && sources.length === 0 && recentJobs.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void reload()} />
  }

  return (
    <main className="space-y-6" data-testid="reward-operations-page">
      <DomainHeader brandLabel="奖励活动 Agent" brandTo={rewardPaths.overview} navLinks={navLinks} />

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">手动同步</h2>
              <p className="mt-1 text-sm text-slate-600">立即执行抓取、召回、调查补证和结果入库，已停用、黑名单或未到窗口的来源会自动跳过。</p>
            </div>
            <button
              type="button"
              onClick={() => void syncSources()}
              disabled={syncing}
              className="inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-emerald-300"
            >
              {syncing ? '同步中...' : '立即同步'}
            </button>
          </div>
          {lastSyncResult ? (
            <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-4">
              <span>文档：{lastSyncResult.document_count}</span>
              <span>候选：{lastSyncResult.candidate_count}</span>
              <span>机会：{lastSyncResult.opportunity_count}</span>
              <span>失败：{lastSyncResult.failures.length}</span>
            </div>
          ) : null}
          {lastSingleSyncResult ? (
            <div className="mt-4 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">
              单源最近重跑：文档 {lastSingleSyncResult.document_count} / 候选 {lastSingleSyncResult.candidate_count} / 机会{' '}
              {lastSingleSyncResult.opportunity_count}
              {lastSingleSyncResult.error ? ` / 错误：${lastSingleSyncResult.error}` : ''}
            </div>
          ) : null}
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="text-sm text-slate-700">
              失败分类
              <select
                value={failureFilter}
                onChange={event => setFailureFilter(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="all">全部</option>
                {Object.keys(failureCategoryCounts).map(category => (
                  <option key={category} value={category}>
                    {formatFailureCategory(category)} ({failureCategoryCounts[category]})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-slate-700">
              建议动作
              <select
                value={actionFilter}
                onChange={event => setActionFilter(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="all">全部</option>
                {Object.keys(recommendedActionCounts).map(action => (
                  <option key={action} value={action}>
                    {formatAction(action)} ({recommendedActionCounts[action]})
                  </option>
                ))}
              </select>
            </label>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Scout 查询模板</h2>
              <p className="mt-1 text-sm text-slate-600">一行一个搜索模板，保存后会立刻用于来源发现。</p>
            </div>
            <button
              type="button"
              onClick={() => void saveQueryTemplates()}
              disabled={savingTemplates}
              className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              {savingTemplates ? '保存中...' : '保存模板'}
            </button>
          </div>
          <textarea
            value={queryTemplateDraft}
            onChange={event => setQueryTemplateDraft(event.target.value)}
            className="mt-4 min-h-48 w-full rounded-lg border border-slate-300 px-3 py-3 text-sm text-slate-800"
            placeholder={'invite reward program\nregister reward new user bonus\ntask reward bounty campaign'}
          />
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Scout 发现候选</h2>
              <p className="mt-1 text-sm text-slate-600">支持导入、忽略和恢复忽略，避免无效来源反复出现。</p>
            </div>
            <button
              type="button"
              onClick={() => void reloadDiscovery()}
              disabled={discovering}
              className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              {discovering ? '发现中...' : '刷新发现'}
            </button>
          </div>
          <div className="mt-4 space-y-3">
            {discoveredSources.length === 0 ? (
              <p className="text-sm text-slate-500">暂无新的来源候选。</p>
            ) : (
              discoveredSources.map(item => (
                <div key={item.dedupe_key || item.entry_url} className="rounded-lg border border-slate-200 px-4 py-3">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-medium text-slate-900">{item.name}</div>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{item.source_platform}</span>
                        <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">score {item.score}</span>
                      </div>
                      <a href={item.entry_url} target="_blank" rel="noreferrer" className="block text-sm text-emerald-700 hover:underline">
                        {item.entry_url}
                      </a>
                      {item.matched_urls && item.matched_urls.length > 1 ? (
                        <p className="text-xs text-slate-500">同模式命中 {item.matched_urls.length} 个链接，已合并显示。</p>
                      ) : null}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void ignoreDiscoveredSource(item)}
                        disabled={importingUrl === item.entry_url}
                        className="inline-flex rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
                      >
                        忽略
                      </button>
                      <button
                        type="button"
                        onClick={() => void importDiscoveredSource(item)}
                        disabled={importingUrl === item.entry_url}
                        className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                      >
                        {importingUrl === item.entry_url ? '处理中...' : '加入来源'}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          {ignoredItems.length > 0 ? (
            <div className="mt-6 space-y-2">
              <h3 className="text-sm font-medium text-slate-900">已忽略候选</h3>
              {ignoredItems.map(item => (
                <div key={item.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="truncate text-slate-600">{item.entry_url}</span>
                  <button
                    type="button"
                    onClick={() => void unignoreDiscoveredSource(item)}
                    className="text-slate-900 underline underline-offset-4"
                  >
                    恢复
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">来源配置</h2>
              <p className="mt-1 text-sm text-slate-600">优先展示需要处置的来源。详情页可编辑基础信息、调度、合并和审计记录。</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {sources.length === 0 ? (
              <p className="text-sm text-slate-500">暂无来源配置。</p>
            ) : (
              sources.map(source => (
                <div key={source.id} className="rounded-lg border border-slate-200 px-4 py-3">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link to={rewardPaths.sourceDetail(source.id)} className="font-medium text-slate-900 hover:text-emerald-700">
                          {source.name}
                        </Link>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{source.source_type}</span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${healthStyles[source.health_level || 'cold']}`}>
                          健康度 {source.health_score ?? 0}
                        </span>
                        {source.cold_start_status === 'cold_start_failed' ? (
                          <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-medium text-rose-700">冷启动失败</span>
                        ) : null}
                        {source.pause_mode === 'suggested' ? (
                          <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-medium text-rose-700">建议停用</span>
                        ) : null}
                        {source.is_paused ? (
                          <span className="rounded-full bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700">已停用</span>
                        ) : null}
                      </div>
                      <div className="text-xs text-slate-500">{source.entry_url || '未配置入口 URL'}</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => void rerunSource(source.id)}
                        disabled={source.is_paused || rerunningSourceId === source.id}
                        className="inline-flex rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
                      >
                        {rerunningSourceId === source.id ? '重跑中...' : '重跑单源'}
                      </button>
                      {source.recommended_action ? (
                        <button
                          type="button"
                          onClick={() => void executeRecommendedAction(source.id, source.recommended_action!)}
                          disabled={actionSourceId === source.id}
                          className="inline-flex rounded-lg border border-emerald-300 px-3 py-1.5 text-xs font-medium text-emerald-700 disabled:cursor-not-allowed disabled:text-emerald-300"
                        >
                          {actionSourceId === source.id ? '执行中...' : formatAction(source.recommended_action)}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => void toggleSourcePaused(source.id, !source.is_paused)}
                        disabled={togglingSourceId === source.id}
                        className="inline-flex rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
                      >
                        {togglingSourceId === source.id ? '处理中...' : source.is_paused ? '恢复来源' : '停用来源'}
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                    <span>最近抓取：{source.last_crawled_at || '从未'}</span>
                    <span>最近成功：{source.last_success_at || '从未'}</span>
                    <span>近 6 次成功：{source.recent_job_stats?.success_runs ?? 0}</span>
                    <span>近 6 次失败：{source.recent_job_stats?.failed_runs ?? 0}</span>
                    <span>连续失败：{source.consecutive_failures ?? 0}</span>
                    <span>调度：{source.schedule?.auto_sync_enabled ? `每 ${source.schedule.sync_interval_minutes} 分钟` : '自动同步关闭'}</span>
                    <span>当前失败分类：{formatFailureCategory(source.current_failure_category)}</span>
                    <span>建议动作：{formatAction(source.recommended_action)}</span>
                    <span className="md:col-span-2">
                      近期失败分类：{source.recent_failure_categories?.length ? source.recent_failure_categories.map(formatFailureCategory).join('、') : '无'}
                    </span>
                    {source.failure_advice ? <span className="md:col-span-2">处理建议：{source.failure_advice}</span> : null}
                  </div>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">最近抓取任务</h2>
          <div className="mt-4 space-y-3">
            {recentJobs.length === 0 ? (
              <p className="text-sm text-slate-500">暂无抓取任务。</p>
            ) : (
              recentJobs.map(job => (
                <div key={job.id} className="rounded-lg border border-slate-200 px-4 py-3">
                  <div className="flex items-center justify-between gap-4">
                    <div className="font-medium text-slate-900">{job.id}</div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{job.status}</span>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                    <span>文档：{job.document_count}</span>
                    <span>候选：{job.candidate_count}</span>
                    <span>机会：{job.opportunity_count}</span>
                    <span>完成时间：{job.completed_at || '运行中'}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">最近失败记录</h2>
          <div className="mt-4 space-y-3">
            {failedJobs.length === 0 ? (
              <p className="text-sm text-slate-500">暂无失败记录。</p>
            ) : (
              failedJobs.map(job => (
                <div key={job.id} className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
                  <div className="flex items-center justify-between gap-4">
                    <div className="font-medium text-slate-900">{job.id}</div>
                    <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-medium text-rose-700">{job.status}</span>
                  </div>
                  <div className="mt-2 text-sm text-rose-700">{job.error_message || '未知错误'}</div>
                  <div className="mt-1 text-xs text-rose-700">失败分类：{formatFailureCategory(job.failure_category)}</div>
                  <div className="mt-1 text-xs text-rose-700">建议动作：{formatAction(job.recommended_action)}</div>
                  {job.failure_advice ? <div className="mt-1 text-xs text-rose-700">处理建议：{job.failure_advice}</div> : null}
                </div>
              ))
            )}
          </div>
        </article>
      </section>
    </main>
  )
}
