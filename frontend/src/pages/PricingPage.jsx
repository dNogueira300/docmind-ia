import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Check, X, ArrowRight, BrainCircuit, FileSearch2, Sparkles,
  Search, Bell, ShieldCheck, FileText, Upload,
} from 'lucide-react'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ThemeToggle from '../components/UI/ThemeToggle'
import { getPricing } from '../services/api/pricing'

/* ── Identidad: logo del sistema (mismo ícono del login) ──────────────────── */
function Logo({ size = 22 }) {
  return (
    <div
      className="flex items-center justify-center rounded-[var(--radius-lg)] shrink-0"
      style={{
        width: size + 18,
        height: size + 18,
        background: 'linear-gradient(135deg, var(--color-ai-accent), var(--color-primary))',
      }}
    >
      <BrainCircuit size={size} className="text-white" />
    </div>
  )
}

/* ── Contenido informativo ────────────────────────────────────────────────── */
const FEATURES_INFO = [
  { Icon: FileSearch2, title: 'OCR automático', text: 'Extrae el texto de PDFs e imágenes, incluso documentos escaneados, con soporte para español.' },
  { Icon: Sparkles, title: 'Clasificación con IA', text: 'Cada documento se organiza solo en su categoría. Y si no existe, la IA sugiere crearla.' },
  { Icon: Search, title: 'Búsqueda inteligente', text: 'Encuentra por nombre o contenido, con la línea exacta resaltada y búsqueda semántica.' },
  { Icon: Bell, title: 'Alertas de vencimiento', text: 'Detecta fechas límite, renovaciones y plazos en tus documentos y te avisa a tiempo.' },
  { Icon: BrainCircuit, title: 'Chatbot documental', text: 'Pregunta en lenguaje natural y obtén respuestas basadas en tus propios documentos.' },
  { Icon: ShieldCheck, title: 'Roles y multi-empresa', text: 'Control de acceso por rol (admin, editor, consultor) y aislamiento total entre organizaciones.' },
]

const STEPS = [
  { Icon: Upload, title: 'Sube', text: 'Arrastra tus PDF, JPG o PNG.' },
  { Icon: FileSearch2, title: 'OCR', text: 'Se extrae el texto automáticamente.' },
  { Icon: Sparkles, title: 'Clasifica', text: 'La IA lo categoriza y resume.' },
  { Icon: FileText, title: 'Usa', text: 'Busca, conversa y descarga en Word o PDF.' },
]

/* ── Tarjetas de precios ──────────────────────────────────────────────────── */
const FEATURE_LABELS = {
  ai_classification: 'Auto-clasificación con IA',
  ai_summary: 'Resúmenes automáticos',
  ai_suggestions: 'Sugerencias de categoría',
  chatbot: 'Chatbot documental',
  semantic_search: 'Búsqueda semántica',
}

const storageLabel = (mb) =>
  mb >= 1024 ? `${(mb / 1024).toFixed(mb % 1024 ? 1 : 0)} GB` : `${mb} MB`

function priceLabel(p) {
  if (p.custom_quote) return 'Cotización'
  if (Number(p.price) === 0) return 'Gratis'
  return `${p.currency} ${Number(p.price).toLocaleString('es-PE')}`
}

function Bullet({ on, children }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      {on
        ? <Check size={15} style={{ color: 'var(--color-success)' }} className="shrink-0" />
        : <X size={15} style={{ color: 'var(--color-text-muted)' }} className="shrink-0" />}
      <span style={{ color: on ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }}>
        {children}
      </span>
    </li>
  )
}

function PlanCard({ p }) {
  const highlight = p.highlight
  return (
    <div
      className="relative flex flex-col rounded-[var(--radius-lg)] border p-6 gap-5"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: highlight ? 'var(--color-ai-accent)' : 'var(--color-border)',
        boxShadow: highlight ? '0 0 0 1px var(--color-ai-accent)' : 'none',
      }}
    >
      {highlight && (
        <span
          className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-bold uppercase tracking-wide px-3 py-1 rounded-full"
          style={{ backgroundColor: 'var(--color-ai-accent)', color: '#fff' }}
        >
          Recomendado
        </span>
      )}
      <div>
        <h3 className="text-lg font-bold text-[var(--color-text-primary)]">{p.label}</h3>
        {p.tagline && <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{p.tagline}</p>}
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold text-[var(--color-text-primary)]">{priceLabel(p)}</span>
        {!p.custom_quote && Number(p.price) > 0 && (
          <span className="text-sm text-[var(--color-text-muted)]">{p.period}</span>
        )}
      </div>
      <ul className="flex flex-col gap-2">
        <Bullet on>Hasta {p.limits.max_users} usuarios</Bullet>
        <Bullet on>{storageLabel(p.limits.max_storage_mb)} de almacenamiento</Bullet>
        <Bullet on>Clasificación {p.features.ai_classification ? 'con IA' : 'por código'}</Bullet>
        <Bullet on>Alertas de vencimiento</Bullet>
        <Bullet on={p.limits.ai_credits_per_month > 0}>
          {p.limits.ai_credits_per_month > 0
            ? `${p.limits.ai_credits_per_month.toLocaleString('es-PE')} créditos de IA/mes`
            : 'Sin créditos de IA'}
        </Bullet>
        {Object.entries(FEATURE_LABELS).map(([key, label]) => (
          <Bullet key={key} on={!!p.features[key]}>{label}</Bullet>
        ))}
      </ul>
      <div className="mt-auto pt-2">
        <Link
          to="/login"
          className="flex items-center justify-center gap-1.5 w-full py-2.5 rounded-[var(--radius-md)] text-sm font-medium transition-colors"
          style={{
            backgroundColor: highlight ? 'var(--color-primary)' : 'var(--color-bg-surface-2)',
            color: highlight ? '#fff' : 'var(--color-text-primary)',
          }}
        >
          {p.custom_quote ? 'Contactar ventas' : Number(p.price) === 0 ? 'Comenzar gratis' : `Activar ${p.label}`}
          <ArrowRight size={15} />
        </Link>
      </div>
    </div>
  )
}

/* ── Página ───────────────────────────────────────────────────────────────── */
export default function PricingPage() {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPricing().then(setPlans).catch(console.error).finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg-page)' }}>
      {/* Header */}
      <header className="sticky top-0 z-10 backdrop-blur" style={{ backgroundColor: 'color-mix(in srgb, var(--color-bg-page) 80%, transparent)' }}>
        <div className="flex items-center justify-between px-6 py-3 max-w-6xl mx-auto">
          <div className="flex items-center gap-2.5">
            <Logo size={18} />
            <span className="font-bold text-[var(--color-text-primary)]" style={{ fontFamily: 'var(--font-display)' }}>
              DocMind IA
            </span>
          </div>
          <div className="flex items-center gap-3">
            <a href="#planes" className="hidden sm:inline text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">Planes</a>
            <ThemeToggle />
            <Link to="/login" className="text-sm font-medium px-4 py-2 rounded-[var(--radius-md)]" style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
              Iniciar sesión
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="text-center max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex justify-center mb-5"><Logo size={30} /></div>
        <h1 className="text-3xl sm:text-5xl font-bold text-[var(--color-text-primary)] leading-tight" style={{ fontFamily: 'var(--font-display)' }}>
          Gestión documental inteligente para tu institución
        </h1>
        <p className="text-[var(--color-text-secondary)] mt-5 text-base sm:text-lg max-w-2xl mx-auto">
          DocMind IA digitaliza, clasifica y centraliza tus documentos con OCR e inteligencia
          artificial. Encuentra cualquier documento en segundos y nunca pierdas un vencimiento.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
          <Link to="/login" className="flex items-center gap-1.5 px-5 py-3 rounded-[var(--radius-md)] text-sm font-medium" style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
            Comenzar gratis <ArrowRight size={16} />
          </Link>
          <a href="#planes" className="px-5 py-3 rounded-[var(--radius-md)] text-sm font-medium border" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}>
            Ver planes
          </a>
        </div>
      </section>

      {/* Qué es / Features */}
      <section className="max-w-5xl mx-auto px-6 py-12">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)]" style={{ fontFamily: 'var(--font-display)' }}>
            Todo tu archivo, ordenado por IA
          </h2>
          <p className="text-[var(--color-text-secondary)] mt-2">
            Pensado para instituciones que manejan contratos, resoluciones, informes y más.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES_INFO.map(({ Icon, title, text }) => (
            <div key={title} className="rounded-[var(--radius-lg)] border p-5 flex flex-col gap-2" style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}>
              <div className="w-9 h-9 rounded-[var(--radius-md)] flex items-center justify-center" style={{ backgroundColor: 'var(--color-ai-subtle)' }}>
                <Icon size={18} style={{ color: 'var(--color-ai-accent)' }} />
              </div>
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mt-1">{title}</h3>
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Cómo funciona */}
      <section className="max-w-5xl mx-auto px-6 py-12">
        <h2 className="text-2xl font-bold text-center text-[var(--color-text-primary)] mb-10" style={{ fontFamily: 'var(--font-display)' }}>
          Cómo funciona
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map(({ Icon, title, text }, i) => (
            <div key={title} className="flex flex-col items-center text-center gap-2">
              <div className="relative w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-primary-subtle)' }}>
                <Icon size={20} style={{ color: 'var(--color-primary)' }} />
                <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full text-[10px] font-bold flex items-center justify-center text-white" style={{ backgroundColor: 'var(--color-ai-accent)' }}>{i + 1}</span>
              </div>
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
              <p className="text-xs text-[var(--color-text-muted)]">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Planes */}
      <section id="planes" className="max-w-5xl mx-auto px-6 py-12 scroll-mt-20">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)]" style={{ fontFamily: 'var(--font-display)' }}>
            Planes para cada institución
          </h2>
          <p className="text-[var(--color-text-secondary)] mt-2">
            Empieza gratis y escala cuando lo necesites. Sin permanencia.
          </p>
        </div>
        {loading ? (
          <div className="flex justify-center py-16"><LoadingSpinner /></div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-stretch">
            {plans.map((p) => <PlanCard key={p.plan} p={p} />)}
          </div>
        )}
        <p className="text-center text-xs text-[var(--color-text-muted)] mt-8">
          Los planes de pago se activan con un código de activación. Contáctanos para comprarlo.
        </p>
      </section>

      {/* Footer */}
      <footer className="border-t mt-8" style={{ borderColor: 'var(--color-border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Logo size={14} />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">DocMind IA</span>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">
            UNAP · Gestión de Servicios de TI 2026 · Equipo Error 404
          </p>
        </div>
      </footer>
    </div>
  )
}
