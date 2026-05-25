import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { getOrganizationBySlug } from './services/api/organizations'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import UploadPage from './pages/UploadPage'
import SearchPage from './pages/SearchPage'
import CategoriesPage from './pages/CategoriesPage'
import UsersPage from './pages/UsersPage'
import AuditPage from './pages/AuditPage'
import OrganizationsPage from './pages/OrganizationsPage'

/* ───────────── Guards ─────────────────────────────────────────── */

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isAdmin) return <Navigate to="/" replace />
  return children
}

function EditorRoute({ children }) {
  const { isAuthenticated, isEditor, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isEditor) return <Navigate to="/" replace />
  return children
}

function SuperAdminRoute({ children }) {
  const { isAuthenticated, isSuperAdmin, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isSuperAdmin) return <Navigate to="/" replace />
  return children
}

/**
 * Guard de aislamiento de tenant.
 *
 * Si un usuario regular intenta entrar a `/otra-empresa/...`, lo redirigimos
 * a su propia empresa. Los super_admin pueden entrar a cualquier slug y la URL
 * gana sobre el tenant activo (se sincroniza vía useEffect en TenantSync).
 */
function TenantGuard({ children }) {
  const { user, isSuperAdmin, switchTenant, activeTenantId } = useAuth()
  const { tenantSlug } = useParams()
  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState(false)

  // Super admin: si el slug en URL no coincide con el tenant activo,
  // resolverlo vía API y actualizar el header X-Active-Tenant.
  useEffect(() => {
    if (!user || !isSuperAdmin || !tenantSlug) return
    let cancelled = false
    setResolving(true)
    getOrganizationBySlug(tenantSlug)
      .then((org) => {
        if (cancelled) return
        // Pasamos el objeto completo (no solo id) para hidratar el nombre en
        // el header sin un round-trip extra.
        switchTenant(org)
        setResolveError(false)
      })
      .catch(() => { if (!cancelled) setResolveError(true) })
      .finally(() => { if (!cancelled) setResolving(false) })
    return () => { cancelled = true }
  }, [user, isSuperAdmin, tenantSlug, activeTenantId, switchTenant])

  if (!user) return null

  // Regulares: redirigir si el slug no es el suyo
  if (!isSuperAdmin) {
    const userSlug = user.organization?.slug
    if (tenantSlug !== userSlug) {
      return <Navigate to={`/${userSlug}/documents`} replace />
    }
    return children
  }

  // Super admin: bloquear render mientras se resuelve el slug (evita queries
  // a la API con el tenant equivocado).
  if (resolveError) return <Navigate to="/admin/organizations" replace />
  if (resolving) return null
  return children
}

/* ───────────── Rutas ──────────────────────────────────────────── */

function AppRoutes() {
  const { isAuthenticated, isSuperAdmin, tenantSlug } = useAuth()

  const homeForRole = () => {
    if (!isAuthenticated) return '/login'
    if (isSuperAdmin) return '/admin/organizations'
    return tenantSlug ? `/${tenantSlug}/documents` : '/login'
  }

  return (
    <Routes>
      {/* Login global (super admin entra por aquí; regulares también pueden
          entrar acá y elegir empresa, o bien ir directo a /:slug/login). */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to={homeForRole()} replace /> : <LoginPage />}
      />
      <Route
        path="/:tenantSlug/login"
        element={isAuthenticated ? <Navigate to={homeForRole()} replace /> : <LoginPage />}
      />

      {/* Root → redirige según rol */}
      <Route path="/" element={<Navigate to={homeForRole()} replace />} />

      {/* ── Rutas SUPER ADMIN (sin tenant) ──────────────────────── */}
      <Route
        path="/admin/organizations"
        element={
          <SuperAdminRoute>
            <OrganizationsPage />
          </SuperAdminRoute>
        }
      />

      {/* ── Rutas TENANT-SCOPED ─────────────────────────────────── */}
      <Route
        path="/:tenantSlug/dashboard"
        element={
          <ProtectedRoute>
            <TenantGuard><DashboardPage /></TenantGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/:tenantSlug/documents"
        element={
          <ProtectedRoute>
            <TenantGuard><DocumentsPage /></TenantGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/:tenantSlug/upload"
        element={
          <EditorRoute>
            <TenantGuard><UploadPage /></TenantGuard>
          </EditorRoute>
        }
      />
      <Route
        path="/:tenantSlug/search"
        element={
          <ProtectedRoute>
            <TenantGuard><SearchPage /></TenantGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/:tenantSlug/categories"
        element={
          <AdminRoute>
            <TenantGuard><CategoriesPage /></TenantGuard>
          </AdminRoute>
        }
      />
      <Route
        path="/:tenantSlug/users"
        element={
          <AdminRoute>
            <TenantGuard><UsersPage /></TenantGuard>
          </AdminRoute>
        }
      />
      <Route
        path="/:tenantSlug/audit"
        element={
          <AdminRoute>
            <TenantGuard><AuditPage /></TenantGuard>
          </AdminRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
