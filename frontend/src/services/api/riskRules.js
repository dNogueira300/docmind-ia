import client from './client'

export async function getRiskRules() {
  const { data } = await client.get('/api/v1/risk-rules/')
  return data
}

export async function createRiskRule(rule) {
  const { data } = await client.post('/api/v1/risk-rules/', rule)
  return data
}

export async function updateRiskRule(id, updates) {
  const { data } = await client.patch(`/api/v1/risk-rules/${id}`, updates)
  return data
}

export async function deleteRiskRule(id) {
  const { data } = await client.delete(`/api/v1/risk-rules/${id}`)
  return data
}
