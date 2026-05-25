import client from './client'

/**
 * Login multi-tenant.
 * @param {string} email
 * @param {string} password
 * @param {string|null} orgSlug — Slug de la empresa. Obligatorio para usuarios
 *   regulares (admin/editor/consultor). Para super_admin debe ser null.
 */
export async function login(email, password, orgSlug = null) {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
  if (orgSlug) params.append('org_slug', orgSlug)

  const { data } = await client.post('/api/v1/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data // { access_token, token_type }
}

export async function logout() {
  await client.post('/api/v1/auth/logout')
}

export async function getMe() {
  const { data } = await client.get('/api/v1/auth/me')
  return data
}
