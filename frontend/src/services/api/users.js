import client from './client'

export async function getUsers() {
  const { data } = await client.get('/api/v1/users/')
  return data
}

export async function getGlobalAdmins(skip = 0, limit = 100) {
  const { data } = await client.get('/api/v1/users/global-admins', { params: { skip, limit } })
  return data
}

/** @param {{ organization_id, name, email, password }} payload */
export async function createGlobalAdmin(payload) {
  const { data } = await client.post('/api/v1/users/global-admins', payload)
  return data
}

/** @param {string} id @param {{ name?, email? }} payload */
export async function updateGlobalAdmin(id, payload) {
  const { data } = await client.put(`/api/v1/users/global-admins/${id}`, payload)
  return data
}

/** @param {string} id @param {string} newPassword */
export async function changeGlobalAdminPassword(id, newPassword) {
  const { data } = await client.patch(`/api/v1/users/global-admins/${id}/password`, {
    new_password: newPassword,
  })
  return data
}

/** @param {string} id */
export async function deactivateGlobalAdmin(id) {
  const { data } = await client.patch(`/api/v1/users/global-admins/${id}/deactivate`)
  return data
}

/** @param {string} id */
export async function activateGlobalAdmin(id) {
  const { data } = await client.patch(`/api/v1/users/global-admins/${id}/activate`)
  return data
}

/** @param {{ name: string, email: string, password: string, role: string }} userData */
export async function createUser(userData) {
  const { data } = await client.post('/api/v1/users/', userData)
  return data
}

/** @param {string} id @param {{ name?, role?, active? }} updates */
export async function updateUser(id, updates) {
  const { data } = await client.patch(`/api/v1/users/${id}`, updates)
  return data
}
