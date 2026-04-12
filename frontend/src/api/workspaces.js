// workspaces.js — All workspace related API calls
// Normalizes backend workspace payloads to match current UI expectations.

import axiosInstance from './axiosInstance'

const normalizeWorkspace = (workspace) => ({
  ...workspace,
  // Backend currently does not include doc counts on list endpoint.
  doc_count: workspace.doc_count ?? 0,
  // Keep UI date formatting stable until backend exposes created_at.
  created_at: workspace.created_at ?? new Date().toISOString(),
})


// ─── GET all workspaces ───────────────────────────
// Backend endpoint: GET /workspaces
export const getWorkspaces = async () => {
  const response = await axiosInstance.get('/workspaces')
  const baseWorkspaces = response.data.map(normalizeWorkspace)

  const workspacesWithCounts = await Promise.all(
    baseWorkspaces.map(async (workspace) => {
      try {
        const docsResponse = await axiosInstance.get(`/documents?workspace_id=${workspace.id}`)
        return { ...workspace, doc_count: docsResponse.data.length }
      } catch {
        return { ...workspace, doc_count: 0 }
      }
    })
  )

  return workspacesWithCounts
}


// ─── CREATE a workspace ───────────────────────────
// Backend endpoint: POST /workspaces
// Body: { name: "My Workspace" }
export const createWorkspace = async (name) => {
  const response = await axiosInstance.post('/workspaces', { name })
  return normalizeWorkspace(response.data)
}


// ─── DELETE a workspace ───────────────────────────
// Backend endpoint: DELETE /workspaces/{id}
export const deleteWorkspace = async (id) => {
  const response = await axiosInstance.delete(`/workspaces/${id}`)
  return response.data
}


// ─── GET single workspace ─────────────────────────
// Backend endpoint: not available directly; fetch list and filter.
export const getWorkspaceById = async (id) => {
  const workspaces = await getWorkspaces()
  return workspaces.find((workspace) => workspace.id === id) || null
}