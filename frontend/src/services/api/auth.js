import client from './client'

export async function login(email, password) {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
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
