import { useEffect, useState } from 'react'
import { Tag, Save, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { getPricing, updatePricing } from '../services/api/pricing'
import { useToast } from '../context/ToastContext'

function PlanEditor({ plan, onSaved }) {
  const toast = useToast()
  const [form, setForm] = useState({
    price: plan.price,
    currency: plan.currency,
    period: plan.period,
    tagline: plan.tagline ?? '',
    highlight: plan.highlight,
    custom_quote: plan.custom_quote,
  })
  const [saving, setSaving] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const save = async () => {
    setSaving(true)
    try {
      await updatePricing(plan.plan, {
        price: Number(form.price) || 0,
        currency: form.currency,
        period: form.period,
        tagline: form.tagline,
        highlight: form.highlight,
        custom_quote: form.custom_quote,
      })
      toast.success('Precio actualizado', plan.label)
      onSaved?.()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{plan.label}</h3>
        <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full"
          style={{ backgroundColor: 'var(--color-bg-surface-2)', color: 'var(--color-text-muted)' }}>
          {plan.plan}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
          Precio
          <Input type="number" value={form.price} onChange={(e) => set('price', e.target.value)} disabled={form.custom_quote} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
          Moneda
          <Input value={form.currency} onChange={(e) => set('currency', e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
          Periodo
          <Input value={form.period} onChange={(e) => set('period', e.target.value)} />
        </label>
      </div>

      <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
        Eslogan (subtítulo en la tarjeta)
        <Input value={form.tagline} onChange={(e) => set('tagline', e.target.value)} placeholder="Ej. El más popular" />
      </label>

      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm cursor-pointer text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={form.highlight} onChange={(e) => set('highlight', e.target.checked)} className="accent-[var(--color-ai-accent)]" />
          Recomendado
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={form.custom_quote} onChange={(e) => set('custom_quote', e.target.checked)} className="accent-[var(--color-ai-accent)]" />
          Mostrar "Cotización" (sin precio)
        </label>
      </div>

      <div className="flex justify-end">
        <Button size="sm" onClick={save} loading={saving}>
          <Save size={14} /> Guardar
        </Button>
      </div>
    </div>
  )
}

export default function PricingAdminPage() {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => getPricing().then(setPlans).catch(console.error).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  return (
    <Layout title="Precios de la landing">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <p className="text-xs text-[var(--color-text-muted)]">
            Ajusta los precios que se muestran en la página pública.
          </p>
          <Link
            to="/pricing"
            target="_blank"
            className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-primary)]"
          >
            Ver página pública <ExternalLink size={13} />
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-10"><LoadingSpinner /></div>
        ) : (
          plans.map((p) => <PlanEditor key={p.plan} plan={p} onSaved={load} />)
        )}
      </div>
    </Layout>
  )
}
