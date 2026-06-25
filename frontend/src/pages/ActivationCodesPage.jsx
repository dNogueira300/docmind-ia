import { useEffect, useState } from 'react'
import { KeyRound, Plus, Copy, Check } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import { createActivationCodes, listActivationCodes } from '../services/api/plan'
import { useToast } from '../context/ToastContext'

export default function ActivationCodesPage() {
  const toast = useToast()
  const [codes, setCodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ plan: 'pro', duration_days: 365, quantity: 1 })
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(null)

  const load = () =>
    listActivationCodes(false).then(setCodes).catch(console.error).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const created = await createActivationCodes({
        plan: form.plan,
        duration_days: Number(form.duration_days) || 365,
        quantity: Number(form.quantity) || 1,
      })
      toast.success('Códigos generados', `${created.length} código(s) creado(s)`)
      load()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo generar')
    } finally {
      setGenerating(false)
    }
  }

  const copy = (code) => {
    navigator.clipboard?.writeText(code)
    setCopied(code)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <Layout title="Códigos de activación">
      <div className="max-w-3xl mx-auto flex flex-col gap-5">
        {/* Generador */}
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-5 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <KeyRound size={16} style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Generar códigos</h3>
          </div>
          <div className="flex flex-wrap gap-3 items-end">
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Plan
              <select
                value={form.plan}
                onChange={(e) => setForm({ ...form, plan: e.target.value })}
                className="px-3 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
              >
                <option value="pro">Pro</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Duración (días)
              <Input
                type="number"
                value={form.duration_days}
                onChange={(e) => setForm({ ...form, duration_days: e.target.value })}
                className="w-28"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Cantidad
              <Input
                type="number"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                className="w-24"
              />
            </label>
            <Button onClick={handleGenerate} loading={generating}>
              <Plus size={15} /> Generar
            </Button>
          </div>
        </div>

        {/* Lista */}
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : codes.length === 0 ? (
            <EmptyState title="Sin códigos" description="Genera el primer código de activación" icon={<KeyRound size={22} />} />
          ) : (
            <ul className="divide-y divide-[var(--color-border)]">
              {codes.map((c) => (
                <li key={c.id} className="flex items-center gap-3 px-4 py-3">
                  <code className="text-sm font-mono text-[var(--color-text-primary)]">{c.code}</code>
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase"
                    style={{ backgroundColor: 'var(--color-ai-subtle)', color: 'var(--color-ai-accent)' }}
                  >
                    {c.plan}
                  </span>
                  <span className="text-xs text-[var(--color-text-muted)]">{c.duration_days} días</span>
                  <div className="flex-1" />
                  {c.used ? (
                    <span className="text-xs text-[var(--color-text-muted)]">Usado</span>
                  ) : (
                    <button
                      onClick={() => copy(c.code)}
                      className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-primary)] transition-colors"
                      title="Copiar"
                    >
                      {copied === c.code ? <Check size={14} style={{ color: 'var(--color-success)' }} /> : <Copy size={14} />}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Layout>
  )
}
