import client from './client'

/** Precios públicos de los planes (no requiere autenticación). */
export async function getPricing() {
  const { data } = await client.get('/api/v1/pricing')
  return data
}

/** super_admin: edita el precio de un plan. */
export async function updatePricing(plan, payload) {
  const { data } = await client.put(`/api/v1/pricing/${plan}`, payload)
  return data
}
