import { useEffect } from 'react'
import { X } from 'lucide-react'
import clsx from 'clsx'

/**
 * @param {{ open: boolean, onClose: () => void, title: string, children, footer?, size?: 'sm'|'md'|'lg' }} props
 */
export default function Modal({ open, onClose, title, children, footer, size = 'md' }) {
  // Cerrar con Escape
  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const sizes = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg' }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={clsx(
          'relative w-full bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)]',
          'border border-[var(--color-border)] shadow-lg',
          sizes[size]
        )}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        {/* Body */}
        <div className="px-5 py-4">{children}</div>
        {/* Footer */}
        {footer && (
          <div className="flex justify-end gap-2 px-5 py-4 border-t border-[var(--color-border)]">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
