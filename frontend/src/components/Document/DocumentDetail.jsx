import { X, Download, RefreshCw, Calendar, FileType, HardDrive, Brain } from 'lucide-react'
import { useState } from 'react'
import Badge from '../UI/Badge'
import Button from '../UI/Button'
import { getDownloadUrl, reclassifyDocument } from '../../services/api/documents'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'

function Field({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-muted)] mb-0.5">{label}</p>
      <p className="text-sm text-[var(--color-text-primary)]">{value ?? '—'}</p>
    </div>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-PE', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

/**
 * @param {{ doc: object, categories: object[], onClose: () => void, onUpdated: () => void }} props
 */
export default function DocumentDetail({ doc, categories = [], onClose, onUpdated }) {
  const { isEditor } = useAuth()
  const toast = useToast()
  const [downloading, setDownloading] = useState(false)
  const [reclassifyMode, setReclassifyMode] = useState(false)
  const [selectedCat, setSelectedCat] = useState(doc.category_id ?? '')
  const [reclassifying, setReclassifying] = useState(false)

  const category = categories.find((c) => c.id === doc.category_id)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const { download_url } = await getDownloadUrl(doc.id)
      window.open(download_url, '_blank', 'noopener')
      toast.info('Descarga iniciada', 'El archivo se abrirá en nueva pestaña')
    } catch (err) {
      console.error('Error al obtener URL de descarga', err)
      toast.error('Error al descargar', 'No se pudo obtener el enlace de descarga')
    } finally {
      setDownloading(false)
    }
  }

  const handleReclassify = async () => {
    if (!selectedCat) return
    setReclassifying(true)
    try {
      await reclassifyDocument(doc.id, selectedCat)
      toast.success('Documento reclasificado', 'Nueva categoría asignada')
      onUpdated?.()
      setReclassifyMode(false)
    } catch (err) {
      console.error('Error al reclasificar', err)
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo reclasificar el documento')
    } finally {
      setReclassifying(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <aside className="relative w-full max-w-md bg-[var(--color-bg-surface)] border-l border-[var(--color-border)] h-full flex flex-col shadow-xl overflow-y-auto">
        {/* Header — h-14 alineado con TopBar */}
        <div className="flex items-center justify-between h-14 px-5 border-b border-[var(--color-border)] sticky top-0 bg-[var(--color-bg-surface)] z-10 shrink-0">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)] truncate pr-4">
            {doc.original_filename}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] shrink-0">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 p-5 flex flex-col gap-6">
          {/* Estado y acciones */}
          <div className="flex items-center justify-between">
            <Badge type="status" value={doc.status} />
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" loading={downloading} onClick={handleDownload}>
                <Download size={14} />
                Descargar
              </Button>
              {isEditor && !reclassifyMode && doc.status !== 'pending' && doc.status !== 'processing' && (
                <Button variant="secondary" size="sm" onClick={() => setReclassifyMode(true)}>
                  <RefreshCw size={14} />
                  Reclasificar
                </Button>
              )}
            </div>
          </div>

          {/* Reclasificación */}
          {reclassifyMode && (
            <div className="p-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface-2)] flex flex-col gap-3">
              <p className="text-xs font-medium text-[var(--color-text-secondary)]">Seleccionar nueva categoría</p>
              <select
                value={selectedCat}
                onChange={(e) => setSelectedCat(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              >
                <option value="">Seleccionar...</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setReclassifyMode(false)}>Cancelar</Button>
                <Button size="sm" loading={reclassifying} disabled={!selectedCat} onClick={handleReclassify}>
                  Guardar
                </Button>
              </div>
            </div>
          )}

          {/* Metadatos */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo" value={doc.file_type?.toUpperCase()} />
            <Field label="Tamaño" value={doc.file_size_kb ? `${doc.file_size_kb} KB` : null} />
            <Field label="Subido" value={formatDate(doc.created_at)} />
            <Field label="Actualizado" value={formatDate(doc.updated_at)} />
          </div>

          {/* Categoría y score */}
          <div className="flex flex-col gap-3 p-3 rounded-[var(--radius-md)] bg-[var(--color-ai-subtle)] border border-[var(--color-primary-border)]">
            <div className="flex items-center gap-1.5 text-[var(--color-ai-accent)]">
              <Brain size={14} />
              <span className="text-xs font-medium uppercase tracking-wide">Clasificación IA</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] text-[var(--color-text-muted)] mb-0.5">Categoría</p>
                {category ? (
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-text-primary)]">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: category.color }} />
                    {category.name}
                  </span>
                ) : (
                  <span className="text-sm text-[var(--color-text-muted)]">Sin asignar</span>
                )}
              </div>
              <div>
                <p className="text-[10px] text-[var(--color-text-muted)] mb-0.5">Confianza</p>
                <p className="text-sm font-medium text-[var(--color-ai-accent)]">
                  {doc.ai_confidence_score != null
                    ? `${(doc.ai_confidence_score * 100).toFixed(1)}%`
                    : '—'
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Texto OCR */}
          {doc.ocr_text && (
            <div className="flex flex-col gap-2">
              <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">Texto extraído (OCR)</p>
              <div className="max-h-48 overflow-y-auto p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)] border border-[var(--color-border)]">
                <p className="text-xs text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
                  {doc.ocr_text}
                </p>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
