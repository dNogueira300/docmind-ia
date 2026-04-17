import client from './client'

export async function getUsers() {
  const { data } = await client.get('/api/v1/users/')
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
