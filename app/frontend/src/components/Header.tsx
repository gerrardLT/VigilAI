import { useEffect, useId, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { APP_NAME } from '../utils/constants'

const navLinks = [
  { path: '/', label: '工作台' },
  { path: '/activities', label: '机会池' },
  { path: '/analysis/results', label: '分析结果' },
  { path: '/analysis/templates', label: '模板中心' },
  { path: '/tracking', label: '跟进' },
  { path: '/digests', label: '日报' },
  { path: '/sources', label: '来源' },
]

export function Header() {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname === '/workspace'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <header className="border-b border-gray-200 bg-white shadow-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" aria-label={`${APP_NAME} 首页`} className="flex items-center gap-2">
          <span className="text-2xl">V</span>
          <span className="text-xl font-bold text-gray-900">{APP_NAME}</span>
        </Link>

        <nav aria-label="主导航" className="hidden items-center gap-1 md:flex">
          {navLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              aria-current={isActive(link.path) ? 'page' : undefined}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isActive(link.path)
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="md:hidden">
          <MobileMenu />
        </div>
      </div>
    </header>
  )
}

function MobileMenu() {
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)
  const menuId = useId()

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname === '/workspace'
    }
    return location.pathname.startsWith(path)
  }

  useEffect(() => {
    setIsOpen(false)
  }, [location.pathname])

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={isOpen ? '收起导航菜单' : '打开导航菜单'}
        aria-expanded={isOpen}
        aria-controls={menuId}
        onClick={() => setIsOpen(current => !current)}
        className="rounded-lg p-2.5 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      {isOpen ? (
        <nav
          id={menuId}
          aria-label="移动端导航菜单"
          className="absolute right-0 top-full z-20 mt-2 w-48 rounded-lg border border-gray-200 bg-white py-2 shadow-lg"
        >
          {navLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              aria-current={isActive(link.path) ? 'page' : undefined}
              className={`block px-4 py-3 text-sm ${
                isActive(link.path) ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </div>
  )
}

export default Header
