import client from './client'

export async function getApprovals({ status, skip = 0, limit = 20 } = {}) {
  const { data } = await client.get('/api/v1/approvals/', {
    params: { status, skip, limit },
  })
  return data
}

export async function approveDocument(documentId, comment = null) {
  const { data } = await client.post(`/api/v1/approvals/${documentId}/approve`, { comment })
  return data
}

export async function rejectDocument(documentId, comment = null) {
  const { data } = await client.post(`/api/v1/approvals/${documentId}/reject`, { comment })
  return data
}
