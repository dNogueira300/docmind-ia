import { useEffect, useState } from 'react'
import {
  Files, CheckCircle, Clock, Upload, ArrowRight,
  Bell, ShieldAlert, ThumbsUp,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import StatCard from '../components/UI/StatCard'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import Badge from '../components/UI/Badge'
import AlertCard from '../components/UI/AlertCard'
import { getDocuments, getStatsByRisk } from '../services/api/documents'
import { getCategories } from '../services/api/categories'
import { getAlerts } from '../services/api/alerts'
import { getApprovals } from '../services/api/approvals'
import { useAuth } from '../context/AuthContext'

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short' })
}

const RISK_ORDER = ['critical', 'high', 'medium', 'low']
const RISK_COLORS = {
  critical: 'var(--color-error)',
  high:     'rgba(245,88,88,0.7)',
  medium:   'var(--color-warning)',
  low:      'var(--color-text-muted)',
}
const RISK_LABELS = { critical: 'Crítico', high: 'Alto', medium: 'Medio', low: 'Bajo' }

export default function DashboardPage() {
  const { isEditor, isAdmin, tenantSlug } = useAuth()
  const link = (p) => tenantSlug ? `/${tenantSlug}/${p}` : `/${p}`

  const [docs, setDocs] = useState([])
  const [categories, setCategories] = useState([])
  const [alerts, setAlerts] = useState([])
  const [approvals, setApprovals] = useState([])
  const [riskStats, setRiskStats] = useState([])
  const [loading, setLoading] = useState(true)

  const loadData = () => {
    const fetches = [
      getDocuments({ limit: 50 }),
      getCategories(),
    ]
    if (isEditor) fetches.push(getAlerts({ status: 'pending', limit: 5 }))
    if (isEditor) fetches.push(getApprovals({ status: 'pending', limit: 5 }))
    if (isAdmin) fetches.push(getStatsByRisk())

    Promise.allSettled(fetches).then((results) => {
      setDocs(results[0].value ?? [])
      setCategories(results[1].value ?? [])
      if (isEditor) setAlerts(results[2]?.value ?? [])
      if (isEditor) setApprovals(results[3]?.value ?? [])
      if (isAdmin) setRiskStats(results[isEditor ? 4 : 2]?.value ?? [])
    }).finally(() => setLoading(false))
  }

  useEffect(() => { loadData() }, []) // eslint-disable-line

  const total      = docs.length
  const classified = docs.filter((d) => d.status === 'classified').length
  const pending    = docs.filter((d) => ['pending', 'review', 'pending_approval'].includes(d.status)).length
  const recent     = [...docs].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5)

  const riskMap = Object.fromEntries(riskStats.map((r) => [r.risk_level, r.count]))

  return (
    <Layout title="Dashboard">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 anim-stagger">
          <StatCard label="Total documentos" value={loading ? '—' : total} icon={<Files size={18} />} />
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

        {/* Upload rápido */}
        {isEditor && (
          <div
            className="card-hover glow-primary-hover rounded-[var(--radius-lg)] p-4 flex items-center justify-between anim-fade-in-up"
            style={{ backgroundColor: 'var(--color-primary-subtle)', border: '1px solid var(--color-primary-border)' }}
          >
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--color-primary)' }}>Subir nuevo documento</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>PDF, JPG o PNG · hasta 20 MB</p>
            </div>
            <Link
              to={link('upload')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-white text-sm font-medium transition-all duration-150 hover:-translate-y-px hover:shadow-md active:scale-[0.97]"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              <Upload size={15} /> Subir
            </Link>
          </div>
        )}

        {/* Alertas de vencimiento — siempre visible para editores */}
        {isEditor && (
          <div
            className="rounded-[var(--radius-lg)] overflow-hidden anim-fade-in-up"
            style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-card)' }}
          >
            {/* Header */}
            <div className="px-5 py-3.5 flex items-center gap-2">
              <Bell size={15} style={{ color: alerts.length > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)' }} />
              <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                Alertas de vencimiento
              </h2>
              {alerts.length > 0 ? (
                <span
                  className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: 'var(--color-warning-bg)', color: 'var(--color-warning)' }}
                >
                  {alerts.length}
                </span>
              ) : (
                <span
                  className="ml-auto text-xs px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: 'var(--color-success-bg)', color: 'var(--color-success)' }}
                >
                  Sin pendientes
                </span>
              )}
            </div>
            <div style={{ height: 1, background: 'linear-gradient(to right, transparent, var(--color-border) 20%, var(--color-border) 80%, transparent)' }} />

            {alerts.length === 0 ? (
              /* Estado vacío */
              <div className="px-5 py-4 flex items-center gap-3">
                <Bell size={18} style={{ color: 'var(--color-text-muted)', opacity: 0.4 }} />
                <div>
                  <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    No hay documentos próximos a vencer.
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                    Las alertas se generan automáticamente cuando el OCR detecta fechas como
                    "vence el", "válido hasta" o "fecha límite" en los documentos procesados.
                  </p>
                </div>
              </div>
            ) : (
              /* Lista de alertas */
              <div className="p-4 flex flex-col gap-2">
                {alerts.map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onDismissed={() => setAlerts((prev) => prev.filter((a) => a.id !== alert.id))}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Pendientes de aprobación */}
        {isEditor && approvals.length > 0 && (
          <div
            className="rounded-[var(--radius-lg)] overflow-hidden anim-fade-in-up"
            style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-card)' }}
          >
            <div className="px-5 py-3.5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ThumbsUp size={15} style={{ color: 'var(--color-primary)' }} />
                <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                  Pendientes de aprobación
                </h2>
              </div>
              <Link
                to={link('documents') + '?status=pending_approval'}
                className="text-xs font-medium flex items-center gap-1 hover:gap-1.5 transition-all"
                style={{ color: 'var(--color-primary)' }}
              >
                Ver todos <ArrowRight size={11} />
              </Link>
            </div>
            <div style={{ height: 1, background: 'linear-gradient(to right, transparent, var(--color-border) 20%, var(--color-border) 80%, transparent)' }} />
            <ul className="divide-y divide-[var(--color-border)]">
              {approvals.map((appr) => (
                <li key={appr.id} className="px-5 py-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                      Documento #{appr.document_id.slice(0, 8)}…
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      Solicitado: {formatDate(appr.requested_at)}
                    </p>
                  </div>
                  <Badge type="status" value="pending_approval" />
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Mapa de riesgo */}
        {isAdmin && riskStats.length > 0 && (
          <div
            className="rounded-[var(--radius-lg)] overflow-hidden anim-fade-in-up"
            style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-card)' }}
          >
            <div className="px-5 py-3.5 flex items-center gap-2">
              <ShieldAlert size={15} style={{ color: 'var(--color-ai-accent)' }} />
              <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                Mapa de riesgo
              </h2>
            </div>
            <div style={{ height: 1, background: 'linear-gradient(to right, transparent, var(--color-border) 20%, var(--color-border) 80%, transparent)' }} />
            <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {RISK_ORDER.map((level) => (
                <div
                  key={level}
                  className="flex flex-col items-center gap-1 p-3 rounded-[var(--radius-md)]"
                  style={{ backgroundColor: 'var(--color-bg-surface-2)' }}
                >
                  <span className="text-2xl font-bold" style={{ color: RISK_COLORS[level] }}>
                    {riskMap[level] ?? 0}
                  </span>
                  <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                    {RISK_LABELS[level]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Documentos recientes */}
        <div
          className="rounded-[var(--radius-lg)] overflow-hidden anim-fade-in-up"
          style={{ backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-card)' }}
        >
          <div className="px-5 py-3.5 flex items-center justify-between">
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Documentos recientes
            </h2>
            <Link
              to={link('documents')}
              className="flex items-center gap-1 text-xs font-medium transition-all duration-150 hover:gap-1.5"
              style={{ color: 'var(--color-primary)' }}
            >
              Ver todos <ArrowRight size={12} />
            </Link>
          </div>
          <div style={{ height: 1, background: 'linear-gradient(to right, transparent, var(--color-border) 20%, var(--color-border) 80%, transparent)' }} />

          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : recent.length === 0 ? (
            <EmptyState title="Sin documentos aún" description="Sube tu primer documento para comenzar" />
          ) : (
            <ul>
              {recent.map((doc, i) => {
                const cat = categories.find((c) => c.id === doc.category_id)
                return (
                  <li key={doc.id} className="anim-fade-in-up" style={{ animationDelay: `${i * 50}ms` }}>
                    {i > 0 && <div style={{ height: 1, margin: '0 20px', background: 'var(--color-border)', opacity: 0.6 }} />}
                    <div
                      className="flex items-center gap-4 px-5 py-3 transition-all duration-150 cursor-pointer"
                      onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'; e.currentTarget.style.paddingLeft = '22px' }}
                      onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.paddingLeft = '20px' }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                          {doc.original_filename}
                        </p>
                        {doc.ai_summary ? (
                          <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>{doc.ai_summary}</p>
                        ) : cat && (
                          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{cat.name}</p>
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
