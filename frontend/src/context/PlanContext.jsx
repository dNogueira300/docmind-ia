import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getPlan } from '../services/api/plan'
import { useAuth } from './AuthContext'

const PlanContext = createContext(null)

/**
 * Provee el plan vigente de la organización activa (límites, features, uso).
 * Se usa para ocultar/mostrar features de pago en el frontend. El backend es la
 * fuente de verdad: aunque algo no se oculte, la API rechaza lo que el plan no incluye.
 */
export function PlanProvider({ children }) {
  const { isAuthenticated, isSuperAdmin, activeTenantId } = useAuth()
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(() => {
    // Sin sesión, o super_admin sin empresa activa → no hay plan que mostrar.
    if (!isAuthenticated || (isSuperAdmin && !activeTenantId)) {
      setPlan(null)
      return
    }
    setLoading(true)
    getPlan()
      .then(setPlan)
      .catch(() => setPlan(null))
      .finally(() => setLoading(false))
  }, [isAuthenticated, isSuperAdmin, activeTenantId])

  useEffect(() => { refresh() }, [refresh])

  const features = plan?.features || {}
  const value = {
    plan,
    features,
    loading,
    refresh,
    hasFeature: (f) => !!features[f],
  }
  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>
}

export function usePlan() {
  const ctx = useContext(PlanContext)
  if (!ctx) throw new Error('usePlan debe usarse dentro de PlanProvider')
  return ctx
}
