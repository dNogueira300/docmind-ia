import client from './client'

/** Chat sobre un documento específico. */
export async function chatWithDocument(documentId, message, history = []) {
  const { data } = await client.post(`/api/v1/chat/${documentId}`, { message, history })
  return data // { reply, history }
}

/** Chat global sobre el sistema (estadísticas, usuarios, documentos, etc.). */
export async function chatGlobal(message, history = []) {
  const { data } = await client.post('/api/v1/chat/global', { message, history })
  return data // { reply, history }
}
