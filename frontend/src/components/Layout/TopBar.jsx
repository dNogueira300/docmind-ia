import { LogOut, ChevronDown, Menu } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import Badge from '../UI/Badge'
import ThemeToggle from '../UI/ThemeToggle'

/**
 * @param {{ title: string, onToggleSidebar: () => void }} props
 */
export default function TopBar({ title, onToggleSidebar }) {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const initial = user?.name?.[0]?.toUpperCase() ?? '?'

  return (
    /* relative + z-10 garantiza que el dropdown (z-20) aparezca
       sobre el contenido scrollable de main */
    <header
      className="h-14 px-4 flex items-center justify-between shrink-0 relative z-10 anim-fade-in"
      style={{
        backgroundColor: 'var(--color-bg-page)',
        boxShadow: '0 1px 0 var(--color-border)',
      }}
    >
      {/* Izquierda: hamburger + título */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded-[var(--radius-md)] transition-colors"
          style={{ color: 'var(--color-text-muted)' }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          aria-label="Toggle sidebar"
        >
          <Menu size={18} />
        </button>

        <h1 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          {title}
        </h1>
      </div>

      {/* Derecha: toggle tema + separador + user */}
      <div className="flex items-center gap-3">
        <ThemeToggle />

        {/* Separador vertical */}
        <span className="h-5 w-px" style={{ backgroundColor: 'var(--color-border)' }} />

        {/* User dropdown */}
        <div className="relative">
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-2 px-2 py-1.5 rounded-[var(--radius-lg)] transition-all duration-150"
            style={{ color: 'var(--color-text-primary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            {/* Avatar */}
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-semibold uppercase shrink-0 transition-transform duration-150 hover:scale-105"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              {initial}
            </div>

            <div className="hidden sm:block text-left">
              <p className="text-sm font-medium leading-none" style={{ color: 'var(--color-text-primary)' }}>
                {user?.name}
              </p>
              <div className="mt-0.5">
                <Badge type="role" value={user?.role} />
              </div>
            </div>

            <ChevronDown
              size={13}
              className="transition-transform duration-200"
              style={{
                color: 'var(--color-text-muted)',
                transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              }}
            />
          </button>

          {open && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
              <div
                className="absolute right-0 top-full mt-1.5 z-20 w-48 rounded-[var(--radius-lg)] py-1 anim-scale-in"
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border)',
                  boxShadow: 'var(--shadow-dropdown)',
                }}
              >
                <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <p className="text-xs font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                    {user?.name}
                  </p>
                  <p className="text-xs truncate mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                    {user?.email}
                  </p>
                </div>
                <button
                  onClick={() => { setOpen(false); logout() }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium transition-colors duration-100"
                  style={{ color: 'var(--color-error)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-error-bg)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <LogOut size={13} />
                  Cerrar sesión
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
