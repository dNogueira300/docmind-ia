import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Modal from '../components/UI/Modal'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import { getCategories, createCategory, updateCategory, deleteCategory } from '../services/api/categories'
import { getDocuments } from '../services/api/documents'
import { useToast } from '../context/ToastContext'
import { Tag } from 'lucide-react'

const EMPTY_FORM = { name: '', color: '#2563D4', description: '' }

export default function CategoriesPage() {
  const toast = useToast()
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleteDocCount, setDeleteDocCount] = useState(0)
  const [loadingDeleteCount, setLoadingDeleteCount] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const load = () => getCategories().then(setCategories).catch(console.error).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const openCreate = () => { setEditTarget(null); setForm(EMPTY_FORM); setError(''); setModalOpen(true) }
  const openEdit = (cat) => { setEditTarget(cat); setForm({ name: cat.name, color: cat.color, description: cat.description ?? '' }); setError(''); setModalOpen(true) }

  const openDelete = async (cat) => {
    setDeleteTarget(cat)
    setDeleteDocCount(0)
    setLoadingDeleteCount(true)
    try {
      const docs = await getDocuments({ category_id: cat.id, limit: 1000 })
      setDeleteDocCount(Array.isArray(docs) ? docs.length : 0)
    } catch {
      setDeleteDocCount(0)
    } finally {
      setLoadingDeleteCount(false)
    }
  }

  const handleSave = async () => {
    if (!form.name.trim()) { setError('El nombre es obligatorio'); return }
    setSaving(true)
    setError('')
    try {
      if (editTarget) {
        await updateCategory(editTarget.id, form)
        toast.success('Categoría actualizada', 'Los cambios fueron guardados')
      } else {
        await createCategory(form)
        toast.success('Categoría creada', form.name)
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

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteCategory(deleteTarget.id)
      toast.success('Categoría eliminada', 'Los documentos quedaron sin categoría')
      setDeleteTarget(null)
      load()
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Error al eliminar'
      toast.error('Error', msg)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Layout title="Categorías">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <p className="text-xs text-[var(--color-text-muted)]">
            {categories.length} / 10 categorías
          </p>
          <Button size="sm" onClick={openCreate} disabled={categories.length >= 10}>
            <Plus size={14} /> Nueva categoría
          </Button>
        </div>

        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : categories.length === 0 ? (
            <EmptyState
              title="Sin categorías"
              description="Crea la primera categoría para organizar tus documentos"
              icon={<Tag size={22} />}
              action={<Button size="sm" onClick={openCreate}><Plus size={14} /> Crear categoría</Button>}
            />
          ) : (
            <ul className="divide-y divide-[var(--color-border)]">
              {categories.map((cat) => (
                <li key={cat.id} className="flex items-center gap-4 px-4 py-3 hover:bg-[var(--color-bg-surface-2)] transition-colors group">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: cat.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{cat.name}</p>
                    {cat.description && (
                      <p className="text-xs text-[var(--color-text-muted)] truncate">{cat.description}</p>
                    )}
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openEdit(cat)}
                      className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] transition-colors"
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      onClick={() => openDelete(cat)}
                      className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-error-bg)] hover:text-[var(--color-error)] transition-colors"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Modal crear/editar */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editTarget ? 'Editar categoría' : 'Nueva categoría'}
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
            label="Nombre"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Ej. Contratos, Actas, Informes..."
            error={error}
          />
          <Input
            label="Descripción (opcional)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Descripción breve..."
          />
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">
              Color
            </label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={form.color}
                onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))}
                className="w-10 h-10 rounded-[var(--radius-md)] border border-[var(--color-border)] cursor-pointer bg-[var(--color-bg-surface-2)] p-0.5"
              />
              <span className="text-sm font-mono text-[var(--color-text-secondary)]">{form.color}</span>
            </div>
          </div>
        </div>
      </Modal>

      {/* Modal eliminar */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar categoría"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(null)}>Cancelar</Button>
            <Button variant="danger" size="sm" loading={deleting} onClick={handleDelete}>Eliminar</Button>
          </>
        }
      >
        {loadingDeleteCount ? (
          <p className="text-sm text-[var(--color-text-secondary)]">Verificando documentos asociados...</p>
        ) : deleteDocCount > 0 ? (
          <p className="text-sm text-[var(--color-text-secondary)]">
            Esta categoría tiene{' '}
            <span className="font-medium text-[var(--color-text-primary)]">{deleteDocCount} documento{deleteDocCount !== 1 ? 's' : ''} asociado{deleteDocCount !== 1 ? 's' : ''}</span>.
            Al eliminarla, esos documentos quedarán sin categoría. ¿Deseas continuar?
          </p>
        ) : (
          <p className="text-sm text-[var(--color-text-secondary)]">
            ¿Eliminar la categoría{' '}
            <span className="font-medium text-[var(--color-text-primary)]">{deleteTarget?.name}</span>?
          </p>
        )}
      </Modal>
    </Layout>
  )
}
