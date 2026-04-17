import { useState, useEffect } from 'react'
import { Plus, Pencil, UserCheck, UserX } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Modal from '../components/UI/Modal'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import Badge from '../components/UI/Badge'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import { getUsers, createUser, updateUser } from '../services/api/users'
import { useToast } from '../context/ToastContext'
import { Users } from 'lucide-react'

const EMPTY_FORM = { name: '', email: '', password: '', role: 'consultor' }

export default function UsersPage() {
  const toast = useToast()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = () =>
    getUsers()
      .then(setUsers)
      .catch(console.error)
      .finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setError('')
    setModalOpen(true)
  }

  const openEdit = (u) => {
    setEditTarget(u)
    setForm({ name: u.name, email: u.email, password: '', role: u.role })
    setError('')
    setModalOpen(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { setError('El nombre es obligatorio'); return }
    if (!form.email.trim()) { setError('El email es obligatorio'); return }
    if (!editTarget && !form.password.trim()) { setError('La contraseña es obligatoria'); return }

    setSaving(true)
    setError('')
    try {
      if (editTarget) {
        const updates = { name: form.name, role: form.role }
        if (form.password.trim()) updates.password = form.password
        await updateUser(editTarget.id, updates)
        toast.success('Usuario actualizado')
      } else {
        await createUser(form)
        toast.success('Usuario creado', form.email)
      }
      setModalOpen(false)
      load()
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Error al guardar'
      setError(msg)
      toast.error('Error', msg)
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async (u) => {
    try {
      await updateUser(u.id, { is_active: !u.is_active })
      load()
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <Layout title="Usuarios">
      <div className="max-w-3xl mx-auto flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <p className="text-xs text-[var(--color-text-muted)]">
            {users.length} usuario{users.length !== 1 ? 's' : ''}
          </p>
          <Button size="sm" onClick={openCreate}>
            <Plus size={14} /> Nuevo usuario
          </Button>
        </div>

        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : users.length === 0 ? (
            <EmptyState
              title="Sin usuarios"
              description="Crea el primer usuario del sistema"
              icon={<Users size={22} />}
              action={<Button size="sm" onClick={openCreate}><Plus size={14} /> Crear usuario</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-surface-2)]">
                  {['Nombre', 'Email', 'Rol', 'Estado', ''].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {users.map((u) => (
                  <tr
                    key={u.id}
                    className="hover:bg-[var(--color-bg-surface-2)] transition-colors group"
                  >
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[var(--color-text-primary)]">{u.name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-[var(--color-text-secondary)]">{u.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge type="role" value={u.role} />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full ${
                          u.is_active
                            ? 'bg-[var(--color-success-bg)] text-[var(--color-success)]'
                            : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]'
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-[var(--color-success)]' : 'bg-[var(--color-text-muted)]'}`} />
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity justify-end">
                        <button
                          onClick={() => openEdit(u)}
                          title="Editar"
                          className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] transition-colors"
                        >
                          <Pencil size={13} />
                        </button>
                        <button
                          onClick={() => handleToggleActive(u)}
                          title={u.is_active ? 'Desactivar' : 'Activar'}
                          className={`p-1.5 rounded-[var(--radius-sm)] transition-colors ${
                            u.is_active
                              ? 'text-[var(--color-text-muted)] hover:bg-[var(--color-error-bg)] hover:text-[var(--color-error)]'
                              : 'text-[var(--color-text-muted)] hover:bg-[var(--color-success-bg)] hover:text-[var(--color-success)]'
                          }`}
                        >
                          {u.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                        </button>
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

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editTarget ? 'Editar usuario' : 'Nuevo usuario'}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button size="sm" loading={saving} onClick={handleSave}>
              {editTarget ? 'Guardar cambios' : 'Crear'}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Nombre completo"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Ej. María García"
            error={error && error.toLowerCase().includes('nombre') ? error : ''}
          />
          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            placeholder="usuario@institución.edu.pe"
            disabled={!!editTarget}
            error={error && error.toLowerCase().includes('email') ? error : ''}
          />
          <Input
            label={editTarget ? 'Nueva contraseña (dejar en blanco para no cambiar)' : 'Contraseña'}
            type="password"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            placeholder={editTarget ? 'Sin cambios' : 'Mínimo 8 caracteres'}
            error={error && error.toLowerCase().includes('contraseña') ? error : ''}
          />
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">
              Rol
            </label>
            <select
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              className="px-3 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-[var(--color-primary)]"
            >
              <option value="consultor">Consultor — solo lectura</option>
              <option value="editor">Editor — puede subir y reclasificar</option>
              <option value="admin">Administrador — acceso completo</option>
            </select>
          </div>
          {error && !error.toLowerCase().includes('nombre') && !error.toLowerCase().includes('email') && !error.toLowerCase().includes('contraseña') && (
            <p className="text-xs text-[var(--color-error)]">{error}</p>
          )}
        </div>
      </Modal>
    </Layout>
  )
}
