// workspaces.js — All workspace related API calls
// Each function = one backend endpoint
//
// DUMMY DATA: all functions return fake data right now
// 🔌 BACKEND: comments show exactly what to uncomment
//    when connecting to your FastAPI backend

import axiosInstance from './axiosInstance'

// ─── DUMMY DATA ───────────────────────────────────
// This is what your real backend will return
// Shape matches your FastAPI response exactly
// 🔌 BACKEND: delete this entire block when connecting
const DUMMY_WORKSPACES = [
  { id: 1, name: 'My Knowledge Base', doc_count: 12, created_at: '2024-01-01' },
  { id: 2, name: 'Research Papers',   doc_count: 5,  created_at: '2024-01-15' },
  { id: 3, name: 'Work Documents',    doc_count: 8,  created_at: '2024-02-01' },
]
// ── END DUMMY DATA ─────────────────────────────────


// ─── GET all workspaces ───────────────────────────
// Backend endpoint: GET /workspaces
export const getWorkspaces = async () => {
  // ── DUMMY VERSION (active right now) ─────────────
  // Simulates a network delay so UI feels realistic
  await new Promise(resolve => setTimeout(resolve, 500))
  return DUMMY_WORKSPACES

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.get('/workspaces')
  // return response.data
}


// ─── CREATE a workspace ───────────────────────────
// Backend endpoint: POST /workspaces
// Body: { name: "My Workspace" }
export const createWorkspace = async (name) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 700))
  const newWorkspace = {
    id: Date.now(),   // fake unique id
    name,
    doc_count: 0,
    created_at: new Date().toISOString(),
  }
  return newWorkspace

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.post('/workspaces', { name })
  // return response.data
}


// ─── DELETE a workspace ───────────────────────────
// Backend endpoint: DELETE /workspaces/{id}
export const deleteWorkspace = async (id) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 500))
  return { success: true }

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.delete(`/workspaces/${id}`)
  // return response.data
}


// ─── GET single workspace ─────────────────────────
// Backend endpoint: GET /workspaces/{id}
export const getWorkspaceById = async (id) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 300))
  return DUMMY_WORKSPACES.find(w => w.id === id) || DUMMY_WORKSPACES[0]

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.get(`/workspaces/${id}`)
  // return response.data
}