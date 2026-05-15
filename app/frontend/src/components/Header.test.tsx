import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header', () => {
  it('supports toggling the mobile menu', () => {
    render(
      <MemoryRouter initialEntries={['/agent']}>
        <Header />
      </MemoryRouter>
    )

    const menuButton = screen.getByRole('button', { name: 'Open navigation menu' })
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument()

    fireEvent.click(menuButton)

    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    const mobileMenu = screen.getByRole('navigation', { name: 'Mobile navigation' })
    expect(within(mobileMenu).getByRole('link', { name: '智能助手工作台' })).toBeInTheDocument()
    expect(within(mobileMenu).getByRole('link', { name: '奖励活动发现' })).toBeInTheDocument()
    expect(within(mobileMenu).getByRole('link', { name: '选品工作台' })).toBeInTheDocument()
    expect(within(mobileMenu).getByRole('link', { name: '来源' })).toBeInTheDocument()

    fireEvent.click(within(mobileMenu).getByRole('link', { name: '来源' }))

    expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument()
  })
})
