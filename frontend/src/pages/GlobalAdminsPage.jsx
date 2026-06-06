import { useState, useEffect } from 'react'
import { Plus, Pencil, KeyRound, UserX, UserCheck, MoreVertical, Users } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Modal from '../components/UI/Modal'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import ActionMenu from '../components/UI/ActionMenu'
import {
  getGlobalAdmins,
  createGlobalAdmin,
  updateGlobalAdmin,
  changeGlobalAdminPassword,
  deactivateGlobalAdmin,
  activateGlobalAdmin,
} from '../services/api/users'
import { listOrganizations } from '../services/api/organizations'
import { useToast } from '../context/ToastContext'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-PE', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

const EMPTY_CREATE = { organization_id: '', name: '', email: '', password: '', confirm: '' }
const EMPTY_EDIT   = { name: '', email: '' }
const EMPTY_PASS   = { password: '', confirm: '' }

export default function GlobalAdminsPage() {
  const toast = useToast()

  const [admins, setAdmins] = useState([])
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)

  // Modales
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState(null)       // admin obj
  const [passTarget, setPassTarget] = useState(null)       // admin obj
  const [toggleTarget, setToggleTarget] = useState(null)   // { admin, action: 'deactivate'|'activate' }

  // Formularios
  const [createForm, setCreateForm] = useState(EMPTY_CREATE)
  const [editForm, setEditForm] = useState(EMPTY_EDIT)
  const [passForm, setPassForm] = useState(EMPTY_PASS)

  const [saving, setSaving] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [createError, setCreateError] = useState('')
  const [editError, setEditError] = useState('')
  const [passError, setPassError] = useState('')

  const load = () => {
    Promise.all([getGlobalAdmins(), listOrganizations({ include_inactive: false })])
      .then(([a, o]) => { setAdmins(a); setOrgs(o) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  /* ── Helpers ── */
  const cf = (field) => (e) => setCreateForm((f) => ({ ...f, [field]: e.target.value }))
  const ef = (field) => (e) => setEditForm((f) => ({ ...f, [field]: e.target.value }))
  const pf = (field) => (e) => setPassForm((f) => ({ ...f, [field]: e.target.value }))

  /* ── Crear ── */
  const openCreate = () => { setCreateForm(EMPTY_CREATE); setCreateError(''); setCreateOpen(true) }

  const handleCreate = async () => {
    if (!createForm.organization_id) { setCreateError('Selecciona una empresa'); return }
    if (!createForm.name.trim())     { setCreateError('El nombre es obligatorio'); return }
    if (!createForm.email.trim())    { setCreateError('El email es obligatorio'); return }
    if (createForm.password.length < 8) { setCreateError('La contraseña debe tener al menos 8 caracteres'); return }
    if (createForm.password !== createForm.confirm) { setCreateError('Las contraseñas no coinciden'); return }
    setSaving(true)
    setCreateError('')
    try {
      await createGlobalAdmin({
        organization_id: createForm.organization_id,
        name: createForm.name.trim(),
        email: createForm.email.trim(),
        password: createForm.password,
      })
      toast.success('Admin creado', createForm.name)
      setCreateOpen(false)
      load()
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Error al crear el administrador'
      setCreateError(msg)
      toast.error('Error', msg)
    } finally {
      setSaving(false)
    }
  }

  /* ── Editar ── */
  const openEdit = (admin) => {
    setEditTarget(admin)
    setEditForm({ name: admin.name, email: admin.email })
    setEditError('')
  }

  const handleEdit = async () => {
    if (!editForm.name.trim() && !editForm.email.trim()) {
      setEditError('Ingresa al menos un campo para actualizar')
      return
    }
    setSaving(true)
    setEditError('')
    try {
      const payload = {}
      if (editForm.name.trim() !== editTarget.name)   payload.name  = editForm.name.trim()
      if (editForm.email.trim() !== editTarget.email) payload.email = editForm.email.trim()
      if (Object.keys(payload).length === 0) { setEditTarget(null); return }
      await updateGlobalAdmin(editTarget.id, payload)
      toast.success('Admin actualizado', editForm.name)
      setEditTarget(null)
      load()
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Error al actualizar'
      setEditError(msg)
      toast.error('Error', msg)
    } finally {
      setSaving(false)
    }
  }

  /* ── Contraseña ── */
  const openPassword = (admin) => {
    setPassTarget(admin)
    setPassForm(EMPTY_PASS)
    setPassError('')
  }

  const handlePassword = async () => {
    if (passForm.password.length < 8) { setPassError('Mínimo 8 caracteres'); return }
    if (passForm.password !== passForm.confirm) { setPassError('Las contraseñas no coinciden'); return }
    setSaving(true)
    setPassError('')
    try {
      await changeGlobalAdminPassword(passTarget.id, passForm.password)
      toast.success('Contraseña actualizada', passTarget.name)
      setPassTarget(null)
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Error al cambiar contraseña'
      setPassError(msg)
      toast.error('Error', msg)
    } finally {
      setSaving(false)
    }
  }

  /* ── Activar / Desactivar ── */
  const handleToggle = async () => {
    if (!toggleTarget) return
    setToggling(true)
    try {
      if (toggleTarget.action === 'deactivate') {
        await deactivateGlobalAdmin(toggleTarget.admin.id)
        toast.success('Admin desactivado', toggleTarget.admin.name)
      } else {
        await activateGlobalAdmin(toggleTarget.admin.id)
        toast.success('Admin reactivado', toggleTarget.admin.name)
      }
      setToggleTarget(null)
      load()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo cambiar el estado')
    } finally {
      setToggling(false)
    }
  }

  /* ── Menú de acciones por fila ── */
  const rowMenu = (admin) => [
    { label: 'Editar',           icon: Pencil,    onClick: () => openEdit(admin) },
    { label: 'Cambiar contraseña', icon: KeyRound, onClick: () => openPassword(admin) },
    admin.active
      ? { label: 'Desactivar', icon: UserX,    onClick: () => setToggleTarget({ admin, action: 'deactivate' }), danger: true }
      : { label: 'Reactivar',  icon: UserCheck, onClick: () => setToggleTarget({ admin, action: 'activate' }) },
  ]

  return (
    <Layout title="Administradores de empresas">
      <div className="max-w-4xl mx-auto flex flex-col gap-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            {loading ? '…' : `${admins.length} administrador${admins.length !== 1 ? 'es' : ''}`}
          </p>
          <Button size="sm" onClick={openCreate}>
            <Plus size={14} /> Nuevo admin
          </Button>
        </div>

        {/* Tabla */}
        <div
          className="rounded-[var(--radius-lg)] overflow-hidden"
          style={{
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border)',
          }}
        >
          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : admins.length === 0 ? (
            <EmptyState
              title="Sin administradores"
              description="Crea el primer administrador para una empresa"
              icon={<Users size={22} />}
              action={<Button size="sm" onClick={openCreate}><Plus size={14} /> Nuevo admin</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr
                    className="border-b"
                    style={{
                      borderColor: 'var(--color-border)',
                      backgroundColor: 'var(--color-bg-surface-2)',
                    }}
                  >
                    {['Nombre', 'Email', 'Empresa', 'Estado', 'Creado', ''].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-wide"
                        style={{ color: 'var(--color-text-muted)' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
                  {admins.map((admin) => (
                    <tr
                      key={admin.id}
                      className="group transition-colors"
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                          {admin.name}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        {admin.email}
                      </td>
                      <td className="px-4 py-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>
                        {admin.organization_name ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor: admin.active ? 'var(--color-success-bg)' : 'var(--color-error-bg)',
                            color: admin.active ? 'var(--color-success)' : 'var(--color-error)',
                          }}
                        >
                          {admin.active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {formatDate(admin.created_at)}
                      </td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end">
                          <ActionMenu
                            align="right"
                            items={rowMenu(admin)}
                            trigger={
                              <button
                                className="p-1.5 rounded-[var(--radius-sm)] opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
                                style={{ color: 'var(--color-text-muted)' }}
                                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
                                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                                aria-label="Acciones"
                              >
                                <MoreVertical size={14} />
                              </button>
                            }
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── Modal: crear admin ───────────────────────────── */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Nuevo administrador"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setCreateOpen(false)}>Cancelar</Button>
            <Button size="sm" loading={saving} onClick={handleCreate}>Crear</Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {/* Empresa */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>
              Empresa
            </label>
            <select
              value={createForm.organization_id}
              onChange={cf('organization_id')}
              className="px-3 py-2 text-sm rounded-[var(--radius-md)] border bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <option value="">Seleccionar empresa…</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </div>

          <Input
            label="Nombre completo"
            value={createForm.name}
            onChange={cf('name')}
            placeholder="Ej. María García"
          />
          <Input
            label="Correo electrónico"
            type="email"
            value={createForm.email}
            onChange={cf('email')}
            placeholder="admin@empresa.com"
          />
          <Input
            label="Contraseña"
            type="password"
            value={createForm.password}
            onChange={cf('password')}
            placeholder="Mínimo 8 caracteres"
          />
          <Input
            label="Confirmar contraseña"
            type="password"
            value={createForm.confirm}
            onChange={cf('confirm')}
            placeholder="Repite la contraseña"
            error={createError}
          />
        </div>
      </Modal>

      {/* ── Modal: editar admin ──────────────────────────── */}
      <Modal
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        title={`Editar — ${editTarget?.name ?? ''}`}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setEditTarget(null)}>Cancelar</Button>
            <Button size="sm" loading={saving} onClick={handleEdit}>Guardar cambios</Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Nombre completo"
            value={editForm.name}
            onChange={ef('name')}
            placeholder="Nombre"
          />
          <Input
            label="Correo electrónico"
            type="email"
            value={editForm.email}
            onChange={ef('email')}
            placeholder="Email"
            error={editError}
          />
          {editTarget && (
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Empresa: <span style={{ color: 'var(--color-text-secondary)' }}>{editTarget.organization_name ?? '—'}</span>
            </p>
          )}
        </div>
      </Modal>

      {/* ── Modal: cambiar contraseña ────────────────────── */}
      <Modal
        open={!!passTarget}
        onClose={() => setPassTarget(null)}
        title={`Contraseña — ${passTarget?.name ?? ''}`}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setPassTarget(null)}>Cancelar</Button>
            <Button size="sm" loading={saving} onClick={handlePassword}>Actualizar contraseña</Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Nueva contraseña"
            type="password"
            value={passForm.password}
            onChange={pf('password')}
            placeholder="Mínimo 8 caracteres"
          />
          <Input
            label="Confirmar nueva contraseña"
            type="password"
            value={passForm.confirm}
            onChange={pf('confirm')}
            placeholder="Repite la contraseña"
            error={passError}
          />
        </div>
      </Modal>

      {/* ── Modal: confirmar desactivar / reactivar ──────── */}
      <Modal
        open={!!toggleTarget}
        onClose={() => setToggleTarget(null)}
        title={toggleTarget?.action === 'deactivate' ? 'Desactivar administrador' : 'Reactivar administrador'}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setToggleTarget(null)}>Cancelar</Button>
            <Button
              variant={toggleTarget?.action === 'deactivate' ? 'danger' : 'primary'}
              size="sm"
              loading={toggling}
              onClick={handleToggle}
            >
              {toggleTarget?.action === 'deactivate' ? 'Desactivar' : 'Reactivar'}
            </Button>
          </>
        }
      >
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          {toggleTarget?.action === 'deactivate' ? (
            <>
              ¿Desactivar a{' '}
              <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>
                {toggleTarget?.admin?.name}
              </span>
              ? No podrá iniciar sesión hasta que sea reactivado. Sus datos y documentos se conservan.
            </>
          ) : (
            <>
              ¿Reactivar a{' '}
              <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>
                {toggleTarget?.admin?.name}
              </span>
              ? Volverá a poder iniciar sesión en su empresa.
            </>
          )}
        </p>
      </Modal>
    </Layout>
  )
}
