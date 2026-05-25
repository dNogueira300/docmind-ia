import client from './client'

/** Público — resuelve una empresa por slug para mostrar nombre en login. */
export async function getOrganizationBySlug(slug) {
  const { data } = await client.get(`/api/v1/organizations/by-slug/${slug}`)
  return data // { id, name, slug, active }
}

/** Super admin — listar todas las empresas. */
export async function listOrganizations({ include_inactive = false } = {}) {
  const { data } = await client.get('/api/v1/organizations/', {
    params: { include_inactive },
  })
  return data
}

/** Super admin — crear empresa (opcionalmente con admin inicial). */
export async function createOrganization(payload) {
  const { data } = await client.post('/api/v1/organizations/', payload)
  return data
}

/** Super admin — editar empresa (nombre, slug, active). */
export async function updateOrganization(id, payload) {
  const { data } = await client.put(`/api/v1/organizations/${id}`, payload)
  return data
}

/** Super admin — desactivar empresa (no destruye datos). */
export async function deactivateOrganization(id) {
  const { data } = await client.delete(`/api/v1/organizations/${id}`)
  return data
}

/** Super admin — estadísticas globales. */
export async function getOrganizationsStats() {
  const { data } = await client.get('/api/v1/organizations/stats')
  return data
}

/** Super admin — crear admin de una empresa. */
export async function createAdminInOrganization(id, payload) {
  const { data } = await client.post(`/api/v1/organizations/${id}/admin`, payload)
  return data
}
