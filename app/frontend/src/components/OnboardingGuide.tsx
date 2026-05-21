import type { AgentDomainType } from '../types'

interface PromptCard {
  label: string
  prompt: string
  icon: string
}

interface OnboardingGuideProps {
  domainType: AgentDomainType
  onSelectPrompt: (prompt: string) => void
}

const SUGGESTED_PROMPTS: Record<string, PromptCard[]> = {
  opportunity: [
    { label: '发现机会', prompt: '帮我找最近的黑客松和赏金机会', icon: '🔍' },
    { label: '分析机会', prompt: '分析这个机会值不值得参加', icon: '📊' },
    { label: '跟进管理', prompt: '我当前跟进的机会有哪些需要行动？', icon: '📋' },
    { label: '系统状态', prompt: '信息源的健康状态如何？', icon: '🏥' },
  ],
  product_selection: [
    { label: '选品研究', prompt: '帮我研究一下蓝牙耳机在淘宝的竞争情况', icon: '🔬' },
    { label: '对比分析', prompt: '对比我收藏的几个选品机会', icon: '⚖️' },
    { label: '市场趋势', prompt: '最近什么品类比较有机会？', icon: '📈' },
    { label: '跟进提醒', prompt: '我跟进的选品有什么需要更新的？', icon: '🔔' },
  ],
}

const DOMAIN_DESCRIPTIONS: Record<string, string> = {
  opportunity:
    '我可以帮你发现黑客松、赏金、Grant 等开发者赚钱机会，分析它们的价值，并管理你的跟进计划。',
  product_selection:
    '我可以帮你研究淘宝和闲鱼的选品机会，分析竞争情况、价格区间和市场趋势。',
}

export function OnboardingGuide({ domainType, onSelectPrompt }: OnboardingGuideProps) {
  const prompts = SUGGESTED_PROMPTS[domainType] ?? SUGGESTED_PROMPTS.opportunity
  const description = DOMAIN_DESCRIPTIONS[domainType] ?? DOMAIN_DESCRIPTIONS.opportunity

  return (
    <div
      data-testid="onboarding-guide"
      className="rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-6"
    >
      <p className="text-sm leading-6 text-slate-600" aria-label="系统能力描述">
        {description}
      </p>

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {prompts.map(card => (
          <button
            key={card.label}
            type="button"
            onClick={() => onSelectPrompt(card.prompt)}
            aria-label={`${card.label}: ${card.prompt}`}
            className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-sky-300 hover:bg-sky-50 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
          >
            <span className="mt-0.5 text-lg" aria-hidden="true">
              {card.icon}
            </span>
            <div className="min-w-0">
              <div className="text-sm font-medium text-slate-900 group-hover:text-sky-900">
                {card.label}
              </div>
              <div className="mt-0.5 text-xs leading-5 text-slate-500 group-hover:text-sky-700">
                {card.prompt}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default OnboardingGuide
