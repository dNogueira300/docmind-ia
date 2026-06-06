import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, ShieldAlert } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Modal from '../components/UI/Modal'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import Badge from '../components/UI/Badge'
import { getRiskRules, createRiskRule, updateRiskRule, deleteRiskRule } from '../services/api/riskRules'
import { getCategories } from '../services/api/categories'
import { useToast } from '../context/ToastContext'

const EMPTY_FORM = {
  name: '',
  description: '',
  risk_level: 'medium',
  keywords: '',
  category_ids: [],
  min_file_size_kb: '',
  active: true,
}

const RISK_LEVEL_OPTIONS = [
  { value: 'low',      label: 'Bajo' },
  { value: 'medium',   label: 'Medio' },
  { value: 'high',     label: 'Alto' },
  { value: 'critical', label: 'Crítico' },
]

export default function RiskRulesPage() {
  const toast = useToast()
  const [rules, setRules] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    Promise.all([getRiskRules(), getCategories()])
      .then(([r, c]) => { setRules(r); setCategories(c) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setError('')
    setModalOpen(true)
  }

  const openEdit = (rule) => {
    setEditTarget(rule)
    setForm({
      name: rule.name,
      description: rule.description ?? '',
      risk_level: rule.risk_level,
      keywords: (rule.keywords ?? []).join(', '),
      category_ids: rule.category_ids ?? [],
      min_file_size_kb: rule.min_file_size_kb ?? '',
      active: rule.active,
    })
    setError('')
    setModalOpen(true)
  }

  const formToPayload = () => ({
    name: form.name.trim(),
    description: form.description.trim() || null,
    risk_level: form.risk_level,
    keywords: form.keywords ? form.keywords.split(',').map((k) => k.trim()).filter(Boolean) : null,
    category_ids: form.category_ids.length ? form.category_ids : null,
    min_file_size_kb: form.min_file_size_kb ? parseInt(form.min_file_size_kb) : null,
    active: form.active,
  })

  const handleSave = async () => {
    if (!form.name.trim()) { setError('El nombre es obligatorio'); return }
    setSaving(true)
    setError('')
    try {
      if (editTarget) {
        await updateRiskRule(editTarget.id, formToPayload())
        toast.success('Regla actualizada', form.name)
      } else {
        await createRiskRule(formToPayload())
        toast.success('Regla creada', form.name)
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
      await deleteRiskRule(deleteTarget.id)
      toast.success('Regla eliminada')
      setDeleteTarget(null)
      load()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo eliminar')
    } finally {
      setDeleting(false)
    }
  }

  const toggleCategory = (id) => {
    setForm((f) => ({
      ...f,
      category_ids: f.category_ids.includes(id)
        ? f.category_ids.filter((c) => c !== id)
        : [...f.category_ids, id],
    }))
  }

  return (
    <Layout title="Reglas de Riesgo">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <p className="text-xs text-[var(--color-text-muted)]">{rules.length} regla{rules.length !== 1 ? 's' : ''} configurada{rules.length !== 1 ? 's' : ''}</p>
          <Button size="sm" onClick={openCreate}>
            <Plus size={14} /> Nueva regla
          </Button>
        </div>

        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : rules.length === 0 ? (
            <EmptyState
              title="Sin reglas de riesgo"
              description="Crea reglas para clasificar documentos por nivel de riesgo"
              icon={<ShieldAlert size={22} />}
              action={<Button size="sm" onClick={openCreate}><Plus size={14} /> Crear regla</Button>}
            />
          ) : (
            <ul className="divide-y divide-[var(--color-border)]">
              {rules.map((rule) => (
                <li key={rule.id} className="flex items-center gap-4 px-4 py-3 hover:bg-[var(--color-bg-surface-2)] transition-colors group">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-[var(--color-text-primary)]">{rule.name}</p>
                      <Badge type="risk" value={rule.risk_level} />
                      {!rule.active && (
                        <span className="text-[10px] text-[var(--color-text-muted)] px-1.5 py-0.5 rounded-full bg-[var(--color-bg-surface-2)]">Inactiva</span>
                      )}
                    </div>
                    {rule.description && (
                      <p className="text-xs text-[var(--color-text-muted)] truncate">{rule.description}</p>
                    )}
                    {rule.keywords?.length > 0 && (
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                        Palabras clave: {rule.keywords.join(', ')}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openEdit(rule)}
                      className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] transition-colors"
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(rule)}
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
        title={editTarget ? 'Editar regla' : 'Nueva regla de riesgo'}
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
          <Input label="Nombre" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Ej. Contratos de alto valor" error={error} />
          <Input label="Descripción (opcional)" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="Descripción breve" />

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">Nivel de riesgo</label>
            <select
              value={form.risk_level}
              onChange={(e) => setForm((f) => ({ ...f, risk_level: e.target.value }))}
              className="px-3 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            >
              {RISK_LEVEL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <Input
            label="Palabras clave (separadas por coma)"
            value={form.keywords}
            onChange={(e) => setForm((f) => ({ ...f, keywords: e.target.value }))}
            placeholder="contrato, convenio, deuda..."
          />

          {categories.length > 0 && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">Categorías (opcional — vacío = todas)</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => toggleCategory(cat.id)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all"
                    style={{
                      backgroundColor: form.category_ids.includes(cat.id) ? 'var(--color-primary-subtle)' : 'var(--color-bg-surface-2)',
                      borderColor: form.category_ids.includes(cat.id) ? 'var(--color-primary)' : 'var(--color-border)',
                      color: form.category_ids.includes(cat.id) ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                    }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cat.color }} />
                    {cat.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <Input
            label="Tamaño mínimo (KB, opcional)"
            type="number"
            value={form.min_file_size_kb}
            onChange={(e) => setForm((f) => ({ ...f, min_file_size_kb: e.target.value }))}
            placeholder="Ej. 500"
          />

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))}
              className="w-4 h-4 rounded accent-[var(--color-primary)]"
            />
            <span className="text-sm text-[var(--color-text-primary)]">Regla activa</span>
          </label>
        </div>
      </Modal>

      {/* Modal eliminar */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar regla"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(null)}>Cancelar</Button>
            <Button variant="danger" size="sm" loading={deleting} onClick={handleDelete}>Eliminar</Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text-secondary)]">
          ¿Eliminar la regla <span className="font-medium text-[var(--color-text-primary)]">{deleteTarget?.name}</span>?
        </p>
      </Modal>
    </Layout>
  )
}
