import client from './client'

/** @param {{ skip?, limit?, status?, category_id?, file_type?, from_date?, to_date? }} filters */
export async function getDocuments(filters = {}) {
  const { data } = await client.get('/api/v1/documents/', { params: filters })
  return data
}

/** @param {File} file */
export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await client.post('/api/v1/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/** @param {string} q */
export async function searchDocuments(q, skip = 0, limit = 20) {
  const { data } = await client.get('/api/v1/documents/search', {
    params: { q, skip, limit },
  })
  return data
}

/** @param {string} id */
export async function getDocument(id) {
  const { data } = await client.get(`/api/v1/documents/${id}`)
  return data
}

/** @param {string} id */
export async function getDownloadUrl(id) {
  const { data } = await client.get(`/api/v1/documents/${id}/download-url`)
  return data // { download_url, expires_in_seconds } — URL ya generada con localhost:9000
}

/** @param {string} id @param {string} categoryId */
export async function reclassifyDocument(id, categoryId) {
  const { data } = await client.put(`/api/v1/documents/${id}/category`, {
    category_id: categoryId,
  })
  return data
}

/** @param {string} id */
export async function deleteDocument(id) {
  const { data } = await client.delete(`/api/v1/documents/${id}`)
  return data
}
