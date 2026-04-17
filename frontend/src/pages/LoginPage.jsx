import { useState } from 'react'
import {
  Eye, EyeOff, BrainCircuit, AlertCircle,
  FileSearch2, Sparkles, ShieldCheck,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useToast } from '../context/ToastContext'
import ThemeToggle from '../components/UI/ThemeToggle'

const FEATURES = [
  { icon: FileSearch2,  text: 'OCR automático en PDF, JPG y PNG' },
  { icon: Sparkles,     text: 'Clasificación IA con zero-shot NLP' },
  { icon: ShieldCheck,  text: 'Control de acceso por roles' },
]

export default function LoginPage() {
  const { login, loading } = useAuth()
  const { isDark } = useTheme()
  const toast = useToast()
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error,    setError]    = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const result = await login(email, password)
    if (!result.ok) {
      setError(result.error)
      toast.error('Error de autenticación', result.error)
    }
  }

  /* Grid pattern sutil */
  const gridStyle = {
    backgroundImage:
      'linear-gradient(var(--color-brand-panel-grid) 1px, transparent 1px),' +
      'linear-gradient(90deg, var(--color-brand-panel-grid) 1px, transparent 1px)',
    backgroundSize: '40px 40px',
  }

  /* Estilos compartidos para inputs */
  const inputBase = (focused) => ({
    backgroundColor: 'var(--color-bg-surface)',
    border: `1px solid ${focused ? 'var(--color-primary)' : 'var(--color-border)'}`,
    boxShadow: focused ? '0 0 0 3px var(--color-primary-subtle)' : 'none',
    color: 'var(--color-text-primary)',
    outline: 'none',
    transition: 'border-color 150ms, box-shadow 150ms',
  })

  const [emailFocused, setEmailFocused] = useState(false)
  const [passFocused,  setPassFocused]  = useState(false)

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--color-bg-page)' }}>

      {/* Toggle — esquina superior derecha */}
      <div className="absolute top-5 right-6 z-50">
        <ThemeToggle showLabel />
      </div>

      {/* ══ PANEL IZQUIERDO ══════════════════════════════════ */}
      {/*
        Posición: ni pegado al borde izquierdo (px-12) ni centrado (items-center).
        Usamos pl-20 con content max-w-sm alineado a la izquierda del padding.
      */}
      <div
        className="hidden md:flex md:w-[60%] flex-col justify-center pl-20 pr-8 py-16 relative overflow-hidden"
        style={{
          backgroundColor: isDark ? 'var(--color-bg-page)' : 'var(--color-primary)',
          ...gridStyle,
        }}
      >
        {/* Gradiente radial decorativo */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse 55% 45% at 65% 25%, var(--color-brand-panel-glow) 0%, transparent 70%)',
          }}
        />

        <div className="relative z-10 max-w-sm">

          {/* Logo */}
          <div className="flex items-center gap-3 mb-10">
            <div
              className="w-10 h-10 rounded-[var(--radius-lg)] flex items-center justify-center shrink-0"
              style={{ backgroundColor: 'var(--color-brand-icon-bg)' }}
            >
              <BrainCircuit size={22} className="text-white" />
            </div>
            {/* text-lg → text-[19px] (+3pt) */}
            <span className="font-semibold text-white" style={{ fontSize: '19px' }}>
              DocMind IA
            </span>
          </div>

          {/* Headline — text-4xl (36px) → 39px */}
          <h1
            className="font-semibold text-white leading-tight"
            style={{ fontSize: '39px' }}
          >
            Gestiona tu<br />documentación
          </h1>
          <h2
            className="font-semibold leading-tight"
            style={{
              fontSize: '39px',
              color: 'var(--color-brand-headline-accent)',
            }}
          >
            con inteligencia artificial
          </h2>

          {/* Descripción — text-base (16px) → 19px */}
          <p className="mt-4" style={{ fontSize: '19px', color: 'var(--color-brand-text-dim)' }}>
            Digitaliza, clasifica y encuentra documentos institucionales en segundos.
          </p>

          {/* Features — text-sm (14px) → 17px */}
          <ul className="mt-10 flex flex-col gap-4">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <span
                  className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{
                    backgroundColor: 'var(--color-brand-icon-bg)',
                    border: '1px solid var(--color-brand-icon-border)',
                  }}
                >
                  <Icon size={15} style={{ color: 'var(--color-brand-icon-color)' }} />
                </span>
                <span style={{ fontSize: '17px', color: 'var(--color-brand-text-feat)' }}>{text}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ══ PANEL DERECHO — formulario ═══════════════════════ */}
      <div
        className="flex flex-1 items-center justify-center px-8 md:px-12 py-16"
        style={{ backgroundColor: 'var(--color-bg-page)' }}
      >
        <div className="w-full max-w-sm">

          {/* Logo — solo móvil */}
          <div className="flex flex-col items-center mb-8 md:hidden">
            <div
              className="w-10 h-10 rounded-[var(--radius-xl)] flex items-center justify-center mb-2"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              <BrainCircuit size={20} className="text-white" />
            </div>
            <span className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              DocMind IA
            </span>
          </div>

          {/* Encabezado */}
          <h2 className="text-2xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Bienvenido de nuevo
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Inicia sesión en tu espacio de trabajo
          </p>

          {/* Formulario */}
          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">

            {/* Email */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="usuario@institucion.edu.pe"
                required
                autoFocus
                className="w-full h-10 px-3 text-sm rounded-[var(--radius-md)]"
                style={inputBase(emailFocused)}
                onFocus={() => setEmailFocused(true)}
                onBlur={() => setEmailFocused(false)}
              />
            </div>

            {/* Contraseña */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full h-10 px-3 pr-10 text-sm rounded-[var(--radius-md)]"
                  style={inputBase(passFocused)}
                  onFocus={() => setPassFocused(true)}
                  onBlur={() => setPassFocused(false)}
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: 'var(--color-text-muted)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-text-primary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div
                className="flex items-center gap-2 px-3 py-2.5 rounded-[var(--radius-md)] text-xs"
                style={{ backgroundColor: 'var(--color-error-bg)', color: 'var(--color-error)' }}
              >
                <AlertCircle size={14} className="shrink-0" />
                {error}
              </div>
            )}

            {/* Botón submit */}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full h-10 flex items-center justify-center gap-2 text-sm font-medium text-white rounded-[var(--radius-md)] transition-colors duration-150 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--color-primary)' }}
              onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = 'var(--color-primary-hover)' }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-primary)' }}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar sesión'
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="mt-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            UNAP · Gestión de Servicios de TI 2026
          </p>
        </div>
      </div>
    </div>
  )
}
