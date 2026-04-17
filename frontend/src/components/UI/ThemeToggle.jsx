import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../context/ThemeContext'

/**
 * Toggle de tema estilo pill.
 * El ícono activo vive DENTRO del knob para que nunca quede tapado.
 *   Light mode → Sol amarillo  (#D97706) en knob
 *   Dark  mode → Luna celeste  (#38BDF8) en knob
 *
 * @param {{ className?: string, showLabel?: boolean }} props
 */
export default function ThemeToggle({ className = '', showLabel = false }) {
  const { isDark, toggleTheme } = useTheme()

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      onClick={toggleTheme}
      title={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      className={`flex items-center gap-2 cursor-pointer select-none ${className}`}
    >
      {/* Etiqueta opcional */}
      {showLabel && (
        <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          {isDark ? 'Dark' : 'Light'}
        </span>
      )}

      {/* Track del pill */}
      <span
        className="relative inline-flex items-center w-11 h-6 rounded-full flex-shrink-0"
        style={{
          backgroundColor: 'var(--color-bg-surface-2)',
          border: '1px solid var(--color-border-light)',
          transition: 'background-color 300ms, border-color 300ms',
        }}
      >
        {/* Knob — lleva el ícono dentro */}
        <span
          className="absolute flex items-center justify-center w-5 h-5 rounded-full bg-white"
          style={{
            transform: isDark ? 'translateX(22px)' : 'translateX(2px)',
            transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 1px 4px rgba(0,0,0,0.25)',
          }}
        >
          {isDark ? (
            /* Luna — celeste */
            <Moon
              size={11}
              strokeWidth={2.5}
              style={{ color: 'var(--color-toggle-moon)' }}
            />
          ) : (
            /* Sol — amarillo */
            <Sun
              size={11}
              strokeWidth={2.5}
              style={{ color: 'var(--color-toggle-sun)' }}
            />
          )}
        </span>
      </span>
    </button>
  )
}
