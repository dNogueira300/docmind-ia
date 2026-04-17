import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react'

const TYPE_CONFIG = {
  success: { icon: CheckCircle2, color: 'var(--color-success)',  bg: 'var(--color-success-bg)'  },
  error:   { icon: XCircle,      color: 'var(--color-error)',    bg: 'var(--color-error-bg)'    },
  warning: { icon: AlertTriangle, color: 'var(--color-warning)', bg: 'var(--color-warning-bg)'  },
  info:    { icon: Info,          color: 'var(--color-primary)', bg: 'var(--color-primary-subtle)' },
}

function ToastItem({ toast, onDismiss }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Pequeño delay para triggear la animación de entrada
    const t = requestAnimationFrame(() => setVisible(true))
    return () => cancelAnimationFrame(t)
  }, [])

  const { icon: Icon, color, bg } = TYPE_CONFIG[toast.type] ?? TYPE_CONFIG.info

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        transform: visible ? 'translateX(0)' : 'translateX(calc(100% + 16px))',
        opacity: visible ? 1 : 0,
        transition: 'transform 250ms cubic-bezier(0.16,1,0.3,1), opacity 200ms ease',
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border)',
        minWidth: '280px',
        maxWidth: '360px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)',
        borderRadius: 'var(--radius-lg)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Banda de color izquierda */}
      <div
        style={{
          position: 'absolute',
          left: 0, top: 0, bottom: 0,
          width: '3px',
          backgroundColor: color,
          borderRadius: 'var(--radius-lg) 0 0 var(--radius-lg)',
        }}
      />

      <div className="flex items-start gap-3 px-4 py-3 pl-5">
        <div
          className="flex items-center justify-center w-7 h-7 rounded-full shrink-0"
          style={{ backgroundColor: bg }}
        >
          <Icon size={14} style={{ color }} />
        </div>

        <div className="flex-1 min-w-0 pr-5">
          <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
            {toast.title}
          </p>
          {toast.message && (
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
              {toast.message}
            </p>
          )}
        </div>
      </div>

      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Cerrar notificación"
        style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          color: 'var(--color-text-muted)',
          padding: '2px',
          borderRadius: 'var(--radius-sm)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-text-primary)')}
        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
      >
        <X size={14} />
      </button>
    </div>
  )
}

/**
 * Contenedor de toasts — renderizado desde ToastProvider.
 * @param {{ toasts: Array, onDismiss: (id: number) => void }} props
 */
export default function Toast({ toasts, onDismiss }) {
  if (!toasts.length) return null

  return (
    <div
      aria-label="Notificaciones"
      style={{
        position: 'fixed',
        top: '16px',
        right: '16px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        alignItems: 'flex-end',
        pointerEvents: 'none',
      }}
    >
      {toasts.map((t) => (
        <div key={t.id} style={{ pointerEvents: 'auto' }}>
          <ToastItem toast={t} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  )
}
