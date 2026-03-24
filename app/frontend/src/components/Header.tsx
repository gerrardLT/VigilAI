import { Link, useLocation } from 'react-router-dom'
import { APP_NAME } from '../utils/constants'

const navLinks = [
  { path: '/', label: '工作台' },
  { path: '/activities', label: '机会池' },
  { path: '/tracking', label: '跟进' },
  { path: '/digests', label: '日报' },
  { path: '/sources', label: '信息源管理' },
]

/**
 * 头部导航组件
 */
export function Header() {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname === '/workspace'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">🎯</span>
            <span className="text-xl font-bold text-gray-900">{APP_NAME}</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map(link => (
              <Link
                key={link.path}
                to={link.path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive(link.path)
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <MobileMenu />
          </div>
        </div>
      </div>
    </header>
  )
}

/**
 * 移动端菜单组件
 */
function MobileMenu() {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname === '/workspace'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <div className="relative group">
      <button className="p-2 rounded-lg hover:bg-gray-100">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
        {navLinks.map(link => (
          <Link
            key={link.path}
            to={link.path}
            className={`block px-4 py-2 text-sm ${
              isActive(link.path)
                ? 'bg-primary-50 text-primary-700'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  )
}

export default Header
