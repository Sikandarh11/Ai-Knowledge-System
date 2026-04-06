// documents.js — All document related API calls
//
// DUMMY DATA: functions return fake data right now
// 🔌 BACKEND: comments show exactly what to uncomment

import axiosInstance from './axiosInstance'

// ─── DUMMY DATA ───────────────────────────────────
// 🔌 BACKEND: delete this block when connecting
const DUMMY_DOCUMENTS = [
  { id: 1, workspace_id: 1, filename: 'research.pdf',    file_type: 'pdf',  created_at: '2024-01-10', chunk_count: 24 },
  { id: 2, workspace_id: 1, filename: 'notes.docx',      file_type: 'docx', created_at: '2024-01-12', chunk_count: 8  },
  { id: 3, workspace_id: 1, filename: 'summary.txt',     file_type: 'txt',  created_at: '2024-01-15', chunk_count: 4  },
  { id: 4, workspace_id: 2, filename: 'paper1.pdf',      file_type: 'pdf',  created_at: '2024-01-20', chunk_count: 32 },
  { id: 5, workspace_id: 2, filename: 'references.docx', file_type: 'docx', created_at: '2024-01-22', chunk_count: 12 },
]
// ── END DUMMY DATA ─────────────────────────────────


// ─── GET documents by workspace ───────────────────
// Backend endpoint: GET /documents?workspace_id={id}
export const getDocuments = async (workspaceId) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 500))
  return DUMMY_DOCUMENTS.filter(d => d.workspace_id === workspaceId)

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.get(`/documents?workspace_id=${workspaceId}`)
  // return response.data
}


// ─── UPLOAD a file ────────────────────────────────
// Backend endpoint: POST /documents/upload
// Uses FormData because we're sending a file
export const uploadDocument = async (workspaceId, file) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 1500)) // simulate upload time
  const newDoc = {
    id: Date.now(),
    workspace_id: workspaceId,
    filename: file.name,
    file_type: file.name.split('.').pop(), // get extension
    created_at: new Date().toISOString(),
    chunk_count: Math.floor(Math.random() * 20) + 1,
  }
  return newDoc

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const formData = new FormData()
  // formData.append('file', file)
  // formData.append('workspace_id', workspaceId)
  // const response = await axiosInstance.post('/documents/upload', formData, {
  //   headers: { 'Content-Type': 'multipart/form-data' }
  // })
  // return response.data
}


// ─── DELETE a document ────────────────────────────
// Backend endpoint: DELETE /documents/{id}
export const deleteDocument = async (id) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 500))
  return { success: true }

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.delete(`/documents/${id}`)
  // return response.data
}