import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header', () => {
  it('supports toggling the mobile menu for the system-level entry nav', () => {
    render(
      <MemoryRouter initialEntries={['/opportunity/workspace']}>
        <Header />
      </MemoryRouter>
    )

    const menuButton = screen.getByRole('button', { name: '打开VigilAI导航菜单' })
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: 'VigilAI移动端导航菜单' })).not.toBeInTheDocument()

    fireEvent.click(menuButton)

    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    const mobileMenu = screen.getByRole('navigation', { name: 'VigilAI移动端导航菜单' })
    expect(within(mobileMenu).getByRole('link', { name: '旧机会系统' })).toBeInTheDocument()

    fireEvent.click(within(mobileMenu).getByRole('link', { name: 'Agent 平台' }))

    expect(screen.queryByRole('navigation', { name: 'VigilAI移动端导航菜单' })).not.toBeInTheDocument()
  })
})
