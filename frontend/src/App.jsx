import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { PlanProvider } from './context/PlanContext'
import { getOrganizationBySlug } from './services/api/organizations'

import LoginPage from './pages/LoginPage'
import PlanPage from './pages/PlanPage'
import ActivationCodesPage from './pages/ActivationCodesPage'
import PricingPage from './pages/PricingPage'
import PricingAdminPage from './pages/PricingAdminPage'
import DemoRequestsPage from './pages/DemoRequestsPage'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import UploadPage from './pages/UploadPage'
import SearchPage from './pages/SearchPage'
import CategoriesPage from './pages/CategoriesPage'
import UsersPage from './pages/UsersPage'
import AuditPage from './pages/AuditPage'
import OrganizationsPage from './pages/OrganizationsPage'
import GlobalAdminsPage from './pages/GlobalAdminsPage'
import RiskRulesPage from './pages/RiskRulesPage'

/* ───────────── Guards ─────────────────────────────────────────── */

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

/**
 * Ruta exclusiva para usuarios de empresa (non-super_admin).
 * Si un super_admin intenta acceder, lo redirige a /admin/organizations.
 */
function TenantRoute({ children }) {
  const { isAuthenticated, isSuperAdmin, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (isSuperAdmin) return <Navigate to="/admin/organizations" replace />
  return children
}

function TenantAdminRoute({ children }) {
  const { isAuthenticated, isSuperAdmin, isAdmin, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (isSuperAdmin) return <Navigate to="/admin/organizations" replace />
  if (!isAdmin) return <Navigate to="/" replace />
  return children
}

function TenantEditorRoute({ children }) {
  const { isAuthenticated, isSuperAdmin, isEditor, loading } = useAuth()
  if (loading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (isSuperAdmin) return <Navigate to="/admin/organizations" replace />
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
 * Guard de aislamiento de tenant para usuarios regulares.
 * Super admins no llegan aquí (bloqueados por TenantRoute antes).
 */
function TenantGuard({ children }) {
  const { user, isSuperAdmin, switchTenant, activeTenantId } = useAuth()
  const { tenantSlug } = useParams()
  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState(false)

  useEffect(() => {
    if (!user || !isSuperAdmin || !tenantSlug) return
    let cancelled = false
    setResolving(true)
    getOrganizationBySlug(tenantSlug)
      .then((org) => {
        if (cancelled) return
        switchTenant(org)
        setResolveError(false)
      })
      .catch(() => { if (!cancelled) setResolveError(true) })
      .finally(() => { if (!cancelled) setResolving(false) })
    return () => { cancelled = true }
  }, [user, isSuperAdmin, tenantSlug, activeTenantId, switchTenant])

  if (!user) return null

  if (!isSuperAdmin) {
    const userSlug = user.organization?.slug
    if (tenantSlug !== userSlug) {
      return <Navigate to={`/${userSlug}/documents`} replace />
    }
    return children
  }

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
      {/* Login */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to={homeForRole()} replace /> : <LoginPage />}
      />
      <Route
        path="/:tenantSlug/login"
        element={isAuthenticated ? <Navigate to={homeForRole()} replace /> : <LoginPage />}
      />

      {/* Página pública de precios (sin autenticación) */}
      <Route path="/pricing" element={<PricingPage />} />

      {/* Root */}
      <Route path="/" element={<Navigate to={homeForRole()} replace />} />

      {/* ── Rutas SUPER ADMIN (globales, sin tenant) ─────────────────── */}
      <Route
        path="/admin/organizations"
        element={<SuperAdminRoute><OrganizationsPage /></SuperAdminRoute>}
      />
      <Route
        path="/admin/users"
        element={<SuperAdminRoute><GlobalAdminsPage /></SuperAdminRoute>}
      />
      <Route
        path="/admin/audit"
        element={<SuperAdminRoute><AuditPage /></SuperAdminRoute>}
      />
      <Route
        path="/admin/activation-codes"
        element={<SuperAdminRoute><ActivationCodesPage /></SuperAdminRoute>}
      />
      <Route
        path="/admin/pricing"
        element={<SuperAdminRoute><PricingAdminPage /></SuperAdminRoute>}
      />
      <Route
        path="/admin/demo-requests"
        element={<SuperAdminRoute><DemoRequestsPage /></SuperAdminRoute>}
      />

      {/* ── Rutas TENANT-SCOPED (bloqueadas para super_admin) ────────── */}
      <Route
        path="/:tenantSlug/dashboard"
        element={<TenantRoute><TenantGuard><DashboardPage /></TenantGuard></TenantRoute>}
      />
      <Route
        path="/:tenantSlug/documents"
        element={<TenantRoute><TenantGuard><DocumentsPage /></TenantGuard></TenantRoute>}
      />
      <Route
        path="/:tenantSlug/upload"
        element={<TenantEditorRoute><TenantGuard><UploadPage /></TenantGuard></TenantEditorRoute>}
      />
      <Route
        path="/:tenantSlug/search"
        element={<TenantRoute><TenantGuard><SearchPage /></TenantGuard></TenantRoute>}
      />
      <Route
        path="/:tenantSlug/categories"
        element={<TenantAdminRoute><TenantGuard><CategoriesPage /></TenantGuard></TenantAdminRoute>}
      />
      <Route
        path="/:tenantSlug/users"
        element={<TenantAdminRoute><TenantGuard><UsersPage /></TenantGuard></TenantAdminRoute>}
      />
      <Route
        path="/:tenantSlug/audit"
        element={<TenantAdminRoute><TenantGuard><AuditPage /></TenantGuard></TenantAdminRoute>}
      />
      <Route
        path="/:tenantSlug/risk-rules"
        element={<TenantAdminRoute><TenantGuard><RiskRulesPage /></TenantGuard></TenantAdminRoute>}
      />
      <Route
        path="/:tenantSlug/plan"
        element={<TenantAdminRoute><TenantGuard><PlanPage /></TenantGuard></TenantAdminRoute>}
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PlanProvider>
          <AppRoutes />
        </PlanProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
