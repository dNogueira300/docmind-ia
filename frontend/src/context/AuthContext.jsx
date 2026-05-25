import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { login as apiLogin, logout as apiLogout, getMe } from '../services/api/auth'
import { listOrganizations } from '../services/api/organizations'
import {
  setToken, clearToken, getToken,
  setActiveTenant, getActiveTenant,
} from '../services/api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [activeTenantId, setActiveTenantIdState] = useState(getActiveTenant())
  // Empresa activa hidratada (objeto completo, no solo el ID). Para usuarios
  // regulares es siempre su propia organización; para super_admin se actualiza
  // cuando entra a una empresa específica vía /:slug/...
  const [activeOrganization, setActiveOrganizationState] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  /* Restaurar sesión al cargar la app */
  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then((me) => {
        setUser(me)
        // Si el usuario regular tiene org, asegurarse de que el tenant header
        // coincida con su empresa. Si es super_admin, mantener el último activo.
        if (me.organization_id && !me.is_super_admin) {
          setActiveTenant(me.organization_id)
          setActiveTenantIdState(me.organization_id)
          setActiveOrganizationState(me.organization)
        }
      })
      .catch(() => {
        clearToken()
        setActiveTenant(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  /**
   * @param {string} email
   * @param {string} password
   * @param {string|null} orgSlug — Slug de la empresa o null para super_admin.
   */
  const login = useCallback(async (email, password, orgSlug = null) => {
    setLoading(true)
    try {
      const { access_token } = await apiLogin(email, password, orgSlug)
      setToken(access_token)
      const me = await getMe()
      setUser(me)

      // Setear tenant activo coherente con el rol
      if (me.is_super_admin) {
        // Super admin: traer la lista de empresas y entrar a la primera
        // activa automáticamente. Esto les da acceso completo a TODOS los
        // módulos (Documentos, Categorías, Usuarios, etc.) sin tener que
        // pasar primero por /admin/organizations.
        try {
          const orgs = await listOrganizations({ include_inactive: false })
          const firstActive = orgs.find((o) => o.active) || orgs[0]
          if (firstActive) {
            setActiveTenant(firstActive.id)
            setActiveTenantIdState(firstActive.id)
            setActiveOrganizationState(firstActive)
            navigate(`/${firstActive.slug}/documents`)
          } else {
            // No hay empresas todavía → ir al panel de gestión para crear una
            setActiveTenant(null)
            setActiveTenantIdState(null)
            setActiveOrganizationState(null)
            navigate('/admin/organizations')
          }
        } catch (e) {
          // Si falla la consulta, caemos al panel de empresas
          setActiveTenant(null)
          setActiveTenantIdState(null)
          setActiveOrganizationState(null)
          navigate('/admin/organizations')
        }
      } else {
        setActiveTenant(me.organization_id)
        setActiveTenantIdState(me.organization_id)
        setActiveOrganizationState(me.organization)
        navigate(`/${me.organization.slug}/documents`)
      }
      return { ok: true, user: me }
    } catch (err) {
      clearToken()
      setActiveTenant(null)
      setUser(null)
      const msg = err.response?.data?.detail || 'Credenciales incorrectas'
      return { ok: false, error: msg }
    } finally {
      setLoading(false)
    }
  }, [navigate])

  const logout = useCallback(async () => {
    // Capturar el slug ANTES de limpiar estado, para regresar al login de la
    // misma empresa del usuario que está cerrando sesión.
    // - Usuario regular  → /{slugDeSuEmpresa}/login
    // - Super admin      → /login (global)
    const isSuper = user?.role === 'super_admin'
    const tenantSlugAtLogout = user?.organization?.slug || null

    try { await apiLogout() } catch (_) {}
    clearToken()
    setActiveTenant(null)
    setActiveTenantIdState(null)
    setActiveOrganizationState(null)
    setUser(null)

    if (!isSuper && tenantSlugAtLogout) {
      navigate(`/${tenantSlugAtLogout}/login`)
    } else {
      navigate('/login')
    }
  }, [navigate, user])

  /** Super admin — cambiar la empresa sobre la que opera (acepta id o objeto). */
  const switchTenant = useCallback((orgOrId) => {
    if (!orgOrId) {
      setActiveTenant(null)
      setActiveTenantIdState(null)
      setActiveOrganizationState(null)
      return
    }
    if (typeof orgOrId === 'string') {
      setActiveTenant(orgOrId)
      setActiveTenantIdState(orgOrId)
      return
    }
    // Es un objeto org completo
    setActiveTenant(orgOrId.id)
    setActiveTenantIdState(orgOrId.id)
    setActiveOrganizationState(orgOrId)
  }, [])

  const isSuperAdmin = user?.role === 'super_admin'
  const isAdmin = user?.role === 'admin' || isSuperAdmin
  const isEditor = user?.role === 'editor' || isAdmin

  // Para usuarios regulares la "empresa visible" es siempre la suya.
  // Para super_admin es la activa (puede ser null en /admin/...).
  const effectiveOrg = isSuperAdmin
    ? activeOrganization
    : (user?.organization || null)

  const value = {
    user,
    loading,
    isSuperAdmin,
    isAdmin,
    isEditor,
    isAuthenticated: !!user,
    organization: user?.organization || null,
    activeOrganization: effectiveOrg,
    tenantSlug: effectiveOrg?.slug || null,
    activeTenantId,
    login,
    logout,
    switchTenant,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * @returns {{
 *   user, loading, isSuperAdmin, isAdmin, isEditor, isAuthenticated,
 *   organization, tenantSlug, activeTenantId,
 *   login, logout, switchTenant
 * }}
 */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
