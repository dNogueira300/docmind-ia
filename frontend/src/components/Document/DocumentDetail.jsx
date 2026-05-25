import { X, Download, RefreshCw, Brain, FileText, Image as ImageIcon } from 'lucide-react'
import { useState, useEffect } from 'react'
import Badge from '../UI/Badge'
import Button from '../UI/Button'
import LoadingSpinner from '../UI/LoadingSpinner'
import {
  getDownloadUrl,
  reclassifyDocument,
  getPreviewUrl,
  getDigitalizedUrl,
  getDocument,
} from '../../services/api/documents'
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

/** Renderiza el archivo original embebido según su tipo. */
function OriginalPreview({ url, fileType }) {
  if (!url) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-[var(--color-text-muted)]">
        <LoadingSpinner />
      </div>
    )
  }
  if (fileType === 'pdf') {
    return (
      <iframe
        title="Vista previa del documento original"
        src={url}
        className="w-full h-full border-0 rounded-[var(--radius-md)]"
      />
    )
  }
  // jpg / png
  return (
    <div className="w-full h-full overflow-auto bg-[var(--color-bg-surface-2)] rounded-[var(--radius-md)] flex items-center justify-center">
      <img
        src={url}
        alt="Original"
        className="max-w-full max-h-full object-contain"
      />
    </div>
  )
}

/** Renderiza el contenido digitalizado (texto OCR formateado). */
function DigitalizedPreview({ text }) {
  const normalized = (text || '').trim()
  if (!normalized) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-6 text-xs text-[var(--color-text-muted)]">
        <FileText size={28} className="mb-2 opacity-60" />
        <p>Sin texto digitalizado disponible todavía.</p>
        <p className="mt-1">
          El OCR aún no ha terminado o no pudo extraer texto del documento.
        </p>
      </div>
    )
  }
  return (
    <div className="w-full h-full overflow-auto bg-white text-black rounded-[var(--radius-md)] border border-[var(--color-border)]">
      <article className="prose prose-sm max-w-none p-6 leading-relaxed font-serif text-[13px] whitespace-pre-wrap">
        {normalized}
      </article>
    </div>
  )
}

/**
 * @param {{ doc: object, categories: object[], onClose: () => void, onUpdated: () => void }} props
 */
export default function DocumentDetail({ doc: initialDoc, categories = [], onClose, onUpdated }) {
  const { isEditor } = useAuth()
  const toast = useToast()
  const [doc, setDoc] = useState(initialDoc)
  const [downloading, setDownloading] = useState(false)
  const [downloadingDocx, setDownloadingDocx] = useState(false)
  const [reclassifyMode, setReclassifyMode] = useState(false)
  const [selectedCat, setSelectedCat] = useState(initialDoc.category_id ?? '')
  const [reclassifying, setReclassifying] = useState(false)
  const [activeTab, setActiveTab] = useState('original') // 'original' | 'digitalized'
  const [previewUrl, setPreviewUrl] = useState(null)
  const [previewType, setPreviewType] = useState(initialDoc.file_type)

  const category = categories.find((c) => c.id === doc.category_id)
  const hasDigitalized = doc.has_digitalized || !!doc.digitalized_path
  const stillProcessing = doc.status === 'pending' || doc.status === 'processing'

  // Cargar el documento completo (incluye ocr_text + digitalized_path)
  useEffect(() => {
    let cancelled = false
    getDocument(initialDoc.id)
      .then((full) => { if (!cancelled) setDoc(full) })
      .catch((err) => console.error('Error cargando documento', err))
    return () => { cancelled = true }
  }, [initialDoc.id])

  // Re-fetch periódico mientras esté procesándose
  useEffect(() => {
    if (!stillProcessing) return
    const interval = setInterval(() => {
      getDocument(initialDoc.id)
        .then(setDoc)
        .catch(() => {})
    }, 3000)
    return () => clearInterval(interval)
  }, [stillProcessing, initialDoc.id])

  // Cargar URL firmada para preview del original
  useEffect(() => {
    let cancelled = false
    setPreviewUrl(null)
    getPreviewUrl(initialDoc.id)
      .then((data) => {
        if (!cancelled) {
          setPreviewUrl(data.preview_url)
          setPreviewType(data.file_type)
        }
      })
      .catch((err) => {
        console.error('Error obteniendo preview URL', err)
      })
    return () => { cancelled = true }
  }, [initialDoc.id])

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const { download_url } = await getDownloadUrl(doc.id)
      window.open(download_url, '_blank', 'noopener')
      toast.info('Descarga iniciada', 'El archivo original se abrirá en nueva pestaña')
    } catch (err) {
      console.error('Error al obtener URL de descarga', err)
      toast.error('Error al descargar', 'No se pudo obtener el enlace de descarga')
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadDocx = async () => {
    setDownloadingDocx(true)
    try {
      const { download_url } = await getDigitalizedUrl(doc.id)
      window.open(download_url, '_blank', 'noopener')
      toast.success('Descargando .docx', 'El archivo digitalizado se abrirá en nueva pestaña')
    } catch (err) {
      console.error('Error al descargar .docx', err)
      toast.error(
        'No disponible',
        err.response?.data?.detail ?? 'El documento aún no ha sido digitalizado.',
      )
    } finally {
      setDownloadingDocx(false)
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
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative w-full max-w-5xl bg-[var(--color-bg-surface)] border-l border-[var(--color-border)] h-full flex flex-col shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between h-14 px-5 border-b border-[var(--color-border)] sticky top-0 bg-[var(--color-bg-surface)] z-10 shrink-0">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)] truncate pr-4">
            {doc.original_filename}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] shrink-0">
            <X size={16} />
          </button>
        </div>

        {/* Layout 2 columnas: previews a la izquierda, metadatos a la derecha */}
        <div className="flex-1 flex overflow-hidden">
          {/* ── Columna izquierda: vistas previas ──────────────────────── */}
          <div className="flex-1 flex flex-col p-5 border-r border-[var(--color-border)] min-w-0">
            {/* Tabs */}
            <div className="flex items-center gap-1 mb-3">
              <button
                onClick={() => setActiveTab('original')}
                className={[
                  'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] transition-colors',
                  activeTab === 'original'
                    ? 'bg-[var(--color-primary-subtle)] text-[var(--color-primary)] border border-[var(--color-primary-border)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] border border-transparent',
                ].join(' ')}
              >
                <ImageIcon size={13} />
                Original
              </button>
              <button
                onClick={() => setActiveTab('digitalized')}
                className={[
                  'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] transition-colors',
                  activeTab === 'digitalized'
                    ? 'bg-[var(--color-ai-subtle)] text-[var(--color-ai-accent)] border border-[var(--color-primary-border)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] border border-transparent',
                ].join(' ')}
              >
                <FileText size={13} />
                Digitalizado
              </button>

              {hasDigitalized && (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={downloadingDocx}
                  onClick={handleDownloadDocx}
                  className="ml-auto"
                >
                  <Download size={13} />
                  .docx
                </Button>
              )}
            </div>

            {/* Contenedor del preview activo */}
            <div className="flex-1 min-h-0">
              {activeTab === 'original' ? (
                <OriginalPreview url={previewUrl} fileType={previewType} />
              ) : (
                <DigitalizedPreview text={doc.ocr_text} />
              )}
            </div>

            {stillProcessing && (
              <p className="mt-3 text-[11px] text-[var(--color-warning)] flex items-center gap-1.5">
                <LoadingSpinner size="sm" />
                Procesando OCR y clasificación… la vista digitalizada se actualizará en segundos.
              </p>
            )}
          </div>

          {/* ── Columna derecha: metadatos + acciones ──────────────────── */}
          <div className="w-[340px] shrink-0 flex flex-col overflow-y-auto p-5 gap-5">
            {/* Estado y acciones */}
            <div className="flex items-center justify-between">
              <Badge type="status" value={doc.status} />
              <Button variant="secondary" size="sm" loading={downloading} onClick={handleDownload}>
                <Download size={13} />
                Original
              </Button>
            </div>

            {/* Reclasificación */}
            {isEditor && !reclassifyMode && !stillProcessing && (
              <Button variant="ghost" size="sm" onClick={() => setReclassifyMode(true)}>
                <RefreshCw size={13} />
                Reclasificar
              </Button>
            )}
            {reclassifyMode && (
              <div className="p-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface-2)] flex flex-col gap-3">
                <p className="text-xs font-medium text-[var(--color-text-secondary)]">Nueva categoría</p>
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
          </div>
        </div>
      </aside>
    </div>
  )
}
