import { useEffect, useState } from 'react'
import { Files, CheckCircle, Clock, Upload, ArrowRight } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import StatCard from '../components/UI/StatCard'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import Badge from '../components/UI/Badge'
import { getDocuments } from '../services/api/documents'
import { getCategories } from '../services/api/categories'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short' })
}

export default function DashboardPage() {
  const { isEditor } = useAuth()
  const [docs, setDocs] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDocuments({ limit: 50 }),
      getCategories(),
    ]).then(([d, c]) => {
      setDocs(d)
      setCategories(c)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const total      = docs.length
  const classified = docs.filter((d) => d.status === 'classified').length
  const pending    = docs.filter((d) => d.status === 'pending' || d.status === 'review').length
  const recent     = [...docs].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5)

  return (
    <Layout title="Dashboard">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">

        {/* Stats — animación escalonada */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 anim-stagger">
          <StatCard
            label="Total documentos"
            value={loading ? '—' : total}
            icon={<Files size={18} />}
          />
          <StatCard
            label="Clasificados"
            value={loading ? '—' : classified}
            icon={<CheckCircle size={18} />}
            iconBg="var(--color-success-bg)"
            iconColor="var(--color-success)"
            trend={total > 0 ? `${Math.round((classified / total) * 100)}% del total` : undefined}
          />
          <StatCard
            label="Pendientes / Revisión"
            value={loading ? '—' : pending}
            icon={<Clock size={18} />}
            iconBg="var(--color-warning-bg)"
            iconColor="var(--color-warning)"
          />
        </div>

        {/* Acceso rápido — banner con hover lift */}
        {isEditor && (
          <div
            className="card-hover glow-primary-hover rounded-[var(--radius-lg)] p-4 flex items-center justify-between anim-fade-in-up"
            style={{
              backgroundColor: 'var(--color-primary-subtle)',
              border: '1px solid var(--color-primary-border)',
            }}
          >
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--color-primary)' }}>
                Subir nuevo documento
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                PDF, JPG o PNG · hasta 20 MB
              </p>
            </div>
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-white text-sm font-medium transition-all duration-150 hover:-translate-y-px hover:shadow-md active:scale-[0.97]"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              <Upload size={15} />
              Subir
            </Link>
          </div>
        )}

        {/* Documentos recientes */}
        <div
          className="rounded-[var(--radius-lg)] overflow-hidden anim-fade-in-up"
          style={{
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          {/* Header sin borde duro — degradado */}
          <div className="px-5 py-3.5 flex items-center justify-between">
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Documentos recientes
            </h2>
            <Link
              to="/documents"
              className="flex items-center gap-1 text-xs font-medium transition-all duration-150 hover:gap-1.5"
              style={{ color: 'var(--color-primary)' }}
            >
              Ver todos
              <ArrowRight size={12} />
            </Link>
          </div>

          {/* Separador degradado */}
          <div style={{
            height: '1px',
            background: 'linear-gradient(to right, transparent, var(--color-border) 20%, var(--color-border) 80%, transparent)',
          }} />

          {loading ? (
            <div className="flex justify-center py-10">
              <LoadingSpinner />
            </div>
          ) : recent.length === 0 ? (
            <EmptyState
              title="Sin documentos aún"
              description="Sube tu primer documento para comenzar"
            />
          ) : (
            <ul>
              {recent.map((doc, i) => {
                const cat = categories.find((c) => c.id === doc.category_id)
                return (
                  <li
                    key={doc.id}
                    className="anim-fade-in-up"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    {i > 0 && (
                      <div style={{
                        height: '1px',
                        margin: '0 20px',
                        background: 'var(--color-border)',
                        opacity: 0.6,
                      }} />
                    )}
                    <div
                      className="flex items-center gap-4 px-5 py-3 transition-all duration-150 cursor-pointer"
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'
                        e.currentTarget.style.paddingLeft = '22px'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                        e.currentTarget.style.paddingLeft = '20px'
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <p
                          className="text-sm font-medium truncate"
                          style={{ color: 'var(--color-text-primary)' }}
                        >
                          {doc.original_filename}
                        </p>
                        {cat && (
                          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                            {cat.name}
                          </p>
                        )}
                      </div>
                      <Badge type="status" value={doc.status} />
                      <span className="text-xs shrink-0" style={{ color: 'var(--color-text-muted)' }}>
                        {formatDate(doc.created_at)}
                      </span>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </Layout>
  )
}
