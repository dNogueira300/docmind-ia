import { useState, useEffect } from 'react'
import { Sparkles, Check, X } from 'lucide-react'
import {
  getCategorySuggestions, approveCategorySuggestion, rejectCategorySuggestion,
  getCategories,
} from '../../services/api/categories'
import { useToast } from '../../context/ToastContext'

/**
 * Banner reutilizable con las sugerencias de categorías de la IA pendientes.
 * Permite aprobar (crea la categoría, respeta el límite de 10) o rechazar.
 * Solo debe renderizarse para administradores.
 *
 * @param {{ onChange?: () => void }} props onChange se llama tras aprobar/rechazar.
 */
export default function CategorySuggestionsBanner({ onChange }) {
  const toast = useToast()
  const [suggestions, setSuggestions] = useState([])
  const [catCount, setCatCount] = useState(0)
  const [busy, setBusy] = useState(null)

  const load = () => {
    getCategorySuggestions('pending').then(setSuggestions).catch(console.error)
    getCategories().then((c) => setCatCount(c.length)).catch(console.error)
  }
  // Carga inicial + sondeo cada 6s para que las sugerencias nuevas aparezcan
  // sin tener que refrescar la página (se crean en background tras subir un doc).
  useEffect(() => {
    load()
    const timer = setInterval(load, 6000)
    return () => clearInterval(timer)
  }, [])

  const approve = async (s) => {
    setBusy(s.id)
    try {
      await approveCategorySuggestion(s.id)
      toast.success('Categoría creada', s.suggested_name)
      load()
      onChange?.()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo aprobar')
    } finally {
      setBusy(null)
    }
  }

  const reject = async (s) => {
    setBusy(s.id)
    try {
      await rejectCategorySuggestion(s.id)
      load()
      onChange?.()
    } catch (err) {
      toast.error('Error', err.response?.data?.detail ?? 'No se pudo rechazar')
    } finally {
      setBusy(null)
    }
  }

  if (suggestions.length === 0) return null

  return (
    <div
      className="rounded-[var(--radius-lg)] border p-4 flex flex-col gap-3"
      style={{ backgroundColor: 'var(--color-ai-subtle)', borderColor: 'var(--color-ai-accent)' }}
    >
      <div className="flex items-center gap-2">
        <Sparkles size={15} style={{ color: 'var(--color-ai-accent)' }} />
        <p className="text-sm font-semibold" style={{ color: 'var(--color-ai-accent)' }}>
          Categorías sugeridas por la IA ({suggestions.length})
        </p>
      </div>
      <p className="text-xs text-[var(--color-text-muted)]">
        La IA propuso estas categorías a partir de documentos que no encajaban. Apruébalas
        para crearlas (respeta el límite de 10) o recházalas.
      </p>
      <ul className="flex flex-col gap-2">
        {suggestions.map((s) => (
          <li
            key={s.id}
            className="flex items-center gap-3 bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] px-3 py-2"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                {s.suggested_name}
              </p>
              {s.document_name && (
                <p className="text-[11px] text-[var(--color-text-muted)] truncate">
                  Sugerida a partir de: {s.document_name}
                </p>
              )}
              {s.confidence != null && (
                <p className="text-[11px] text-[var(--color-text-muted)]">
                  Confianza IA: {Math.round(s.confidence * 100)}%
                </p>
              )}
            </div>
            <button
              onClick={() => approve(s)}
              disabled={busy === s.id || catCount >= 10}
              title={catCount >= 10 ? 'Límite de 10 categorías alcanzado' : 'Aprobar'}
              className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-success)] hover:bg-[var(--color-success-bg)] transition-colors disabled:opacity-40"
            >
              <Check size={15} />
            </button>
            <button
              onClick={() => reject(s)}
              disabled={busy === s.id}
              title="Rechazar"
              className="p-1.5 rounded-[var(--radius-sm)] text-[var(--color-error)] hover:bg-[var(--color-error-bg)] transition-colors disabled:opacity-40"
            >
              <X size={15} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
