import { useState } from 'react'
import { Sparkles, Check, X, KeyRound } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { usePlan } from '../context/PlanContext'
import { activatePlan } from '../services/api/plan'
import { useToast } from '../context/ToastContext'

const FEATURE_LABELS = {
  ai_classification: 'Auto-clasificación con IA',
  ai_summary: 'Resúmenes automáticos',
  ai_suggestions: 'Sugerencias de categoría',
  chatbot: 'Chatbot documental',
  semantic_search: 'Búsqueda semántica',
}

function UsageBar({ label, used, limit, unit = '' }) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const near = pct >= 85
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs">
        <span className="text-[var(--color-text-secondary)]">{label}</span>
        <span className="text-[var(--color-text-muted)] tabular-nums">
          {used}{unit} / {limit}{unit}
        </span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-bg-surface-2)' }}>
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            backgroundColor: near ? 'var(--color-warning)' : 'var(--color-primary)',
          }}
        />
      </div>
    </div>
  )
}

export default function PlanPage() {
  const { plan, loading, refresh } = usePlan()
  const toast = useToast()
  const [code, setCode] = useState('')
  const [activating, setActivating] = useState(false)

  const handleActivate = async () => {
    if (!code.trim()) return
    setActivating(true)
    try {
      const res = await activatePlan(code.trim())
      toast.success('Plan activado', res.detail)
      setCode('')
      refresh()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'Código inválido')
    } finally {
      setActivating(false)
    }
  }

  return (
    <Layout title="Plan y facturación">
      <div className="max-w-2xl mx-auto flex flex-col gap-5">
        {loading || !plan ? (
          <div className="flex justify-center py-10"><LoadingSpinner /></div>
        ) : (
          <>
            {/* Plan actual */}
            <div
              className="rounded-[var(--radius-lg)] border p-5 flex flex-col gap-2"
              style={{ backgroundColor: 'var(--color-ai-subtle)', borderColor: 'var(--color-ai-accent)' }}
            >
              <div className="flex items-center gap-2">
                <Sparkles size={18} style={{ color: 'var(--color-ai-accent)' }} />
                <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
                  Plan {plan.plan_label}
                </h2>
              </div>
              {plan.plan_expires_at && (
                <p className="text-xs text-[var(--color-text-muted)]">
                  Vigente hasta {new Date(plan.plan_expires_at + 'Z').toLocaleDateString('es-PE')}
                </p>
              )}
            </div>

            {/* Uso */}
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-5 flex flex-col gap-4">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Uso del plan</h3>
              <UsageBar label="Usuarios" used={plan.usage.users} limit={plan.limits.max_users} />
              <UsageBar label="Almacenamiento" used={plan.usage.storage_mb} limit={plan.limits.max_storage_mb} unit=" MB" />
              <UsageBar
                label="Créditos de IA (este mes)"
                used={plan.usage.ai_credits_used}
                limit={plan.limits.ai_credits_per_month}
              />
            </div>

            {/* Features incluidas */}
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-5 flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Funciones incluidas</h3>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(FEATURE_LABELS).map(([key, label]) => {
                  const on = !!plan.features[key]
                  return (
                    <li key={key} className="flex items-center gap-2 text-sm">
                      {on
                        ? <Check size={15} style={{ color: 'var(--color-success)' }} />
                        : <X size={15} style={{ color: 'var(--color-text-muted)' }} />}
                      <span style={{ color: on ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }}>
                        {label}
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>

            {/* Activar con código */}
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-5 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <KeyRound size={15} style={{ color: 'var(--color-primary)' }} />
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                  Activar un plan con código
                </h3>
              </div>
              <p className="text-xs text-[var(--color-text-muted)]">
                ¿Compraste un plan? Ingresa tu código de activación (formato DOCMIND-XXXX-XXXX).
              </p>
              <div className="flex gap-2">
                <Input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="DOCMIND-XXXX-XXXX"
                  className="flex-1"
                />
                <Button onClick={handleActivate} loading={activating} disabled={!code.trim()}>
                  Activar
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
