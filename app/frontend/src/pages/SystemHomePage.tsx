import { Link } from 'react-router-dom'
import { agentPaths, opportunityPaths, selectionPaths } from '../routes/domainPaths'

const SYSTEMS = [
  {
    path: opportunityPaths.workspace,
    badge: '旧机会系统',
    title: '机会工作台',
    description: '处理机会池、跟进、日报、来源健康和 AI 分析模板。',
  },
  {
    path: agentPaths.home,
    badge: 'Agent 平台',
    title: '共享 Agent 入口',
    description: '只处理跨域会话、工具路由和产出物，不再和旧系统导航混在一起。',
  },
  {
    path: selectionPaths.workspace,
    badge: '选品域',
    title: '选品工作台',
    description: '专门处理淘宝、闲鱼研究任务、候选池、对比和跟进。',
  },
]

export function SystemHomePage() {
  return (
    <main className="mx-auto max-w-6xl space-y-8 py-10" data-testid="system-home-page">
      <section className="space-y-3">
        <div className="text-sm font-medium uppercase tracking-[0.24em] text-slate-500">VigilAI 前端入口</div>
        <h1 className="text-4xl font-semibold text-slate-950">选择要进入的系统</h1>
        <p className="max-w-3xl text-sm leading-7 text-slate-600">
          旧机会系统、Agent 平台、选品域已经拆成三套独立前端壳。这里是唯一中立入口。
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {SYSTEMS.map(system => (
          <Link
            key={system.path}
            to={system.path}
            className="block rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
          >
            <div className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
              {system.badge}
            </div>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">{system.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{system.description}</p>
          </Link>
        ))}
      </section>
    </main>
  )
}

export default SystemHomePage
