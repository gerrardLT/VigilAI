import { useEffect, useRef, useCallback } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm?: () => void
}

/**
 * 模态对话框组件
 * 使用原生 <dialog> 元素，自带焦点陷阱和 Escape 键关闭
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  confirmLabel,
  cancelLabel = '取消',
  onConfirm,
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  const handleCancel = useCallback(
    (e: React.SyntheticEvent) => {
      e.preventDefault()
      onClose()
    },
    [onClose]
  )

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDialogElement>) => {
      if (e.target === dialogRef.current) {
        onClose()
      }
    },
    [onClose]
  )

  return (
    <dialog
      ref={dialogRef}
      aria-modal="true"
      aria-labelledby="modal-title"
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      className="backdrop:bg-black/50 rounded-lg shadow-xl max-w-lg w-full p-0 m-auto"
    >
      <div className="p-6">
        <h2 id="modal-title" className="text-lg font-semibold text-slate-900 mb-4">
          {title}
        </h2>
        <div className="text-slate-700 mb-6">{children}</div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
          >
            {cancelLabel}
          </button>
          {onConfirm && confirmLabel && (
            <button
              type="button"
              onClick={onConfirm}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {confirmLabel}
            </button>
          )}
        </div>
      </div>
    </dialog>
  )
}

export default Modal
