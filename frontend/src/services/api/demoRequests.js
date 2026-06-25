import client from './client'

/** Público: enviar una solicitud de acceso/demo desde la landing. */
export async function createDemoRequest(payload) {
  const { data } = await client.post('/api/v1/demo-requests', payload)
  return data
}

/** super_admin: listar solicitudes. */
export async function listDemoRequests(statusFilter = '') {
  const { data } = await client.get('/api/v1/demo-requests', {
    params: statusFilter ? { status_filter: statusFilter } : {},
  })
  return data
}

/** super_admin: responder una solicitud (simula correo + genera código). */
export async function respondDemoRequest(id, payload) {
  const { data } = await client.post(`/api/v1/demo-requests/${id}/respond`, payload)
  return data
}
