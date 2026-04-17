import { useState, useEffect, useCallback } from 'react'
import { X } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import Badge from '../components/UI/Badge'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EmptyState from '../components/UI/EmptyState'
import Button from '../components/UI/Button'
import { getAuditLog } from '../services/api/audit'
import { getUsers } from '../services/api/users'
import { ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react'

const LIMIT = 25

const ACTION_LABELS = {
  upload: 'Subida',
  view: 'Visualización',
  download: 'Descarga',
  reclassify: 'Reclasificación',
  delete: 'Eliminación',
}

function formatDateTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('es-PE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function AuditPage() {
  const [entries, setEntries] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [skip, setSkip] = useState(0)
  const [filterUser, setFilterUser] = useState('')
  const [filterAction, setFilterAction] = useState('')
  const [filterFrom, setFilterFrom] = useState('')
  const [filterTo, setFilterTo] = useState('')

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    try {
      const filters = { skip, limit: LIMIT }
      if (filterUser) filters.user_id = filterUser
      if (filterAction) filters.action = filterAction
      if (filterFrom) filters.from_date = filterFrom
      if (filterTo) filters.to_date = filterTo
      const data = await getAuditLog(filters)
      setEntries(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [skip, filterUser, filterAction, filterFrom, filterTo])

  useEffect(() => {
    getUsers().then(setUsers).catch(console.error)
  }, [])

  useEffect(() => {
    fetchEntries()
  }, [fetchEntries])

  const clearFilters = () => {
    setFilterUser('')
    setFilterAction('')
    setFilterFrom('')
    setFilterTo('')
    setSkip(0)
  }

  const hasFilters = filterUser || filterAction || filterFrom || filterTo

  return (
    <Layout title="Auditoría">
      <div className="flex flex-col gap-4">
        {/* Filtros */}
        <div className="flex gap-2 flex-wrap items-center">
          <select
            value={filterUser}
            onChange={(e) => { setFilterUser(e.target.value); setSkip(0) }}
            className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] cursor-pointer"
          >
            <option value="">Todos los usuarios</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.name}</option>
            ))}
          </select>

          <select
            value={filterAction}
            onChange={(e) => { setFilterAction(e.target.value); setSkip(0) }}
            className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] cursor-pointer"
          >
            <option value="">Todas las acciones</option>
            {Object.entries(ACTION_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>

          <div className="flex items-center gap-1.5">
            <label className="text-xs text-[var(--color-text-muted)]">Desde</label>
            <input
              type="date"
              value={filterFrom}
              onChange={(e) => { setFilterFrom(e.target.value); setSkip(0) }}
              className="px-2 py-1.5 text-xs rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] cursor-pointer"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <label className="text-xs text-[var(--color-text-muted)]">Hasta</label>
            <input
              type="date"
              value={filterTo}
              onChange={(e) => { setFilterTo(e.target.value); setSkip(0) }}
              className="px-2 py-1.5 text-xs rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] cursor-pointer"
            />
          </div>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              <X size={12} /> Limpiar filtros
            </button>
          )}
        </div>

        {/* Tabla */}
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-16"><LoadingSpinner /></div>
          ) : entries.length === 0 ? (
            <EmptyState
              title="Sin registros"
              description={hasFilters ? 'Prueba con otros filtros' : 'No hay actividad registrada aún'}
              icon={<ShieldCheck size={22} />}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[600px] text-left">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-surface-2)]">
                    {['Fecha y hora', 'Usuario', 'Acción', 'Documento'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {entries.map((entry) => (
                    <tr
                      key={entry.id}
                      className="hover:bg-[var(--color-bg-surface-2)] transition-colors"
                    >
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs font-mono text-[var(--color-text-muted)]">
                          {formatDateTime(entry.created_at)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-sm text-[var(--color-text-primary)]">
                          {entry.user_name ?? entry.user_id ?? '—'}
                        </p>
                        {entry.user_email && (
                          <p className="text-xs text-[var(--color-text-muted)]">{entry.user_email}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge type="action" value={entry.action} />
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-sm text-[var(--color-text-secondary)] truncate max-w-xs">
                          {entry.document_name ?? entry.document_id ?? '—'}
                        </p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Paginación */}
        {entries.length > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--color-text-muted)]">
              Mostrando {skip + 1}–{skip + entries.length}
            </span>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={skip === 0}
                onClick={() => setSkip(Math.max(0, skip - LIMIT))}
              >
                <ChevronLeft size={14} /> Anterior
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={entries.length < LIMIT}
                onClick={() => setSkip(skip + LIMIT)}
              >
                Siguiente <ChevronRight size={14} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
