// documents.js — All document related API calls
// Backend payloads are normalized to the UI card shape.

import axiosInstance from './axiosInstance'

const inferChunkCount = (content = '') => {
  if (!content.trim()) {
    return 0
  }
  // UI approximation: backend list endpoint does not return chunk metadata yet.
  return Math.max(1, Math.ceil(content.length / 800))
}

const normalizeDocument = (document) => ({
  ...document,
  filename: document.filename || `Document ${document.id}.txt`,
  file_type: document.file_type || 'txt',
  created_at: document.created_at || new Date().toISOString(),
  chunk_count: document.chunk_count ?? inferChunkCount(document.content),
})


// ─── GET documents by workspace ───────────────────
// Backend endpoint: GET /documents?workspace_id={id}
export const getDocuments = async (workspaceId) => {
  const response = await axiosInstance.get(`/documents?workspace_id=${workspaceId}`)
  return response.data.map(normalizeDocument)
}


// ─── UPLOAD a file ────────────────────────────────
// Backend endpoint: POST /documents/upload
// Uses FormData because we're sending a file
export const uploadDocument = async (workspaceId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('workspace_id', String(workspaceId))

  let response
  try {
    response = await axiosInstance.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // Upload can take longer due extraction + chunking + embeddings.
      timeout: 180000,
    })
  } catch (err) {
    const detail = err?.response?.data?.detail
    const timeoutMessage = err?.code === 'ECONNABORTED' ? 'Upload timed out. Please try a smaller file or retry.' : ''
    const message = typeof detail === 'string' && detail.trim()
      ? detail
      : (timeoutMessage || err?.message || 'Upload failed. Please try again.')
    throw new Error(message)
  }

  const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : 'txt'
  return normalizeDocument({
    id: response.data.document_id,
    workspace_id: Number(workspaceId),
    filename: file.name,
    file_type: ext,
    created_at: new Date().toISOString(),
    chunk_count: response.data.chunks ?? 0,
  })
}


// ─── DELETE a document ────────────────────────────
// Backend endpoint: DELETE /documents/{id}
export const deleteDocument = async (id) => {
  const response = await axiosInstance.delete(`/documents/${id}`)
  return response.data
}