import { useState, useRef, useEffect, useLayoutEffect, cloneElement } from 'react'
import { createPortal } from 'react-dom'

/**
 * Menú de acciones reutilizable que se renderiza en un portal (document.body)
 * para evitar que sea recortado por contenedores con overflow:hidden.
 *
 * Características:
 *   - Renderiza en portal → nunca queda cortado por tablas, tarjetas, modales.
 *   - Auto-flip vertical: si no hay espacio abajo, se abre hacia arriba.
 *   - Auto-flip horizontal: si se sale por la derecha, se ajusta a la izquierda.
 *   - Click fuera o tecla Escape → cierra.
 *   - Se re-posiciona en scroll/resize mientras está abierto.
 *
 * Uso:
 *   <ActionMenu
 *     trigger={<button>···</button>}
 *     items={[
 *       { label: 'Ver',       icon: Eye,      onClick: () => ... },
 *       { label: 'Eliminar',  icon: Trash2,   onClick: () => ..., danger: true },
 *     ]}
 *   />
 */
export default function ActionMenu({
  trigger,
  items = [],
  align = 'right',          // 'right' | 'left' — alineación preferida horizontal
  width = 176,              // ancho del menú en px (w-44 = 176px)
}) {
  const [open, setOpen] = useState(false)
  const [coords, setCoords] = useState({ top: 0, left: 0, placement: 'bottom' })
  const triggerRef = useRef(null)
  const menuRef = useRef(null)

  const recompute = () => {
    const el = triggerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const menuHeight = items.length * 32 + 8  // ~32px por item + padding vertical
    const margin = 6
    const viewportH = window.innerHeight
    const viewportW = window.innerWidth

    // Vertical: si no entra abajo, abre arriba
    const spaceBelow = viewportH - rect.bottom
    const placeBelow = spaceBelow >= menuHeight + margin || rect.top < menuHeight + margin
    const top = placeBelow
      ? rect.bottom + margin
      : rect.top - menuHeight - margin

    // Horizontal: alinear a derecha o izquierda según preferencia y espacio
    let left
    if (align === 'right') {
      left = rect.right - width
      if (left < 8) left = rect.left  // se sale por la izquierda → realinear
    } else {
      left = rect.left
      if (left + width > viewportW - 8) left = rect.right - width
    }
    left = Math.max(8, Math.min(left, viewportW - width - 8))

    setCoords({ top, left, placement: placeBelow ? 'bottom' : 'top' })
  }

  // Re-calcular en cada apertura y en scroll/resize mientras esté abierto
  useLayoutEffect(() => {
    if (!open) return
    recompute()
    const onScroll = () => recompute()
    const onResize = () => recompute()
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('scroll', onScroll, true)
      window.removeEventListener('resize', onResize)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // Click fuera + Escape
  useEffect(() => {
    if (!open) return
    const onDown = (e) => {
      if (
        menuRef.current && !menuRef.current.contains(e.target) &&
        triggerRef.current && !triggerRef.current.contains(e.target)
      ) {
        setOpen(false)
      }
    }
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const handleTriggerClick = (e) => {
    e.stopPropagation()
    setOpen((v) => !v)
  }

  // Inyectar onClick + ref en el trigger sin obligar al consumidor a usar forwardRef.
  // Renderizamos el trigger envuelto en un span con ref.
  return (
    <>
      <span
        ref={triggerRef}
        onClick={handleTriggerClick}
        className="inline-flex"
      >
        {trigger}
      </span>

      {open && createPortal(
        <div
          ref={menuRef}
          role="menu"
          style={{
            position: 'fixed',
            top: coords.top,
            left: coords.left,
            width,
            zIndex: 9999,
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
            padding: '4px 0',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {items.map((item, idx) => (
            <button
              key={idx}
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                if (item.disabled) return
                setOpen(false)
                item.onClick?.()
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium transition-colors duration-100 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                color: item.danger ? 'var(--color-error)' : 'var(--color-text-secondary)',
                backgroundColor: 'transparent',
              }}
              onMouseEnter={(e) => {
                if (item.disabled) return
                e.currentTarget.style.backgroundColor = item.danger
                  ? 'var(--color-error-bg)'
                  : 'var(--color-bg-surface-2)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent'
              }}
            >
              {item.icon && <item.icon size={13} className="shrink-0" />}
              <span className="truncate text-left">{item.label}</span>
            </button>
          ))}
        </div>,
        document.body,
      )}
    </>
  )
}
