import {
  X, Download, RefreshCw, Brain, FileText, Image as ImageIcon,
  Bell, BrainCircuit, Sliders,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import Badge from '../UI/Badge'
import Button from '../UI/Button'
import LoadingSpinner from '../UI/LoadingSpinner'
import AlertCard from '../UI/AlertCard'
import ChatPanel from './ChatPanel'
import {
  getDownloadUrl, reclassifyDocument,
  getPreviewUrl, getDigitalizedUrl, getDocument,
} from '../../services/api/documents'
import { getAlerts } from '../../services/api/alerts'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { formatDateTime as formatDate } from '../../utils/datetime'

/* ── Helpers ───────────────────────────────────────────────────────────── */

function Field({ label, value, wide }) {
  return (
    <div className={wide ? 'col-span-2' : ''}>
      <p className="text-[10px] uppercase tracking-wide mb-0.5" style={{ color: 'var(--color-text-muted)' }}>
        {label}
      </p>
      <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>{value ?? '—'}</p>
    </div>
  )
}

function formatSize(kb) {
  if (!kb) return '—'
  return kb < 1024 ? `${kb} KB` : `${(kb / 1024).toFixed(1)} MB`
}

/* ── Previsualización ──────────────────────────────────────────────────── */

function OriginalPreview({ url, fileType }) {
  if (!url) return (
    <div className="flex items-center justify-center h-full">
      <LoadingSpinner />
    </div>
  )
  if (fileType === 'pdf') return (
    <iframe title="Vista previa" src={url} className="w-full h-full border-0 rounded-[var(--radius-md)]" />
  )
  return (
    <div className="w-full h-full overflow-auto bg-[var(--color-bg-surface-2)] rounded-[var(--radius-md)] flex items-center justify-center">
      <img src={url} alt="Original" className="max-w-full max-h-full object-contain" />
    </div>
  )
}

function DigitalizedPreview({ text }) {
  const normalized = (text || '').trim()
  if (!normalized) return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 text-xs" style={{ color: 'var(--color-text-muted)' }}>
      <FileText size={28} className="mb-2 opacity-60" />
      <p>Sin texto digitalizado disponible todavía.</p>
    </div>
  )
  return (
    <div className="w-full h-full overflow-auto bg-white text-black rounded-[var(--radius-md)] border border-[var(--color-border)]">
      <article className="prose prose-sm max-w-none p-6 leading-relaxed font-serif text-[13px] whitespace-pre-wrap">
        {normalized}
      </article>
    </div>
  )
}

/* ── Tabs de la columna derecha ────────────────────────────────────────── */

const RIGHT_TABS = [
  { id: 'info',    label: 'Resumen',  Icon: FileText      },
  { id: 'chat',    label: 'DocMind',  Icon: BrainCircuit  },
  { id: 'actions', label: 'Acciones', Icon: Sliders       },
]

/* ── Componente principal ──────────────────────────────────────────────── */

export default function DocumentDetail({ doc: initialDoc, categories = [], onClose, onUpdated }) {
  const { isEditor } = useAuth()
  const toast        = useToast()

  const [doc,            setDoc]            = useState(initialDoc)
  const [previewUrl,     setPreviewUrl]     = useState(null)
  const [previewType,    setPreviewType]    = useState(initialDoc.file_type)
  const [previewTab,     setPreviewTab]     = useState('original')  // 'original' | 'digitalized'
  const [rightTab,       setRightTab]       = useState('info')      // 'info' | 'chat' | 'actions'
  const [docAlerts,      setDocAlerts]      = useState([])

  // Acciones
  const [downloading,     setDownloading]     = useState(false)
  const [downloadingDocx, setDownloadingDocx] = useState(false)
  const [reclassifyMode,  setReclassifyMode]  = useState(false)
  const [selectedCat,     setSelectedCat]     = useState(initialDoc.category_id ?? '')
  const [reclassifying,   setReclassifying]   = useState(false)

  const category      = categories.find((c) => c.id === doc.category_id)
  const hasDigitalized = doc.has_digitalized || !!doc.digitalized_path
  const stillProcessing = doc.status === 'pending' || doc.status === 'processing'

  /* ── Effects ─────────────────────────────────────────────────────────── */

  useEffect(() => {
    let cancelled = false
    getDocument(initialDoc.id)
      .then((full) => { if (!cancelled) setDoc(full) })
      .catch(console.error)
    return () => { cancelled = true }
  }, [initialDoc.id])

  useEffect(() => {
    if (!stillProcessing) return
    const t = setInterval(() => getDocument(initialDoc.id).then(setDoc).catch(() => {}), 3000)
    return () => clearInterval(t)
  }, [stillProcessing, initialDoc.id])

  useEffect(() => {
    let cancelled = false
    getAlerts({ document_id: initialDoc.id, limit: 20 })
      .then((d) => { if (!cancelled) setDocAlerts(d) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [initialDoc.id])

  useEffect(() => {
    let cancelled = false
    setPreviewUrl(null)
    getPreviewUrl(initialDoc.id)
      .then((d) => { if (!cancelled) { setPreviewUrl(d.preview_url); setPreviewType(d.file_type) } })
      .catch(console.error)
    return () => { cancelled = true }
  }, [initialDoc.id])

  /* ── Handlers ────────────────────────────────────────────────────────── */

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const { download_url } = await getDownloadUrl(doc.id)
      window.open(download_url, '_blank', 'noopener')
      toast.info('Descarga iniciada', 'El archivo original se abrirá en nueva pestaña')
    } catch { toast.error('Error al descargar', 'No se pudo obtener el enlace') }
    finally { setDownloading(false) }
  }

  const handleDownloadDocx = async () => {
    setDownloadingDocx(true)
    try {
      const { download_url } = await getDigitalizedUrl(doc.id)
      window.open(download_url, '_blank', 'noopener')
      toast.success('Descargando .docx', 'El archivo se abrirá en nueva pestaña')
    } catch (err) {
      toast.error('No disponible', err.response?.data?.detail ?? 'El documento aún no ha sido digitalizado.')
    } finally { setDownloadingDocx(false) }
  }

  const handleReclassify = async () => {
    if (!selectedCat) return
    setReclassifying(true)
    try {
      await reclassifyDocument(doc.id, selectedCat)
      toast.success('Documento reclasificado', 'Nueva categoría asignada')
      onUpdated?.(); setReclassifyMode(false)
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo reclasificar')
    } finally { setReclassifying(false) }
  }

  /* ── Render ──────────────────────────────────────────────────────────── */

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      <aside
        className="relative w-full bg-[var(--color-bg-surface)] border-l border-[var(--color-border)] h-full flex flex-col shadow-xl"
        style={{ maxWidth: 'min(1280px, 92vw)' }}
      >
        {/* ── Header ── */}
        <div
          className="flex items-center gap-3 h-14 px-5 border-b shrink-0 sticky top-0 z-10"
          style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
        >
          {/* Tipo archivo */}
          <div
            className="px-2 py-0.5 rounded text-[10px] font-bold shrink-0"
            style={{
              backgroundColor: doc.file_type === 'pdf' ? 'var(--color-error-bg)' : 'var(--color-primary-subtle)',
              color: doc.file_type === 'pdf' ? 'var(--color-error)' : 'var(--color-primary)',
            }}
          >
            {doc.file_type?.toUpperCase()}
          </div>

          {/* Nombre */}
          <h2
            className="flex-1 text-sm font-medium truncate"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {doc.original_filename}
          </h2>

          {/* Badge estado */}
          <Badge type="status" value={doc.status} />

          {/* Cerrar */}
          <button
            onClick={onClose}
            className="p-1.5 rounded-[var(--radius-sm)] shrink-0 transition-colors"
            style={{ color: 'var(--color-text-muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <X size={16} />
          </button>
        </div>

        {/* ── Cuerpo 2 columnas ── */}
        <div className="flex-1 flex overflow-hidden">

          {/* ── COLUMNA IZQUIERDA: Previsualización ── */}
          <div
            className="flex-1 flex flex-col p-4 border-r min-w-0"
            style={{ borderColor: 'var(--color-border)' }}
          >
            {/* Tabs preview */}
            <div className="flex items-center gap-1 mb-3">
              {[
                { id: 'original',    label: 'Original',     Icon: ImageIcon },
                { id: 'digitalized', label: 'Digitalizado', Icon: FileText  },
              ].map(({ id, label, Icon }) => (
                <button
                  key={id}
                  onClick={() => setPreviewTab(id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] transition-colors border"
                  style={{
                    backgroundColor: previewTab === id
                      ? (id === 'original' ? 'var(--color-primary-subtle)' : 'var(--color-ai-subtle)')
                      : 'transparent',
                    color: previewTab === id
                      ? (id === 'original' ? 'var(--color-primary)' : 'var(--color-ai-accent)')
                      : 'var(--color-text-secondary)',
                    borderColor: previewTab === id
                      ? 'var(--color-primary-border)'
                      : 'transparent',
                  }}
                >
                  <Icon size={13} /> {label}
                </button>
              ))}

              {hasDigitalized && (
                <Button variant="ghost" size="sm" loading={downloadingDocx} onClick={handleDownloadDocx} className="ml-auto">
                  <Download size={13} /> .docx
                </Button>
              )}
            </div>

            {/* Vista previa */}
            <div className="flex-1 min-h-0">
              {previewTab === 'original'
                ? <OriginalPreview url={previewUrl} fileType={previewType} />
                : <DigitalizedPreview text={doc.ocr_text} />
              }
            </div>

            {stillProcessing && (
              <p className="mt-3 text-[11px] flex items-center gap-1.5" style={{ color: 'var(--color-warning)' }}>
                <LoadingSpinner size="sm" />
                Procesando OCR y clasificación…
              </p>
            )}
          </div>

          {/* ── COLUMNA DERECHA: Tabs info/chat/acciones ── */}
          <div className="flex flex-col shrink-0" style={{ width: '380px' }}>

            {/* Barra de tabs */}
            <div
              className="flex border-b shrink-0"
              style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface-2)' }}
            >
              {RIGHT_TABS.map(({ id, label, Icon }) => (
                <button
                  key={id}
                  onClick={() => setRightTab(id)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors border-b-2"
                  style={{
                    color: rightTab === id ? 'var(--color-primary)' : 'var(--color-text-muted)',
                    borderBottomColor: rightTab === id ? 'var(--color-primary)' : 'transparent',
                    backgroundColor: rightTab === id ? 'var(--color-bg-surface)' : 'transparent',
                  }}
                >
                  <Icon size={13} /> {label}
                </button>
              ))}
            </div>

            {/* Contenido del tab activo */}
            <div className="flex-1 overflow-y-auto">

              {/* ── TAB: RESUMEN ── */}
              {rightTab === 'info' && (
                <div className="p-4 flex flex-col gap-4">

                  {/* Resumen IA */}
                  {doc.ai_summary ? (
                    <div
                      className="rounded-[var(--radius-md)] overflow-hidden border"
                      style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface-2)' }}
                    >
                      <p
                        className="px-3 pt-2.5 pb-1 text-[10px] font-semibold uppercase tracking-wide"
                        style={{ color: 'var(--color-ai-accent)' }}
                      >
                        ✦ Resumen generado por IA
                      </p>
                      <div className="px-3 pb-3">
                        <p
                          className="text-sm leading-relaxed"
                          style={{
                            color: 'var(--color-text-primary)',
                            wordBreak: 'break-word',
                            overflowWrap: 'break-word',
                          }}
                        >
                          {doc.ai_summary}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div
                      className="rounded-[var(--radius-md)] p-4 text-center"
                      style={{ backgroundColor: 'var(--color-bg-surface-2)', border: '1px dashed var(--color-border)' }}
                    >
                      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {stillProcessing ? 'Generando resumen…' : 'Sin resumen disponible'}
                      </p>
                    </div>
                  )}

                  {/* Clasificación IA */}
                  <div
                    className="rounded-[var(--radius-md)] p-4 flex flex-col gap-3"
                    style={{ backgroundColor: 'var(--color-ai-subtle)', border: '1px solid var(--color-primary-border)' }}
                  >
                    <div className="flex items-center gap-2" style={{ color: 'var(--color-ai-accent)' }}>
                      <Brain size={14} />
                      <span className="text-xs font-semibold uppercase tracking-wide">Clasificación IA</span>
                    </div>
                    <div className="flex items-center justify-between">
                      {category ? (
                        <span className="flex items-center gap-1.5 text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: category.color }} />
                          {category.name}
                        </span>
                      ) : (
                        <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Sin categoría</span>
                      )}
                      <span className="text-sm font-semibold tabular-nums" style={{ color: 'var(--color-ai-accent)' }}>
                        {doc.ai_confidence_score != null
                          ? `${(doc.ai_confidence_score * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                    </div>
                    {doc.risk_level && doc.risk_level !== 'low' && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Riesgo:</span>
                        <Badge type="risk" value={doc.risk_level} />
                      </div>
                    )}
                  </div>

                  {/* Metadatos */}
                  <div
                    className="rounded-[var(--radius-md)] p-4"
                    style={{ backgroundColor: 'var(--color-bg-surface-2)', border: '1px solid var(--color-border)' }}
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--color-text-muted)' }}>
                      Información del archivo
                    </p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      <Field label="Tipo" value={doc.file_type?.toUpperCase()} />
                      <Field label="Tamaño" value={formatSize(doc.file_size_kb)} />
                      <Field label="Subido" value={formatDate(doc.created_at)} wide />
                      <Field label="Procesado" value={formatDate(doc.updated_at)} wide />
                    </div>
                  </div>
                </div>
              )}

              {/* ── TAB: CHAT IA ── */}
              {rightTab === 'chat' && (
                <div className="p-4 h-full flex flex-col">
                  <ChatPanel
                    documentId={initialDoc.id}
                    docName={doc.original_filename}
                    initiallyOpen
                  />
                </div>
              )}

              {/* ── TAB: ACCIONES ── */}
              {rightTab === 'actions' && (
                <div className="p-4 flex flex-col gap-4">

                  {/* Descargas */}
                  <div className="flex flex-col gap-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
                      Descargas
                    </p>
                    <Button variant="secondary" size="sm" loading={downloading} onClick={handleDownload}>
                      <Download size={13} /> Descargar original
                    </Button>
                    {hasDigitalized && (
                      <Button variant="ghost" size="sm" loading={downloadingDocx} onClick={handleDownloadDocx}>
                        <Download size={13} /> Descargar .docx digitalizado
                      </Button>
                    )}
                  </div>

                  {/* Reclasificar */}
                  {isEditor && !stillProcessing && (
                    <div className="flex flex-col gap-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
                        Clasificación
                      </p>
                      {!reclassifyMode ? (
                        <Button variant="ghost" size="sm" onClick={() => setReclassifyMode(true)}>
                          <RefreshCw size={13} /> Reclasificar documento
                        </Button>
                      ) : (
                        <div
                          className="rounded-[var(--radius-md)] p-3 flex flex-col gap-3"
                          style={{ border: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-surface-2)' }}
                        >
                          <select
                            value={selectedCat}
                            onChange={(e) => setSelectedCat(e.target.value)}
                            className="w-full px-3 py-2 text-sm rounded-[var(--radius-md)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                            style={{ border: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-surface)', color: 'var(--color-text-primary)' }}
                          >
                            <option value="">Seleccionar categoría…</option>
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
                    </div>
                  )}

                  {/* Alertas de vencimiento */}
                  {docAlerts.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wide flex items-center gap-1.5" style={{ color: 'var(--color-warning)' }}>
                        <Bell size={11} /> Alertas de vencimiento ({docAlerts.length})
                      </p>
                      {docAlerts.map((alert) => (
                        <AlertCard
                          key={alert.id}
                          alert={alert}
                          compact
                          onDismissed={() => setDocAlerts((prev) => prev.filter((a) => a.id !== alert.id))}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}
