import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { login as apiLogin, logout as apiLogout, getMe } from '../services/api/auth'
import { setToken, clearToken, getToken } from '../services/api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)   // true mientras se verifica token inicial
  const navigate = useNavigate()

  /* ── Restaurar sesión al cargar la app ─────────────────────
     Si hay un token en localStorage, verificar con /me.
     Si el token expiró el backend responde 401 → el interceptor
     de client.js limpia el token y redirige a /login.
  ─────────────────────────────────────────────────────────── */
  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then((me) => setUser(me))
      .catch(() => {
        clearToken()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (email, password) => {
    setLoading(true)
    try {
      const { access_token } = await apiLogin(email, password)
      setToken(access_token)
      const me = await getMe()
      setUser(me)
      navigate('/documents')
      return { ok: true }
    } catch (err) {
      clearToken()
      setUser(null)
      const msg = err.response?.data?.detail || 'Credenciales incorrectas'
      return { ok: false, error: msg }
    } finally {
      setLoading(false)
    }
  }, [navigate])

  const logout = useCallback(async () => {
    try { await apiLogout() } catch (_) {}
    clearToken()
    setUser(null)
    navigate('/login')
  }, [navigate])

  const value = {
    user,
    loading,
    isAdmin: user?.role === 'admin',
    isEditor: user?.role === 'editor' || user?.role === 'admin',
    isAuthenticated: !!user,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** @returns {{ user, loading, isAdmin, isEditor, isAuthenticated, login, logout }} */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
