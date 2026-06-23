import { Image, MoreVertical, Download, Eye, RefreshCw, Trash2, RotateCcw } from 'lucide-react'
import Badge from '../UI/Badge'
import ActionMenu from '../UI/ActionMenu'
import { useAuth } from '../../context/AuthContext'
import { formatDate } from '../../utils/datetime'
import Snippet from '../UI/Snippet'

function FileIcon({ type }) {
  const base = 'w-8 h-8 rounded-[var(--radius-md)] flex items-center justify-center shrink-0 text-[10px] font-semibold'
  if (type === 'pdf') {
    return (
      <div
        className={base}
        style={{ backgroundColor: 'var(--color-error-bg)', color: 'var(--color-error)' }}
      >
        PDF
      </div>
    )
  }
  return (
    <div
      className={base}
      style={{ backgroundColor: 'var(--color-primary-subtle)', color: 'var(--color-primary)' }}
    >
      <Image size={15} />
    </div>
  )
}


function formatSize(kb) {
  if (!kb) return ''
  if (kb < 1024) return `${kb} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

/**
 * @param {{ doc, categories, onView, onDownload, onReclassify, onDelete, onReprocess }} props
 */
export default function DocumentRow({ doc, categories = [], onView, onDownload, onReclassify, onDelete, onReprocess }) {
  const { isAdmin, isEditor } = useAuth()

  const category = categories.find((c) => c.id === doc.category_id)
  const score    = doc.ai_confidence_score
  const canReclassify = isEditor && doc.status !== 'pending' && doc.status !== 'processing'
  const canReprocess  = isEditor && (doc.status === 'review' || doc.status === 'error')

  const menuItems = [
    { label: 'Ver detalle',  icon: Eye,       onClick: () => onView?.(doc) },
    { label: 'Descargar',    icon: Download,  onClick: () => onDownload?.(doc) },
    ...(canReclassify
      ? [{ label: 'Reclasificar', icon: RefreshCw, onClick: () => onReclassify?.(doc) }]
      : []),
    ...(canReprocess
      ? [{ label: 'Reprocesar', icon: RotateCcw, onClick: () => onReprocess?.(doc) }]
      : []),
    ...(isAdmin
      ? [{ label: 'Eliminar', icon: Trash2, onClick: () => onDelete?.(doc), danger: true }]
      : []),
  ]

  return (
    <tr
      className="cursor-pointer group transition-all duration-150"
      style={{ borderBottom: '1px solid var(--color-border)' }}
      onClick={() => onView?.(doc)}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)'
        e.currentTarget.style.boxShadow = 'inset 2px 0 0 var(--color-primary)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {/* Archivo */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <FileIcon type={doc.file_type} />
          <div className="min-w-0">
            <p
              className="text-sm font-medium truncate max-w-[220px]"
              style={{ color: 'var(--color-text-primary)' }}
            >
              {doc.original_filename}
            </p>
            {doc.snippet ? (
              <Snippet
                text={doc.snippet}
                className="text-xs max-w-[260px] mt-0.5 line-clamp-2"
              />
            ) : doc.ai_summary ? (
              <p
                className="text-xs truncate max-w-[220px] mt-0.5"
                style={{ color: 'var(--color-text-muted)' }}
              >
                {doc.ai_summary}
              </p>
            ) : (
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {formatSize(doc.file_size_kb)}
              </p>
            )}
          </div>
        </div>
      </td>

      {/* Estado */}
      <td className="px-4 py-3">
        <Badge type="status" value={doc.status} />
      </td>

      {/* Categoría */}
      <td className="px-4 py-3">
        {category ? (
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
            style={{
              backgroundColor: 'var(--color-bg-surface-2)',
              color: 'var(--color-text-secondary)',
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ backgroundColor: category.color ?? 'var(--color-primary)' }}
            />
            {category.name}
          </span>
        ) : (
          <span style={{ color: 'var(--color-text-muted)' }} className="text-xs">—</span>
        )}
      </td>

      {/* Score IA + Riesgo */}
      <td className="px-4 py-3">
        <div className="flex flex-col gap-1">
          {score != null ? (
            <span
              className="text-xs font-medium tabular-nums"
              style={{
                color: score >= 0.70 ? 'var(--color-success)' : 'var(--color-warning)',
              }}
            >
              {(score * 100).toFixed(0)}%
            </span>
          ) : (
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>—</span>
          )}
          {doc.risk_level && doc.risk_level !== 'low' && (
            <Badge type="risk" value={doc.risk_level} />
          )}
        </div>
      </td>

      {/* Subido por */}
      <td className="px-4 py-3">
        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          {doc.uploader_name ?? '—'}
        </span>
      </td>

      {/* Fecha */}
      <td className="px-4 py-3">
        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          {formatDate(doc.created_at)}
        </span>
      </td>

      {/* Acciones */}
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-end">
          <ActionMenu
            align="right"
            items={menuItems}
            trigger={
              <button
                className="p-1.5 rounded-[var(--radius-sm)] opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity duration-150"
                style={{ color: 'var(--color-text-muted)' }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                aria-label="Acciones"
              >
                <MoreVertical size={14} />
              </button>
            }
          />
        </div>
      </td>
    </tr>
  )
}
