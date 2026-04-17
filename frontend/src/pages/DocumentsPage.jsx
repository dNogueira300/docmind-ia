import { useState, useEffect, useCallback, useRef } from 'react'
import { Search, Upload, ChevronLeft, ChevronRight, X } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import DocumentRow from '../components/Document/DocumentRow'
import DocumentDetail from '../components/Document/DocumentDetail'
import DocumentUpload from '../components/Document/DocumentUpload'
import Modal from '../components/UI/Modal'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import { getDocuments, searchDocuments, getDownloadUrl, deleteDocument } from '../services/api/documents'
import { getCategories } from '../services/api/categories'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

const LIMIT = 20
const POLL_INTERVAL = 3000

export default function DocumentsPage() {
  const { isEditor } = useAuth()
  const toast = useToast()
  const [docs, setDocs] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [skip, setSkip] = useState(0)
  const [query, setQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const pollRef = useRef(null)

  const fetchDocs = useCallback(async (resetSkip = false) => {
    const currentSkip = resetSkip ? 0 : skip
    if (resetSkip) setSkip(0)
    try {
      let results
      if (query.trim()) {
        results = await searchDocuments(query.trim(), currentSkip, LIMIT)
      } else {
        const filters = { skip: currentSkip, limit: LIMIT }
        if (filterStatus) filters.status = filterStatus
        if (filterCat) filters.category_id = filterCat
        results = await getDocuments(filters)
      }
      setDocs(results)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [query, filterStatus, filterCat, skip])

  // Initial load + categorías
  useEffect(() => {
    getCategories().then(setCategories).catch(console.error)
  }, [])

  // Re-fetch when filters/pagination change
  useEffect(() => {
    setLoading(true)
    fetchDocs()
  }, [query, filterStatus, filterCat, skip]) // eslint-disable-line

  // Polling para documentos en procesamiento
  useEffect(() => {
    const hasPending = docs.some((d) => d.status === 'pending' || d.status === 'processing')
    if (hasPending) {
      pollRef.current = setInterval(() => fetchDocs(), POLL_INTERVAL)
    } else {
      clearInterval(pollRef.current)
    }
    return () => clearInterval(pollRef.current)
  }, [docs, fetchDocs])

  const handleDownload = async (doc) => {
    try {
      const { download_url } = await getDownloadUrl(doc.id)
      window.open(download_url, '_blank', 'noopener')
      toast.info('Descarga iniciada', 'El archivo se abrirá en nueva pestaña')
    } catch (err) {
      console.error(err)
      toast.error('Error al descargar', 'No se pudo obtener el enlace de descarga')
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteDocument(deleteTarget.id)
      setDeleteTarget(null)
      fetchDocs()
    } catch (err) {
      console.error(err)
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo eliminar el documento')
    } finally {
      setDeleting(false)
    }
  }

  const clearFilters = () => {
    setQuery('')
    setFilterStatus('')
    setFilterCat('')
    setSkip(0)
  }

  const hasFilters = query || filterStatus || filterCat

  return (
    <Layout title="Documentos">
      {/* Barra superior */}
      <div className="flex flex-col gap-3 mb-4">
        {/* Search + Upload */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSkip(0) }}
              placeholder="Buscar en el contenido de los documentos..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-[var(--color-primary)] transition-colors"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              >
                <X size={14} />
              </button>
            )}
          </div>
          {isEditor && (
            <Button size="md" onClick={() => setUploadOpen(true)}>
              <Upload size={15} />
              Subir
            </Button>
          )}
        </div>

        {/* Filtros */}
        <div className="flex gap-2 flex-wrap items-center">
          <select
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value); setSkip(0) }}
            className={[
              'px-3 py-1.5 text-sm rounded-[var(--radius-md)] border cursor-pointer',
              'transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]',
              'hover:border-[var(--color-primary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
              filterStatus
                ? 'bg-[var(--color-primary-subtle)] border-[var(--color-primary)] text-[var(--color-primary)] font-medium'
                : 'bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-secondary)]',
            ].join(' ')}
          >
            <option value="">Todos los estados</option>
            <option value="classified">Clasificado</option>
            <option value="pending">Pendiente</option>
            <option value="processing">Procesando</option>
            <option value="review">Revisión</option>
            <option value="error">Error</option>
          </select>

          <select
            value={filterCat}
            onChange={(e) => { setFilterCat(e.target.value); setSkip(0) }}
            className={[
              'px-3 py-1.5 text-sm rounded-[var(--radius-md)] border cursor-pointer',
              'transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]',
              'hover:border-[var(--color-primary)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
              filterCat
                ? 'bg-[var(--color-primary-subtle)] border-[var(--color-primary)] text-[var(--color-primary)] font-medium'
                : 'bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-secondary)]',
            ].join(' ')}
          >
            <option value="">Todas las categorías</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              <X size={12} /> Limpiar filtros
            </button>
          )}
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <LoadingSpinner />
          </div>
        ) : docs.length === 0 ? (
          <EmptyState
            title={hasFilters ? 'Sin resultados' : 'Sin documentos'}
            description={hasFilters ? 'Prueba con otros filtros' : 'Sube tu primer documento para comenzar'}
            action={isEditor && !hasFilters && (
              <Button size="sm" onClick={() => setUploadOpen(true)}>
                <Upload size={14} /> Subir documento
              </Button>
            )}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-surface-2)]">
                  {['Documento', 'Estado', 'Categoría', 'Score IA', 'Fecha', ''].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {docs.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    doc={doc}
                    categories={categories}
                    onView={setSelectedDoc}
                    onDownload={handleDownload}
                    onReclassify={setSelectedDoc}
                    onDelete={setDeleteTarget}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Paginación */}
      {docs.length > 0 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-[var(--color-text-muted)]">
            Mostrando {skip + 1}–{skip + docs.length}
          </span>
          <div className="flex gap-2">
            <button
              disabled={skip === 0}
              onClick={() => setSkip(Math.max(0, skip - LIMIT))}
              className={[
                'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-[var(--radius-md)] border',
                'transition-all duration-200 ease-out',
                skip === 0
                  ? 'opacity-40 cursor-not-allowed pointer-events-none bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-secondary)]'
                  : 'bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer hover:bg-[var(--color-bg-surface-2)] hover:border-[var(--color-primary)] hover:text-[var(--color-text-primary)] hover:scale-[1.02] hover:shadow-sm',
              ].join(' ')}
            >
              <ChevronLeft size={14} /> Anterior
            </button>
            <button
              disabled={docs.length < LIMIT}
              onClick={() => setSkip(skip + LIMIT)}
              className={[
                'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-[var(--radius-md)] border',
                'transition-all duration-200 ease-out',
                docs.length < LIMIT
                  ? 'opacity-40 cursor-not-allowed pointer-events-none bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-secondary)]'
                  : 'bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer hover:bg-[var(--color-bg-surface-2)] hover:border-[var(--color-primary)] hover:text-[var(--color-text-primary)] hover:scale-[1.02] hover:shadow-sm',
              ].join(' ')}
            >
              Siguiente <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Panel detalle */}
      {selectedDoc && (
        <DocumentDetail
          doc={selectedDoc}
          categories={categories}
          onClose={() => setSelectedDoc(null)}
          onUpdated={() => { setSelectedDoc(null); fetchDocs() }}
        />
      )}

      {/* Modal upload */}
      <Modal open={uploadOpen} onClose={() => setUploadOpen(false)} title="Subir documento">
        <DocumentUpload
          onSuccess={() => { fetchDocs(); setUploadOpen(false) }}
          onClose={() => setUploadOpen(false)}
        />
      </Modal>

      {/* Modal eliminar */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar documento"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(null)}>Cancelar</Button>
            <Button variant="danger" size="sm" loading={deleting} onClick={handleDelete}>Eliminar</Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text-secondary)]">
          ¿Eliminar <span className="font-medium text-[var(--color-text-primary)]">{deleteTarget?.original_filename}</span>?
          Esta acción no se puede deshacer.
        </p>
      </Modal>
    </Layout>
  )
}
