import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Building2, Plus, Power, PowerOff, ArrowRightCircle, X, Users as UsersIcon,
  HardDrive, Files, Copy, ExternalLink, Check,
} from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Button from '../components/UI/Button'
import Modal from '../components/UI/Modal'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import {
  listOrganizations,
  createOrganization,
  updateOrganization,
  deactivateOrganization,
  getOrganizationsStats,
} from '../services/api/organizations'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

/** Construye la URL pública de login de una empresa según el host actual. */
function buildTenantUrl(slug) {
  if (typeof window === 'undefined') return `/${slug}/login`
  return `${window.location.origin}/${slug}/login`
}

export default function OrganizationsPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { switchTenant } = useAuth()
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [copiedId, setCopiedId] = useState(null)  // id de la org cuya URL acaba de ser copiada
  const [form, setForm] = useState({
    name: '', slug: '',
    admin_name: '', admin_email: '', admin_password: '',
  })

  const reload = () =>
    getOrganizationsStats()
      .then(setStats)
      .catch((err) => {
        console.error(err)
        toast.error('Error', 'No se pudieron cargar las empresas')
      })
      .finally(() => setLoading(false))

  useEffect(() => { reload() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createOrganization({
        name: form.name,
        slug: form.slug,
        admin_name: form.admin_name || undefined,
        admin_email: form.admin_email || undefined,
        admin_password: form.admin_password || undefined,
      })
      toast.success('Empresa creada', `'${form.name}' está lista para usar`)
      setCreateOpen(false)
      setForm({ name: '', slug: '', admin_name: '', admin_email: '', admin_password: '' })
      reload()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo crear la empresa')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async (org) => {
    try {
      if (org.active) {
        await deactivateOrganization(org.id)
        toast.info('Empresa desactivada', `'${org.name}' está bloqueada`)
      } else {
        await updateOrganization(org.id, { active: true })
        toast.success('Empresa reactivada', `'${org.name}' está habilitada`)
      }
      reload()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo actualizar')
    }
  }

  const handleEnterTenant = (org) => {
    switchTenant(org)
    navigate(`/${org.slug}/documents`)
  }

  const handleCopyUrl = async (org) => {
    const url = buildTenantUrl(org.slug)
    try {
      // navigator.clipboard requiere contexto seguro (https / localhost).
      // En contextos inseguros (LAN sin TLS) cae al fallback con textarea.
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(url)
      } else {
        const ta = document.createElement('textarea')
        ta.value = url
        ta.style.position = 'fixed'
        ta.style.left = '-9999px'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopiedId(org.id)
      toast.success('URL copiada', url)
      setTimeout(() => setCopiedId((id) => (id === org.id ? null : id)), 1800)
    } catch (err) {
      toast.error('No se pudo copiar', 'Intenta copiar manualmente: ' + url)
    }
  }

  const handleOpenUrl = (org) => {
    window.open(buildTenantUrl(org.slug), '_blank', 'noopener,noreferrer')
  }

  return (
    <Layout title="Empresas (Super Admin)">
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm text-[var(--color-text-secondary)]">
          {stats.length} empresa{stats.length !== 1 ? 's' : ''} registrada{stats.length !== 1 ? 's' : ''}
        </p>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus size={14} /> Nueva empresa
        </Button>
      </div>

      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><LoadingSpinner /></div>
        ) : stats.length === 0 ? (
          <EmptyState
            title="Sin empresas"
            description="Crea la primera empresa para comenzar a usar la plataforma."
            icon={<Building2 size={22} />}
            action={
              <Button size="sm" onClick={() => setCreateOpen(true)}>
                <Plus size={13} /> Nueva empresa
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm min-w-[820px]">
            <thead className="bg-[var(--color-bg-surface-2)]">
              <tr className="border-b border-[var(--color-border)]">
                {['Empresa', 'URL de acceso', 'Usuarios', 'Documentos', 'Storage', 'Estado', ''].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-text-muted)] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {stats.map((org) => {
                const url = buildTenantUrl(org.slug)
                return (
                <tr key={org.id} className="hover:bg-[var(--color-bg-surface-2)] transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Building2 size={14} className="text-[var(--color-primary)] shrink-0" />
                      <div className="min-w-0">
                        <span className="block font-medium text-[var(--color-text-primary)] truncate">{org.name}</span>
                        <code className="text-[11px] text-[var(--color-text-muted)]">/{org.slug}</code>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 max-w-[320px]">
                      <code
                        className="flex-1 text-xs px-2 py-1 rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] truncate"
                        title={url}
                      >
                        {url}
                      </code>
                      <button
                        type="button"
                        onClick={() => handleCopyUrl(org)}
                        title={copiedId === org.id ? 'Copiado' : 'Copiar URL'}
                        aria-label="Copiar URL al portapapeles"
                        className="p-1.5 rounded-[var(--radius-md)] transition-colors shrink-0"
                        style={{
                          color: copiedId === org.id ? 'var(--color-success)' : 'var(--color-text-muted)',
                          backgroundColor: 'transparent',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-primary-subtle)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        {copiedId === org.id ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenUrl(org)}
                        title="Abrir en nueva pestaña"
                        aria-label="Abrir URL en nueva pestaña"
                        className="p-1.5 rounded-[var(--radius-md)] transition-colors shrink-0"
                        style={{
                          color: 'var(--color-text-muted)',
                          backgroundColor: 'transparent',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-primary-subtle)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <ExternalLink size={14} />
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                    <span className="inline-flex items-center gap-1.5"><UsersIcon size={12} />{org.users_count}</span>
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                    <span className="inline-flex items-center gap-1.5"><Files size={12} />{org.documents_count}</span>
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                    <span className="inline-flex items-center gap-1.5"><HardDrive size={12} />
                      {org.storage_kb < 1024 ? `${org.storage_kb} KB` : `${(org.storage_kb / 1024).toFixed(1)} MB`}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {org.active ? (
                      <span className="text-xs font-medium" style={{ color: 'var(--color-success)' }}>Activa</span>
                    ) : (
                      <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>Inactiva</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1">
                      <button
                        title="Entrar como super admin a esta empresa"
                        onClick={() => handleEnterTenant(org)}
                        className="p-1.5 rounded-[var(--radius-sm)] hover:bg-[var(--color-primary-subtle)] text-[var(--color-primary)] transition-colors"
                      >
                        <ArrowRightCircle size={15} />
                      </button>
                      <button
                        title={org.active ? 'Desactivar' : 'Reactivar'}
                        onClick={() => handleToggleActive(org)}
                        className="p-1.5 rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
                        style={{ color: org.active ? 'var(--color-error)' : 'var(--color-success)' }}
                      >
                        {org.active ? <PowerOff size={15} /> : <Power size={15} />}
                      </button>
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {/* Modal crear empresa */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Nueva empresa"
      >
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-secondary)]">
              Nombre
            </label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Municipalidad Provincial de Maynas"
              className="mt-1 w-full h-10 px-3 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
            />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-secondary)]">
              Slug (URL)
            </label>
            <input
              required
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
              placeholder="maynas"
              className="mt-1 w-full h-10 px-3 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] font-mono"
            />
            <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">
              La empresa será accesible en /{form.slug || 'slug'}/login
            </p>
          </div>

          <div className="border-t border-[var(--color-border)] pt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-secondary)] mb-2">
              Administrador inicial (opcional)
            </p>
            <div className="flex flex-col gap-3">
              <input
                value={form.admin_name}
                onChange={(e) => setForm({ ...form, admin_name: e.target.value })}
                placeholder="Nombre del administrador"
                className="w-full h-10 px-3 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)]"
              />
              <input
                type="email"
                value={form.admin_email}
                onChange={(e) => setForm({ ...form, admin_email: e.target.value })}
                placeholder="admin@empresa.com"
                className="w-full h-10 px-3 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)]"
              />
              <input
                type="password"
                value={form.admin_password}
                onChange={(e) => setForm({ ...form, admin_password: e.target.value })}
                placeholder="Contraseña (mín. 8 caracteres)"
                className="w-full h-10 px-3 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" loading={saving}>
              Crear empresa
            </Button>
          </div>
        </form>
      </Modal>
    </Layout>
  )
}
