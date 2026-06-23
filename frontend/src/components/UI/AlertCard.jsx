import { Bell, X, FileText } from 'lucide-react'
import { dismissAlert } from '../../services/api/alerts'
import { useToast } from '../../context/ToastContext'
import { formatDate, daysUntilDate as daysUntil } from '../../utils/datetime'

const TYPE_LABELS = { expiry: 'Vencimiento', deadline: 'Plazo límite', renewal: 'Renovación' }

/**
 * @param {{ alert: object, onDismissed?: () => void, compact?: boolean }} props
 * compact=true: diseño reducido para usar dentro de DocumentDetail
 */
export default function AlertCard({ alert, onDismissed, compact = false }) {
  const toast = useToast()
  const days     = daysUntil(alert.detected_date)
  const isUrgent = days !== null && days <= 7
  const accentColor = isUrgent ? 'var(--color-error)' : 'var(--color-warning)'
  const bgColor     = isUrgent ? 'var(--color-error-bg)' : 'var(--color-warning-bg)'

  const handleDismiss = async (e) => {
    e.stopPropagation()
    try {
      await dismissAlert(alert.id)
      onDismissed?.()
    } catch {
      toast.error('Error', 'No se pudo marcar la alerta como revisada')
    }
  }

  return (
    <div
      className="flex gap-3 p-3 rounded-[var(--radius-md)] border"
      style={{ backgroundColor: bgColor, borderColor: accentColor, opacity: 0.97 }}
    >
      {/* Ícono */}
      <Bell size={14} className="mt-0.5 shrink-0" style={{ color: accentColor }} />

      {/* Contenido */}
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        {/* Línea 1: tipo + días restantes + fecha */}
        <div className="flex items-center flex-wrap gap-2">
          <span className="text-xs font-semibold" style={{ color: accentColor }}>
            {TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
          </span>
          <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            {formatDate(alert.detected_date)}
          </span>
          {days !== null && days <= 30 && (
            <span
              className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
              style={{
                backgroundColor: accentColor,
                color: '#fff',
              }}
            >
              {days <= 0 ? 'VENCIDO' : days === 1 ? 'mañana' : `${days} días`}
            </span>
          )}
        </div>

        {/* Línea 2: nombre del documento (si está disponible) */}
        {!compact && alert.document_name && (
          <div className="flex items-center gap-1.5">
            <FileText size={11} style={{ color: 'var(--color-text-muted)' }} className="shrink-0" />
            <span
              className="text-xs font-medium truncate"
              style={{ color: 'var(--color-text-primary)' }}
              title={alert.document_name}
            >
              {alert.document_name}
            </span>
          </div>
        )}

        {/* Línea 3: descripción generada por IA */}
        {alert.detail && (
          <p
            className="text-xs font-medium"
            style={{ color: isUrgent ? accentColor : 'var(--color-text-secondary)' }}
          >
            {alert.detail}
          </p>
        )}
      </div>

      {/* Botón dismiss */}
      {onDismissed && (
        <button
          onClick={handleDismiss}
          className="p-1 rounded transition-colors shrink-0 self-start"
          style={{ color: 'var(--color-text-muted)' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
          title="Marcar como revisada"
        >
          <X size={12} />
        </button>
      )}
    </div>
  )
}
