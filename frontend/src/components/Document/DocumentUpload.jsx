import { useState, useRef, useCallback } from 'react'
import { Upload, X, FileText, Image, CheckCircle2, AlertCircle } from 'lucide-react'
import { uploadDocument } from '../../services/api/documents'
import { useToast } from '../../context/ToastContext'
import Button from '../UI/Button'
import clsx from 'clsx'

const ACCEPTED = ['.pdf', '.jpg', '.jpeg', '.png']
const MAX_MB = 20
const MAX_BYTES = MAX_MB * 1024 * 1024

function getFileError(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ACCEPTED.includes(ext)) return `Tipo no permitido (${ext}). Solo PDF, JPG, PNG.`
  if (file.size > MAX_BYTES) return `El archivo supera ${MAX_MB} MB.`
  return null
}

/** @param {{ onSuccess?: (doc: object) => void, onClose?: () => void }} props */
export default function DocumentUpload({ onSuccess, onClose }) {
  const toast = useToast()
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [fileError, setFileError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploaded, setUploaded] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()

  const handleFile = useCallback((f) => {
    const err = getFileError(f)
    setFile(f)
    setFileError(err)
    setUploaded(null)
    setError(null)
  }, [])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const onInputChange = (e) => {
    const f = e.target.files[0]
    if (f) handleFile(f)
  }

  const handleUpload = async () => {
    if (!file || fileError) return
    setUploading(true)
    setError(null)
    try {
      const doc = await uploadDocument(file)
      setUploaded(doc)
      toast.success('Documento subido', 'El archivo está siendo procesado')
      onSuccess?.(doc)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al subir el archivo'
      setError(msg)
      toast.error('Error al subir', msg)
    } finally {
      setUploading(false)
    }
  }

  if (uploaded) {
    return (
      <div className="flex flex-col items-center gap-3 py-6">
        <CheckCircle2 size={36} className="text-[var(--color-success)]" />
        <p className="text-sm font-medium text-[var(--color-text-primary)]">Documento subido</p>
        <p className="text-xs text-[var(--color-text-muted)] text-center">
          El archivo está en cola de procesamiento. En unos segundos tendrá su texto y clasificación.
        </p>
        <div className="flex gap-2 mt-2">
          <Button variant="ghost" size="sm" onClick={() => { setFile(null); setUploaded(null) }}>
            Subir otro
          </Button>
          <Button size="sm" onClick={onClose}>Cerrar</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          'border-2 border-dashed rounded-[var(--radius-lg)] p-8 text-center cursor-pointer transition-colors',
          dragging
            ? 'border-[var(--color-primary)] bg-[var(--color-primary-subtle)]'
            : 'border-[var(--color-border)] hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-subtle)]'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={onInputChange}
        />
        <Upload size={28} className="mx-auto mb-3 text-[var(--color-text-muted)]" />
        <p className="text-sm font-medium text-[var(--color-text-primary)]">
          Arrastra un archivo o haz clic para seleccionar
        </p>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">
          PDF, JPG, PNG · máx. {MAX_MB} MB
        </p>
      </div>

      {/* File preview */}
      {file && (
        <div className={clsx(
          'flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] border',
          fileError
            ? 'border-[var(--color-error)] bg-[var(--color-error-bg)]'
            : 'border-[var(--color-border)] bg-[var(--color-bg-surface-2)]'
        )}>
          {file.type === 'application/pdf'
            ? <FileText size={16} className="shrink-0 text-[var(--color-error)]" />
            : <Image size={16} className="shrink-0 text-[var(--color-primary)]" />
          }
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-[var(--color-text-primary)] truncate">{file.name}</p>
            {fileError
              ? <p className="text-xs text-[var(--color-error)]">{fileError}</p>
              : <p className="text-xs text-[var(--color-text-muted)]">{(file.size / 1024).toFixed(0)} KB</p>
            }
          </div>
          <button
            onClick={() => { setFile(null); setFileError(null) }}
            className="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-error-bg)] text-[var(--color-error)] text-xs">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      <div className="flex justify-end gap-2">
        {onClose && <Button variant="ghost" size="sm" onClick={onClose}>Cancelar</Button>}
        <Button
          size="sm"
          disabled={!file || !!fileError}
          loading={uploading}
          onClick={handleUpload}
        >
          Subir documento
        </Button>
      </div>
    </div>
  )
}
