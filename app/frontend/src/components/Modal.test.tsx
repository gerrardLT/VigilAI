import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Modal } from './Modal'

describe('Modal', () => {
  // Mock showModal and close since jsdom doesn't support <dialog> natively
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
  })

  it('should render title and children when open', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="测试标题">
        <p>内容</p>
      </Modal>
    )
    expect(screen.getByText('测试标题')).toBeInTheDocument()
    expect(screen.getByText('内容')).toBeInTheDocument()
  })

  it('should call showModal when open is true', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题">
        内容
      </Modal>
    )
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
  })

  it('should have aria-modal attribute', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题">
        内容
      </Modal>
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('should have aria-labelledby pointing to title', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题">
        内容
      </Modal>
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title')
    expect(screen.getByText('标题')).toHaveAttribute('id', 'modal-title')
  })

  it('should render cancel button with default label', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题">
        内容
      </Modal>
    )
    expect(screen.getByText('取消')).toBeInTheDocument()
  })

  it('should render custom cancel label', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题" cancelLabel="关闭">
        内容
      </Modal>
    )
    expect(screen.getByText('关闭')).toBeInTheDocument()
  })

  it('should render confirm button when onConfirm and confirmLabel provided', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题" confirmLabel="确定" onConfirm={vi.fn()}>
        内容
      </Modal>
    )
    expect(screen.getByText('确定')).toBeInTheDocument()
  })

  it('should not render confirm button when onConfirm is not provided', () => {
    render(
      <Modal open={true} onClose={vi.fn()} title="标题" confirmLabel="确定">
        内容
      </Modal>
    )
    expect(screen.queryByText('确定')).not.toBeInTheDocument()
  })

  it('should call onClose when cancel button is clicked', () => {
    const onClose = vi.fn()
    render(
      <Modal open={true} onClose={onClose} title="标题">
        内容
      </Modal>
    )
    fireEvent.click(screen.getByText('取消'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('should call onConfirm when confirm button is clicked', () => {
    const onConfirm = vi.fn()
    render(
      <Modal open={true} onClose={vi.fn()} title="标题" confirmLabel="确定" onConfirm={onConfirm}>
        内容
      </Modal>
    )
    fireEvent.click(screen.getByText('确定'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('should call onClose on backdrop click', () => {
    const onClose = vi.fn()
    render(
      <Modal open={true} onClose={onClose} title="标题">
        内容
      </Modal>
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    // Simulate clicking the dialog element itself (backdrop)
    fireEvent.click(dialog)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('should call onClose on Escape key (cancel event)', () => {
    const onClose = vi.fn()
    render(
      <Modal open={true} onClose={onClose} title="标题">
        内容
      </Modal>
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    const cancelEvent = new Event('cancel', { bubbles: false, cancelable: true })
    fireEvent(dialog, cancelEvent)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
