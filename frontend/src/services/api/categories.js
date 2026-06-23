import client from './client'

export async function getCategories() {
  const { data } = await client.get('/api/v1/categories/')
  return data
}

/** @param {{ name: string, color?: string, description?: string }} categoryData */
export async function createCategory(categoryData) {
  const { data } = await client.post('/api/v1/categories/', categoryData)
  return data
}

/** @param {string} id @param {{ name?, color?, description? }} updates */
export async function updateCategory(id, updates) {
  const { data } = await client.put(`/api/v1/categories/${id}`, updates)
  return data
}

/** @param {string} id */
export async function deleteCategory(id) {
  const { data } = await client.delete(`/api/v1/categories/${id}`)
  return data
}

/** Lista las sugerencias de categorías de la IA (por defecto, pendientes). */
export async function getCategorySuggestions(statusFilter = 'pending') {
  const { data } = await client.get('/api/v1/categories/suggestions', {
    params: { status_filter: statusFilter },
  })
  return data
}

/** Aprueba una sugerencia → crea la categoría. */
export async function approveCategorySuggestion(id) {
  const { data } = await client.post(`/api/v1/categories/suggestions/${id}/approve`)
  return data
}

/** Rechaza una sugerencia. */
export async function rejectCategorySuggestion(id) {
  const { data } = await client.post(`/api/v1/categories/suggestions/${id}/reject`)
  return data
}
