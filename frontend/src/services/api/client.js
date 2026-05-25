import axios from "axios";

const BASE_URL = "";
const TOKEN_KEY = "docmind-token";
const TENANT_KEY = "docmind-active-tenant";

// Token — persiste en localStorage para sobrevivir recargas
let _token = localStorage.getItem(TOKEN_KEY) || null;
// Tenant activo — usado solo por super_admin para operar dentro de una empresa
let _activeTenant = localStorage.getItem(TENANT_KEY) || null;

export function setToken(token) {
  _token = token;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  _token = null;
  localStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return _token;
}

/** Setea el tenant activo (UUID de la empresa). Usado por el super admin. */
export function setActiveTenant(orgId) {
  if (!orgId) {
    _activeTenant = null;
    localStorage.removeItem(TENANT_KEY);
  } else {
    _activeTenant = String(orgId);
    localStorage.setItem(TENANT_KEY, _activeTenant);
  }
}

export function getActiveTenant() {
  return _activeTenant;
}

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Agregar token + tenant activo a cada request
client.interceptors.request.use((config) => {
  if (_token) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  if (_activeTenant) {
    config.headers["X-Active-Tenant"] = _activeTenant;
  }
  return config;
});

// Si 401 → limpiar token y redirigir al login.
// Si la URL actual está dentro de un tenant (/:slug/...) regresamos al login
// de esa misma empresa. El super admin (sin slug en la URL) cae a /login.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      setActiveTenant(null);
      const path = window.location.pathname || "";
      // Match /:slug/... (no captura rutas reservadas como /admin o /login)
      const m = path.match(/^\/([^/]+)(?:\/|$)/);
      const reserved = new Set(["login", "admin", "api"]);
      const slug = m && !reserved.has(m[1]) ? m[1] : null;
      window.location.href = slug ? `/${slug}/login` : "/login";
    }
    return Promise.reject(error);
  },
);

export default client;
