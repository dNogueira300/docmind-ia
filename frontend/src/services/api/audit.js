import client from './client'

/** @param {{ skip?, limit?, action?, user_id?, from_date?, to_date? }} filters */
export async function getAuditLog(filters = {}) {
  const { data } = await client.get('/api/v1/audit-log/', { params: filters })
  return data
}
