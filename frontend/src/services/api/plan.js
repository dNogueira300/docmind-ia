import client from './client'

/** Plan vigente, límites, features y uso de la empresa activa. */
export async function getPlan() {
  const { data } = await client.get('/api/v1/organizations/plan')
  return data
}

/** El admin canjea un código de activación → activa el plan. */
export async function activatePlan(code) {
  const { data } = await client.post('/api/v1/organizations/activate', { code })
  return data
}

/** super_admin: genera códigos de activación. */
export async function createActivationCodes({ plan, duration_days = 365, quantity = 1 }) {
  const { data } = await client.post('/api/v1/organizations/activation-codes', {
    plan, duration_days, quantity,
  })
  return data
}

/** super_admin: lista códigos de activación. */
export async function listActivationCodes(onlyUnused = false) {
  const { data } = await client.get('/api/v1/organizations/activation-codes', {
    params: { only_unused: onlyUnused },
  })
  return data
}
