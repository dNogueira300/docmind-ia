import { Image, MoreVertical, Download, Eye, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import Badge from '../UI/Badge'
import { useAuth } from '../../context/AuthContext'
import clsx from 'clsx'

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

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatSize(kb) {
  if (!kb) return ''
  if (kb < 1024) return `${kb} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

/**
 * @param {{ doc: object, categories: object[], onView: fn, onDownload: fn, onReclassify: fn, onDelete: fn }} props
 */
export default function DocumentRow({ doc, categories = [], onView, onDownload, onReclassify, onDelete }) {
  const { isAdmin, isEditor } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const category = categories.find((c) => c.id === doc.category_id)
  const score    = doc.ai_confidence_score

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
            <p
              className="text-xs"
              style={{ color: 'var(--color-text-muted)' }}
            >
              {formatSize(doc.file_size_kb)}
            </p>
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

      {/* Score IA */}
      <td className="px-4 py-3">
        {score != null ? (
          <span
            className="text-xs font-medium tabular-nums"
            style={{
              color: score >= 0.70
                ? 'var(--color-success)'
                : 'var(--color-warning)',
            }}
          >
            {(score * 100).toFixed(0)}%
          </span>
        ) : (
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>—</span>
        )}
      </td>

      {/* Fecha */}
      <td className="px-4 py-3">
        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          {formatDate(doc.created_at)}
        </span>
      </td>

      {/* Acciones */}
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="relative flex justify-end">
          <button
            className="p-1.5 rounded-[var(--radius-sm)] opacity-0 group-hover:opacity-100 transition-opacity duration-150"
            style={{ color: 'var(--color-text-muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <MoreVertical size={14} />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div
                className="absolute right-0 top-full mt-1 z-20 w-40 rounded-[var(--radius-lg)] py-1"
                style={{
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                }}
              >
                <MenuBtn icon={Eye}      label="Ver detalle"  onClick={() => { setMenuOpen(false); onView?.(doc) }} />
                <MenuBtn icon={Download} label="Descargar"    onClick={() => { setMenuOpen(false); onDownload?.(doc) }} />
                {isEditor && doc.status !== 'pending' && doc.status !== 'processing' && (
                  <MenuBtn icon={RefreshCw} label="Reclasificar" onClick={() => { setMenuOpen(false); onReclassify?.(doc) }} />
                )}
                {isAdmin && (
                  <MenuBtn icon={Trash2} label="Eliminar" onClick={() => { setMenuOpen(false); onDelete?.(doc) }} danger />
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

function MenuBtn({ icon: Icon, label, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium transition-colors duration-100"
      style={{ color: danger ? 'var(--color-error)' : 'var(--color-text-secondary)' }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = danger
          ? 'var(--color-error-bg)'
          : 'var(--color-bg-surface-2)'
      }}
      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
    >
      <Icon size={13} />
      {label}
    </button>
  )
}
