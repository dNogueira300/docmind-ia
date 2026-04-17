import { useState } from 'react'
import { Search } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import DocumentDetail from '../components/Document/DocumentDetail'
import Badge from '../components/UI/Badge'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import { searchDocuments } from '../services/api/documents'
import { getCategories } from '../services/api/categories'
import { useEffect } from 'react'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState(null)

  useEffect(() => {
    getCategories().then(setCategories).catch(console.error)
  }, [])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const data = await searchDocuments(query.trim())
      setResults(data)
    } catch (err) {
      console.error(err)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Búsqueda semántica">
      <div className="max-w-2xl mx-auto flex flex-col gap-6">
        {/* Buscador */}
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar en el contenido de los documentos..."
              className="w-full pl-10 pr-4 py-2.5 text-sm rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-[var(--color-primary)] transition-colors"
              autoFocus
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 rounded-[var(--radius-md)] bg-[var(--color-primary)] text-white text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors"
          >
            Buscar
          </button>
        </form>

        {/* Resultados */}
        {loading ? (
          <div className="flex justify-center py-10"><LoadingSpinner /></div>
        ) : searched && results.length === 0 ? (
          <EmptyState
            title="Sin resultados"
            description={`No se encontraron documentos clasificados que contengan "${query}"`}
            icon={<Search size={22} />}
          />
        ) : results.length > 0 ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-[var(--color-text-muted)]">
              {results.length} resultado{results.length !== 1 ? 's' : ''}
            </p>
            {results.map((doc) => {
              const cat = categories.find((c) => c.id === doc.category_id)
              return (
                <button
                  key={doc.id}
                  onClick={() => setSelectedDoc(doc)}
                  className="text-left bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-4 hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-subtle)] transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{doc.original_filename}</p>
                    <Badge type="status" value={doc.status} />
                  </div>
                  {cat && (
                    <span className="inline-flex items-center gap-1.5 mt-1.5 text-xs text-[var(--color-text-muted)]">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cat.color }} />
                      {cat.name}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center py-12 text-center">
            <Search size={32} className="text-[var(--color-text-muted)] mb-3" />
            <p className="text-sm text-[var(--color-text-muted)]">
              Escribe una búsqueda y presiona Enter
            </p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              Busca en el texto extraído de los documentos clasificados
            </p>
          </div>
        )}
      </div>

      {selectedDoc && (
        <DocumentDetail
          doc={selectedDoc}
          categories={categories}
          onClose={() => setSelectedDoc(null)}
          onUpdated={() => setSelectedDoc(null)}
        />
      )}
    </Layout>
  )
}
