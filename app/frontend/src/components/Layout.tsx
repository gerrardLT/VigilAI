import { Outlet } from 'react-router-dom'
import Header from './Header'
import Footer from './Footer'
import { ToastContainer } from './Toast'

/**
 * 布局组件
 * 包含Header、主内容区和Footer
 */
export function Layout() {
  return (
    <ToastContainer>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <Header />
        <main className="flex-1">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <Outlet />
          </div>
        </main>
        <Footer />
      </div>
    </ToastContainer>
  )
}

export default Layout
