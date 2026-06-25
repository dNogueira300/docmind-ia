import { useState } from 'react'
import { CheckCircle2, Mail } from 'lucide-react'
import Modal from './Modal'
import Button from './Button'
import Input from './Input'
import { createDemoRequest } from '../../services/api/demoRequests'

const PLAN_LABELS = { free: 'Gratuito', pro: 'Pro', enterprise: 'Enterprise' }

/**
 * Modal del formulario público para solicitar acceso/demo.
 * @param {{ plan: string|null, onClose: () => void }} props
 *   plan: si no es null, el modal está abierto y preselecciona ese plan.
 */
export default function DemoRequestModal({ plan, onClose }) {
  const open = !!plan
  const [form, setForm] = useState({ name: '', email: '', organization_name: '', message: '' })
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const reset = () => {
    setForm({ name: '', email: '', organization_name: '', message: '' })
    setSent(false)
    setError('')
  }

  const close = () => { reset(); onClose() }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.name.trim() || !form.email.trim()) {
      setError('Nombre y correo son obligatorios')
      return
    }
    setSending(true)
    try {
      await createDemoRequest({
        name: form.name.trim(),
        email: form.email.trim(),
        organization_name: form.organization_name.trim() || null,
        plan,
        message: form.message.trim() || null,
      })
      setSent(true)
    } catch (err) {
      setError(err.response?.data?.detail?.[0]?.msg ?? err.response?.data?.detail ?? 'No se pudo enviar la solicitud')
    } finally {
      setSending(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title={sent ? 'Solicitud enviada' : `Solicitar acceso · Plan ${PLAN_LABELS[plan] ?? ''}`}
    >
      {sent ? (
        <div className="flex flex-col items-center text-center gap-3 py-4">
          <CheckCircle2 size={44} style={{ color: 'var(--color-success)' }} />
          <p className="text-sm font-medium text-[var(--color-text-primary)]">
            ¡Listo! Tu solicitud fue enviada.
          </p>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-sm">
            En breve el equipo de DocMind se pondrá en contacto contigo por correo con
            tus accesos de prueba.
          </p>
          <Button className="mt-2" onClick={close}>Entendido</Button>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <p className="text-xs text-[var(--color-text-muted)] flex items-center gap-1.5">
            <Mail size={13} /> Déjanos tus datos y te enviaremos los accesos de prueba.
          </p>
          <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
            Nombre completo *
            <Input value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Tu nombre" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
            Correo electrónico *
            <Input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="tucorreo@ejemplo.com" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
            Organización (opcional)
            <Input value={form.organization_name} onChange={(e) => set('organization_name', e.target.value)} placeholder="Nombre de tu institución" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
            Mensaje (opcional)
            <textarea
              value={form.message}
              onChange={(e) => set('message', e.target.value)}
              rows={3}
              placeholder="Cuéntanos brevemente para qué lo necesitas"
              className="px-3 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            />
          </label>
          {error && (
            <p className="text-xs" style={{ color: 'var(--color-error)' }}>{error}</p>
          )}
          <div className="flex justify-end gap-2 mt-1">
            <Button type="button" variant="ghost" onClick={close}>Cancelar</Button>
            <Button type="submit" loading={sending}>Enviar solicitud</Button>
          </div>
        </form>
      )}
    </Modal>
  )
}
