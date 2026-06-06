import { useState, useEffect, useCallback } from "react";
import { X, ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";
import Layout from "../components/Layout/Layout";
import Badge from "../components/UI/Badge";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import EmptyState from "../components/UI/EmptyState";
import Button from "../components/UI/Button";
import { getAuditLog } from "../services/api/audit";
import { getUsers } from "../services/api/users";
import { useAuth } from "../context/AuthContext";

const LIMIT = 25;

// Todas las acciones registradas por el sistema
const ACTION_OPTIONS = [
  { value: "upload", label: "Subida" },
  { value: "view", label: "Visualización" },
  { value: "download", label: "Descarga" },
  { value: "reclassify", label: "Reclasificación" },
  { value: "delete", label: "Eliminación" },
  { value: "login", label: "Inicio de sesión" },
  { value: "user_create", label: "Admin creado" },
  { value: "user_update", label: "Admin editado" },
  { value: "user_password", label: "Cambio de contraseña" },
  { value: "user_deactivate", label: "Admin desactivado" },
  { value: "user_activate", label: "Admin reactivado" },
];

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncateId(id) {
  if (!id) return "—";
  return `${id.toString().slice(0, 8)}…`;
}

export default function AuditPage() {
  const { isSuperAdmin } = useAuth();
  const [entries, setEntries] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [skip, setSkip] = useState(0);
  const [filterUser, setFilterUser] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    try {
      const filters = { skip, limit: LIMIT };
      if (filterUser) filters.user_id = filterUser;
      if (filterAction) filters.action = filterAction;
      if (filterFrom) filters.from_date = filterFrom;
      if (filterTo) filters.to_date = filterTo + "T23:59:59";
      const data = await getAuditLog(filters);
      setEntries(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [skip, filterUser, filterAction, filterFrom, filterTo]);

  useEffect(() => {
    // Super admin en vista global no tiene tenant activo → no llamar a /users/
    if (!isSuperAdmin) {
      getUsers().then(setUsers).catch(console.error);
    }
  }, [isSuperAdmin]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const clearFilters = () => {
    setFilterUser("");
    setFilterAction("");
    setFilterFrom("");
    setFilterTo("");
    setSkip(0);
  };

  const hasFilters = filterUser || filterAction || filterFrom || filterTo;

  const inputCls =
    "px-3 py-1.5 text-xs rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] cursor-pointer";

  return (
    <Layout title="Auditoría">
      <div className="flex flex-col gap-4">
        {/* Filtros */}
        <div className="flex gap-2 flex-wrap items-center">
          {/* Filtro por usuario (solo si hay usuarios cargados) */}
          {users.length > 0 && (
            <select
              value={filterUser}
              onChange={(e) => {
                setFilterUser(e.target.value);
                setSkip(0);
              }}
              className={inputCls}
            >
              <option value="">Todos los usuarios</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          )}

          {/* Filtro por acción */}
          <select
            value={filterAction}
            onChange={(e) => {
              setFilterAction(e.target.value);
              setSkip(0);
            }}
            className={inputCls}
          >
            <option value="">Todas las acciones</option>
            {ACTION_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          {/* Rango de fechas */}
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-[var(--color-text-muted)]">
              Desde
            </label>
            <input
              type="date"
              value={filterFrom}
              onChange={(e) => {
                setFilterFrom(e.target.value);
                setSkip(0);
              }}
              className={inputCls}
            />
          </div>

          <div className="flex items-center gap-1.5">
            <label className="text-xs text-[var(--color-text-muted)]">
              Hasta
            </label>
            <input
              type="date"
              value={filterTo}
              onChange={(e) => {
                setFilterTo(e.target.value);
                setSkip(0);
              }}
              className={inputCls}
            />
          </div>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              <X size={12} /> Limpiar
            </button>
          )}
        </div>

        {/* Tabla */}
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-16">
              <LoadingSpinner />
            </div>
          ) : entries.length === 0 ? (
            <EmptyState
              title="Sin registros"
              description={
                hasFilters
                  ? "Prueba con otros filtros"
                  : "No hay actividad registrada aún"
              }
              icon={<ShieldCheck size={22} />}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-surface-2)]">
                    {[
                      "Fecha y hora",
                      "Usuario",
                      "Acción",
                      "Documento / Módulo",
                      "IP",
                    ].map((h) => (
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
                      {/* Fecha y hora — usa entry.timestamp, no entry.created_at */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className="text-xs font-mono"
                          style={{ color: "var(--color-text-secondary)" }}
                        >
                          {formatDateTime(entry.timestamp)}
                        </span>
                      </td>

                      {/* Usuario — nombre resuelto por el backend */}
                      <td className="px-4 py-3">
                        <p
                          className="text-sm font-medium"
                          style={{ color: "var(--color-text-primary)" }}
                        >
                          {entry.user_name ?? truncateId(entry.user_id)}
                        </p>
                        {entry.user_email && (
                          <p
                            className="text-xs"
                            style={{ color: "var(--color-text-muted)" }}
                          >
                            {entry.user_email}
                          </p>
                        )}
                      </td>

                      {/* Acción */}
                      <td className="px-4 py-3">
                        <Badge type="action" value={entry.action} />
                      </td>

                      {/* Documento / Detalle */}
                      <td className="px-4 py-3 max-w-[220px]">
                        {entry.document_name ? (
                          <p
                            className="text-sm truncate"
                            style={{ color: "var(--color-text-secondary)" }}
                            title={entry.document_name}
                          >
                            {entry.document_name}
                          </p>
                        ) : entry.document_id ? (
                          <span
                            className="text-xs font-mono"
                            style={{ color: "var(--color-text-muted)" }}
                          >
                            {truncateId(entry.document_id)}
                          </span>
                        ) : entry.detail_json?.affected_user_name ? (
                          // Acciones de gestión de usuarios
                          <div>
                            <p
                              className="text-sm truncate"
                              style={{ color: "var(--color-text-secondary)" }}
                            >
                              {entry.detail_json.affected_user_name}
                            </p>
                            {entry.detail_json.affected_user_email && (
                              <p
                                className="text-xs truncate"
                                style={{ color: "var(--color-text-muted)" }}
                              >
                                {entry.detail_json.affected_user_email}
                              </p>
                            )}
                          </div>
                        ) : entry.detail_json?.created_user_name ? (
                          // Creación de admin
                          <div>
                            <p
                              className="text-sm truncate"
                              style={{ color: "var(--color-text-secondary)" }}
                            >
                              {entry.detail_json.created_user_name}
                            </p>
                            {entry.detail_json.organization && (
                              <p
                                className="text-xs truncate"
                                style={{ color: "var(--color-text-muted)" }}
                              >
                                {entry.detail_json.organization}
                              </p>
                            )}
                          </div>
                        ) : (
                          <span
                            style={{ color: "var(--color-text-muted)" }}
                            className="text-xs"
                          >
                            —
                          </span>
                        )}
                      </td>

                      {/* IP */}
                      <td className="px-4 py-3">
                        <span
                          className="text-xs font-mono"
                          style={{ color: "var(--color-text-muted)" }}
                        >
                          {entry.ip_address ?? "—"}
                        </span>
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
            <span
              className="text-xs"
              style={{ color: "var(--color-text-muted)" }}
            >
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
  );
}
