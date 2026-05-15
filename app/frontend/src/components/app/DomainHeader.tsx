import { Link, useLocation } from 'react-router-dom'

interface DomainNavLink {
  path: string
  label: string
}

interface DomainHeaderProps {
  brandLabel: string
  brandTo: string
  navLinks: DomainNavLink[]
}

export function DomainHeader({ brandLabel, brandTo, navLinks }: DomainHeaderProps) {
  const location = useLocation()

  return (
    <header className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <Link to={brandTo} className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
            {brandLabel}
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">奖励活动发现 Agent</h1>
        </div>
        <nav aria-label="奖励活动模块导航" className="flex flex-wrap gap-2">
          {navLinks.map(link => {
            const isActive = location.pathname === link.path || location.pathname.startsWith(`${link.path}/`)
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {link.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

export default DomainHeader
