// Utilidades de fecha/hora para la UI.
//
// La API devuelve dos tipos de valores temporales:
//
//   1. Datetimes UTC SIN offset, ej. "2026-06-23T02:00:00" (created_at,
//      updated_at, timestamp, requested_at, reviewed_at). Los genera la BD con
//      NOW() en UTC. `new Date()` los interpreta como hora LOCAL, lo que corre el
//      día (en Perú, UTC-5, un upload de las 21:00 del 22 se ve como el 23) →
//      hay que marcarlos como UTC y formatearlos en la zona local del navegador.
//
//   2. Fechas puras "YYYY-MM-DD", ej. vencimientos (detected_date, alert_date).
//      No tienen hora ni zona. `new Date("2026-08-01")` las toma como medianoche
//      UTC, que en zonas negativas retrocede un día al formatear en local → hay
//      que formatearlas en UTC, sin convertir.

const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;
const HAS_TZ_RE = /([zZ]|[+-]\d{2}:?\d{2})$/;

/** True si el valor es una fecha pura "YYYY-MM-DD" (sin componente horario). */
function isDateOnly(value) {
  return typeof value === "string" && DATE_ONLY_RE.test(value);
}

/**
 * Parsea un valor de la API a un Date correctamente interpretado.
 * Los datetimes sin zona se asumen UTC; las fechas puras quedan en medianoche UTC.
 * @param {string|null|undefined} value
 * @returns {Date|null}
 */
export function parseApiDate(value) {
  if (!value) return null;
  let normalized = value;
  if (typeof value === "string" && !isDateOnly(value) && !HAS_TZ_RE.test(value)) {
    normalized = `${value}Z`; // datetime naive → marcar explícitamente como UTC
  }
  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Formatea solo la fecha. Las fechas puras se muestran en UTC (sin correr el día);
 * los datetimes se convierten a la zona local del navegador.
 * @param {string} value
 * @param {Intl.DateTimeFormatOptions} [opts] sobreescribe los campos por defecto
 */
export function formatDate(value, opts) {
  const d = parseApiDate(value);
  if (!d) return "—";
  const fields = opts ?? { day: "2-digit", month: "short", year: "numeric" };
  return d.toLocaleDateString("es-PE", {
    ...fields,
    ...(isDateOnly(value) ? { timeZone: "UTC" } : {}),
  });
}

/**
 * Formatea fecha + hora. Los datetimes se muestran en la zona local del navegador.
 * @param {string} value
 * @param {Intl.DateTimeFormatOptions} [opts] sobreescribe los campos por defecto
 */
export function formatDateTime(value, opts) {
  const d = parseApiDate(value);
  if (!d) return "—";
  const fields = opts ?? {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  };
  return d.toLocaleString("es-PE", {
    ...fields,
    ...(isDateOnly(value) ? { timeZone: "UTC" } : {}),
  });
}

/**
 * Días enteros desde hoy (calendario local) hasta una fecha. Positivo = futuro,
 * negativo = pasado. Compara por día calendario, ignorando la hora.
 * @param {string} value
 * @returns {number|null}
 */
export function daysUntilDate(value) {
  const d = parseApiDate(value);
  if (!d) return null;
  const today = new Date();
  const target = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const base = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.ceil((target - base) / 86400000);
}
