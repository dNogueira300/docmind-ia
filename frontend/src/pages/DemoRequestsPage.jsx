import { useEffect, useState } from 'react'
import { Inbox, Mail, Copy, Check, Send, Building2 } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Button from '../components/UI/Button'
import Input from '../components/UI/Input'
import Modal from '../components/UI/Modal'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import { listDemoRequests, respondDemoRequest } from '../services/api/demoRequests'
import { createOrganization } from '../services/api/organizations'
import { useToast } from '../context/ToastContext'
import { formatDateTime } from '../utils/datetime'

const PLAN_LABELS = { free: 'Gratuito', pro: 'Pro', enterprise: 'Enterprise' }

/** Convierte un nombre en un slug válido (a-z, 0-9, guiones). */
function slugify(text) {
  return (text || '')
    .normalize('NFKD').replace(/\p{Diacritic}/gu, '')   // quitar acentos
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')                          // no alfanumérico → guion
    .replace(/^-+|-+$/g, '')                              // sin guiones al borde
    .slice(0, 50) || 'empresa'
}

/** Genera una contraseña temporal legible (>= 8 chars). */
function genPassword() {
  const a = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
  const b = 'abcdefghijkmnpqrstuvwxyz'
  const d = '23456789'
  const pick = (s, n) => Array.from({ length: n }, () => s[Math.floor(Math.random() * s.length)]).join('')
  return `${pick(a, 2)}${pick(b, 4)}${pick(d, 3)}!`
}

/** Arma el mensaje de respuesta con los accesos de la empresa creada. */
function buildAccessMessage({ req, orgName, slug, adminEmail, password }) {
  const url = `${window.location.origin}/${slug}/login`
  const lines = [
    `Hola ${req.name},`,
    '',
    `¡Bienvenido a DocMind IA! Creamos la cuenta de tu organización "${orgName}".`,
    '',
    `Ingresa aquí: ${url}`,
    `Usuario administrador: ${adminEmail}`,
    `Contraseña temporal: ${password}`,
  ]
  if (req.plan !== 'free') {
    lines.push('', `Tu plan ${PLAN_LABELS[req.plan] ?? req.plan} se activa con el código de activación que te compartimos (sección "Plan" de tu panel).`)
  }
  lines.push('', 'Te recomendamos cambiar la contraseña tras iniciar sesión.', '', '— Equipo DocMind')
  return lines.join('\n')
}

function defaultMessage(req) {
  return (
    `Hola ${req.name},\n\n` +
    `Gracias por tu interés en DocMind IA. Hemos habilitado tu acceso de prueba al plan ` +
    `${PLAN_LABELS[req.plan] ?? req.plan}.\n\n` +
    `Ingresa a la plataforma y, en la sección "Plan", canjea el código de activación que te ` +
    `compartimos. Si tienes dudas, responde a este correo.\n\n` +
    `— Equipo DocMind`
  )
}

function StatusBadge({ status }) {
  const responded = status === 'responded'
  return (
    <span
      className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase"
      style={{
        backgroundColor: responded ? 'var(--color-success-bg)' : 'var(--color-warning-bg)',
        color: responded ? 'var(--color-success)' : 'var(--color-warning)',
      }}
    >
      {responded ? 'Respondida' : 'Pendiente'}
    </span>
  )
}

export default function DemoRequestsPage() {
  const toast = useToast()
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [target, setTarget] = useState(null)        // solicitud a responder
  const [form, setForm] = useState({ message: '', generate_code: true, duration_days: 30 })
  const [sending, setSending] = useState(false)
  const [copied, setCopied] = useState(null)

  // Crear empresa desde una solicitud
  const [orgTarget, setOrgTarget] = useState(null)
  const [orgForm, setOrgForm] = useState(null)
  const [creating, setCreating] = useState(false)

  const load = () => listDemoRequests().then(setRequests).catch(console.error).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const openCreateOrg = (req) => {
    const orgName = req.organization_name || req.name
    setOrgTarget(req)
    setOrgForm({
      name: orgName,
      slug: slugify(orgName),
      admin_name: req.name,
      admin_email: req.email,
      admin_password: genPassword(),
    })
  }

  const submitCreateOrg = async () => {
    setCreating(true)
    try {
      // 1) Crear la empresa + su admin
      await createOrganization({
        name: orgForm.name.trim(),
        slug: orgForm.slug.trim(),
        admin_name: orgForm.admin_name.trim() || undefined,
        admin_email: orgForm.admin_email.trim() || undefined,
        admin_password: orgForm.admin_password || undefined,
      })
      // 2) Responder la solicitud con los accesos (y código si es plan de pago)
      const message = buildAccessMessage({
        req: orgTarget,
        orgName: orgForm.name.trim(),
        slug: orgForm.slug.trim(),
        adminEmail: orgForm.admin_email.trim(),
        password: orgForm.admin_password,
      })
      await respondDemoRequest(orgTarget.id, {
        message,
        generate_code: orgTarget.plan !== 'free',
        plan: orgTarget.plan,
        duration_days: 30,
      })
      toast.success('Empresa creada', 'Accesos generados y solicitud respondida')
      setOrgTarget(null)
      setOrgForm(null)
      load()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo crear la empresa')
    } finally {
      setCreating(false)
    }
  }

  const openRespond = (req) => {
    setTarget(req)
    setForm({ message: defaultMessage(req), generate_code: req.plan !== 'free', duration_days: 30 })
  }

  const send = async () => {
    setSending(true)
    try {
      await respondDemoRequest(target.id, {
        message: form.message.trim(),
        generate_code: form.generate_code,
        plan: target.plan,
        duration_days: Number(form.duration_days) || 30,
      })
      toast.success('Respuesta registrada', 'Se simuló el envío del correo')
      setTarget(null)
      load()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo responder')
    } finally {
      setSending(false)
    }
  }

  const copy = (text) => {
    navigator.clipboard?.writeText(text)
    setCopied(text)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <Layout title="Solicitudes de demo">
      <div className="max-w-3xl mx-auto flex flex-col gap-4">
        <p className="text-xs text-[var(--color-text-muted)]">
          Solicitudes de acceso enviadas desde la página pública. Responde para generar el
          código de acceso (el envío de correo se implementará más adelante).
        </p>

        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-10"><LoadingSpinner /></div>
          ) : requests.length === 0 ? (
            <EmptyState title="Sin solicitudes" description="Aún no hay solicitudes de demo" icon={<Inbox size={22} />} />
          ) : (
            <ul className="divide-y divide-[var(--color-border)]">
              {requests.map((r) => (
                <li key={r.id} className="px-4 py-3 flex flex-col gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">{r.name}</span>
                    <span className="text-xs text-[var(--color-text-muted)]">·</span>
                    <a href={`mailto:${r.email}`} className="text-xs text-[var(--color-primary)] flex items-center gap-1">
                      <Mail size={12} /> {r.email}
                    </a>
                    <span
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase"
                      style={{ backgroundColor: 'var(--color-ai-subtle)', color: 'var(--color-ai-accent)' }}
                    >
                      {PLAN_LABELS[r.plan] ?? r.plan}
                    </span>
                    <StatusBadge status={r.status} />
                    <div className="flex-1" />
                    <span className="text-[11px] text-[var(--color-text-muted)]">{formatDateTime(r.created_at)}</span>
                  </div>

                  {r.organization_name && (
                    <p className="text-xs text-[var(--color-text-secondary)]">Organización: {r.organization_name}</p>
                  )}
                  {r.message && (
                    <p className="text-xs text-[var(--color-text-muted)] italic">“{r.message}”</p>
                  )}

                  {r.status === 'responded' ? (
                    <div className="flex flex-col gap-1.5 mt-1 p-2.5 rounded-[var(--radius-md)]" style={{ backgroundColor: 'var(--color-bg-surface-2)' }}>
                      <p className="text-[11px] text-[var(--color-text-muted)] whitespace-pre-line">{r.response_message}</p>
                      {r.activation_code && (
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono text-[var(--color-text-primary)]">{r.activation_code}</code>
                          <button onClick={() => copy(r.activation_code)} className="text-[var(--color-text-muted)] hover:text-[var(--color-primary)]" title="Copiar código">
                            {copied === r.activation_code ? <Check size={13} style={{ color: 'var(--color-success)' }} /> : <Copy size={13} />}
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => openRespond(r)}>
                        <Send size={13} /> Solo responder
                      </Button>
                      <Button size="sm" onClick={() => openCreateOrg(r)}>
                        <Building2 size={13} /> Crear empresa
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Modal responder */}
      <Modal
        open={!!target}
        onClose={() => setTarget(null)}
        title={target ? `Responder a ${target.name}` : ''}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setTarget(null)}>Cancelar</Button>
            <Button size="sm" loading={sending} onClick={send}>
              <Send size={14} /> Enviar (simulado)
            </Button>
          </>
        }
      >
        {target && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-[var(--color-text-muted)]">
              Plan solicitado: <strong>{PLAN_LABELS[target.plan] ?? target.plan}</strong> · {target.email}
            </p>
            {target.plan !== 'free' && (
              <div className="flex items-center gap-4 flex-wrap">
                <label className="flex items-center gap-2 text-sm cursor-pointer text-[var(--color-text-secondary)]">
                  <input type="checkbox" checked={form.generate_code} onChange={(e) => setForm({ ...form, generate_code: e.target.checked })} className="accent-[var(--color-ai-accent)]" />
                  Generar código de activación
                </label>
                {form.generate_code && (
                  <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                    Duración (días)
                    <Input type="number" value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: e.target.value })} className="w-24" />
                  </label>
                )}
              </div>
            )}
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Mensaje (simula el correo)
              <textarea
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                rows={7}
                className="px-3 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </label>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              El código se generará al enviar y se mostrará en la solicitud para que lo
              compartas manualmente. (El envío de correo aún no está implementado.)
            </p>
          </div>
        )}
      </Modal>

      {/* Modal crear empresa (prellenado con la solicitud) */}
      <Modal
        open={!!orgTarget}
        onClose={() => { setOrgTarget(null); setOrgForm(null) }}
        title="Crear empresa desde la solicitud"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => { setOrgTarget(null); setOrgForm(null) }}>Cancelar</Button>
            <Button size="sm" loading={creating} onClick={submitCreateOrg}>
              <Building2 size={14} /> Crear y responder
            </Button>
          </>
        }
      >
        {orgForm && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-[var(--color-text-muted)]">
              Se creará la empresa con su usuario administrador y se responderá la
              solicitud con los accesos{orgTarget?.plan !== 'free' ? ' y el código de activación' : ''}.
            </p>
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Nombre de la empresa
              <Input value={orgForm.name} onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value, slug: slugify(e.target.value) })} />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Slug (URL: /{orgForm.slug || '...'}/login)
              <Input value={orgForm.slug} onChange={(e) => setOrgForm({ ...orgForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })} />
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
                Nombre del admin
                <Input value={orgForm.admin_name} onChange={(e) => setOrgForm({ ...orgForm, admin_name: e.target.value })} />
              </label>
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
                Correo del admin
                <Input type="email" value={orgForm.admin_email} onChange={(e) => setOrgForm({ ...orgForm, admin_email: e.target.value })} />
              </label>
            </div>
            <label className="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">
              Contraseña temporal
              <Input value={orgForm.admin_password} onChange={(e) => setOrgForm({ ...orgForm, admin_password: e.target.value })} />
            </label>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              Estos accesos se incluirán en el mensaje de respuesta para enviárselos al cliente.
            </p>
          </div>
        )}
      </Modal>
    </Layout>
  )
}
