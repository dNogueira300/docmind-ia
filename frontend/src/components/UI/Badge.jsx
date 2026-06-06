import clsx from 'clsx'

const STATUS_STYLES = {
  classified: {
    label: 'Clasificado',
    bg:    'var(--color-success-bg)',
    color: 'var(--color-success)',
    dotBg: 'var(--color-success)',
    pulse: false,
  },
  pending: {
    label: 'Pendiente',
    bg:    'var(--color-warning-bg)',
    color: 'var(--color-warning)',
    dotBg: 'var(--color-warning)',
    pulse: false,
  },
  processing: {
    label: 'Procesando',
    bg:    'var(--color-primary-subtle)',
    color: 'var(--color-primary)',
    dotBg: 'var(--color-primary)',
    pulse: true,
  },
  review: {
    label: 'Revisión',
    bg:    'var(--color-review-bg)',
    color: 'var(--color-review)',
    dotBg: 'var(--color-review)',
    pulse: false,
  },
  error: {
    label: 'Error',
    bg:    'var(--color-error-bg)',
    color: 'var(--color-error)',
    dotBg: 'var(--color-error)',
    pulse: false,
  },
  pending_approval: {
    label: 'Aprobación',
    bg:    'rgba(245,197,58,0.15)',
    color: 'var(--color-warning)',
    dotBg: 'var(--color-warning)',
    pulse: true,
  },
}

const RISK_STYLES = {
  low:      { label: 'Bajo',     bg: 'var(--color-bg-surface-2)',   color: 'var(--color-text-muted)' },
  medium:   { label: 'Medio',    bg: 'var(--color-warning-bg)',      color: 'var(--color-warning)' },
  high:     { label: 'Alto',     bg: 'rgba(245,88,88,0.12)',         color: 'var(--color-error)' },
  critical: { label: 'Crítico',  bg: 'rgba(245,88,88,0.25)',         color: 'var(--color-error)' },
}

const ROLE_STYLES = {
  admin:     { bg: 'var(--color-primary-subtle)', color: 'var(--color-primary)' },
  editor:    { bg: 'var(--color-ai-subtle)',       color: 'var(--color-ai-accent)' },
  consultor: { bg: 'var(--color-bg-surface-2)',    color: 'var(--color-text-secondary)' },
}

const ROLE_LABELS   = { admin: 'Admin', editor: 'Editor', consultor: 'Consultor' }
const ACTION_STYLES = {
  upload:          { bg: 'var(--color-primary-subtle)', color: 'var(--color-primary)' },
  download:        { bg: 'var(--color-ai-subtle)',       color: 'var(--color-ai-accent)' },
  view:            { bg: 'var(--color-bg-surface-2)',    color: 'var(--color-text-secondary)' },
  reclassify:      { bg: 'var(--color-warning-bg)',      color: 'var(--color-warning)' },
  delete:          { bg: 'var(--color-error-bg)',        color: 'var(--color-error)' },
  login:           { bg: 'var(--color-success-bg)',      color: 'var(--color-success)' },
  user_create:     { bg: 'var(--color-success-bg)',      color: 'var(--color-success)' },
  user_update:     { bg: 'var(--color-primary-subtle)', color: 'var(--color-primary)' },
  user_password:   { bg: 'var(--color-warning-bg)',      color: 'var(--color-warning)' },
  user_deactivate: { bg: 'var(--color-error-bg)',        color: 'var(--color-error)' },
  user_activate:   { bg: 'var(--color-success-bg)',      color: 'var(--color-success)' },
}
const ACTION_LABELS = {
  upload:          'Subida',
  download:        'Descarga',
  view:            'Vista',
  reclassify:      'Reclasificación',
  delete:          'Eliminación',
  login:           'Login',
  user_create:     'Admin creado',
  user_update:     'Admin editado',
  user_password:   'Contraseña',
  user_deactivate: 'Desactivado',
  user_activate:   'Reactivado',
}

/** @param {{ type?: 'status'|'role'|'action'|'risk', value: string, className?: string }} props */
export default function Badge({ type = 'status', value, className }) {
  if (type === 'status') {
    const cfg = STATUS_STYLES[value] ?? STATUS_STYLES.pending
    return (
      <span
        className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium', className)}
        style={{ backgroundColor: cfg.bg, color: cfg.color }}
      >
        <span
          className={clsx('w-1.5 h-1.5 rounded-full shrink-0', cfg.pulse && 'animate-pulse')}
          style={{ backgroundColor: cfg.dotBg }}
        />
        {cfg.label}
      </span>
    )
  }

  if (type === 'role') {
    const s = ROLE_STYLES[value] ?? ROLE_STYLES.consultor
    return (
      <span
        className={clsx('inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium', className)}
        style={{ backgroundColor: s.bg, color: s.color }}
      >
        {ROLE_LABELS[value] ?? value}
      </span>
    )
  }

  if (type === 'action') {
    const s = ACTION_STYLES[value] ?? ACTION_STYLES.view
    return (
      <span
        className={clsx('inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium', className)}
        style={{ backgroundColor: s.bg, color: s.color }}
      >
        {ACTION_LABELS[value] ?? value}
      </span>
    )
  }

  if (type === 'risk') {
    const s = RISK_STYLES[value] ?? RISK_STYLES.low
    return (
      <span
        className={clsx('inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium', className)}
        style={{ backgroundColor: s.bg, color: s.color }}
      >
        {s.label}
      </span>
    )
  }

  return null
}
