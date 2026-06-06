import client from './client'

export async function getAlerts({ status, alert_type, document_id, skip = 0, limit = 50 } = {}) {
  const { data } = await client.get('/api/v1/alerts/', {
    params: { status, alert_type, document_id, skip, limit },
  })
  return data
}

export async function dismissAlert(alertId) {
  const { data } = await client.patch(`/api/v1/alerts/${alertId}/dismiss`)
  return data
}
