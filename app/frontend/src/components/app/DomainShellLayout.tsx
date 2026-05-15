import { Outlet } from 'react-router-dom'
import Footer from '../Footer'
import { ToastContainer } from '../Toast'
import { DomainHeader, type DomainNavLink } from './DomainHeader'

interface DomainShellLayoutProps {
  brandLabel: string
  brandTo: string
  navLinks: DomainNavLink[]
}

export function DomainShellLayout({ brandLabel, brandTo, navLinks }: DomainShellLayoutProps) {
  return (
    <ToastContainer>
      <div className="min-h-screen bg-gray-50">
        <div className="flex min-h-screen flex-col">
          <DomainHeader brandLabel={brandLabel} brandTo={brandTo} navLinks={navLinks} />
          <main className="flex-1">
            <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
              <Outlet />
            </div>
          </main>
          <Footer />
        </div>
      </div>
    </ToastContainer>
  )
}

export default DomainShellLayout
