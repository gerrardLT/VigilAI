import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header', () => {
  it('supports toggling the mobile menu with Chinese accessibility labels', () => {
    render(
      <MemoryRouter initialEntries={['/workspace']}>
        <Header />
      </MemoryRouter>
    )

    const menuButton = screen.getByRole('button', { name: '打开导航菜单' })
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: '移动端导航' })).not.toBeInTheDocument()

    fireEvent.click(menuButton)

    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    const mobileMenu = screen.getByRole('navigation', { name: '移动端导航' })
    expect(within(mobileMenu).getByRole('link', { name: '分析模板' })).toBeInTheDocument()
    expect(within(mobileMenu).getByRole('link', { name: '奖励' })).toBeInTheDocument()

    fireEvent.click(within(mobileMenu).getByRole('link', { name: '分析结果' }))

    expect(screen.queryByRole('navigation', { name: '移动端导航' })).not.toBeInTheDocument()
  })
})
