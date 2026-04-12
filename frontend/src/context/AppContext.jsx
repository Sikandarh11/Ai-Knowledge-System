// AppContext.jsx — Global state for the entire app
// Stores: workspaces, active workspace, loading states
// Why: avoids fetching same data multiple times
// All pages read from here instead of making own API calls
//
// 🔌 BACKEND: all data here comes from real API calls
//    already set up in src/api/ folder

import { createContext, useContext, useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { getCurrentUser } from '../api/auth'
import {
  getWorkspaces,
  createWorkspace,
  deleteWorkspace,
} from '../api/workspaces'

// ─── Create the context ───────────────────────────
// This is the "storage box" all components can access
const AppContext = createContext(null)

const getLastWorkspaceKey = (userId) => `last_active_workspace:${userId || 'anonymous'}`

// ─── Provider component ───────────────────────────
// Wraps the entire app in App.jsx
// Everything inside can access the context
export const AppProvider = ({ children }) => {

  // ── Workspaces state ────────────────────────────
  // 🔌 BACKEND: filled from GET /workspaces
  const [workspaces, setWorkspaces] = useState([])
  const [workspacesLoading, setWorkspacesLoading] = useState(true)

  // ── Active workspace ─────────────────────────────
  // The currently selected workspace
  // Shared across Sidebar, Documents, Chat
  // 🔌 BACKEND: id used in API calls as workspace_id
  const [activeWorkspace, setActiveWorkspace] = useState(null)
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('access_token'))
  const [currentUser, setCurrentUser] = useState(null)

  // Keep token state in sync when login/logout changes localStorage.
  useEffect(() => {
    const syncToken = () => setAuthToken(localStorage.getItem('access_token'))

    window.addEventListener('storage', syncToken)
    window.addEventListener('auth-changed', syncToken)

    return () => {
      window.removeEventListener('storage', syncToken)
      window.removeEventListener('auth-changed', syncToken)
    }
  }, [])

  // ── Fetch workspaces when authenticated ──────────
  // 🔌 BACKEND: GET /workspaces
  useEffect(() => {
    if (!authToken) {
      setWorkspaces([])
      setActiveWorkspace(null)
      setCurrentUser(null)
      setWorkspacesLoading(false)
      return
    }

    fetchCurrentUser()
    fetchWorkspaces()
  }, [authToken])

  useEffect(() => {
    if (!currentUser?.id || !activeWorkspace?.id) {
      return
    }

    try {
      localStorage.setItem(getLastWorkspaceKey(currentUser.id), String(activeWorkspace.id))
    } catch {
      // Persisting the last workspace should never block the UI.
    }
  }, [currentUser?.id, activeWorkspace?.id])

  useEffect(() => {
    if (!currentUser?.id || workspacesLoading || activeWorkspace || workspaces.length === 0) {
      return
    }

    try {
      const savedWorkspaceId = localStorage.getItem(getLastWorkspaceKey(currentUser.id))
      if (savedWorkspaceId) {
        const restoredWorkspace = workspaces.find(
          (workspace) => String(workspace.id) === String(savedWorkspaceId)
        )
        if (restoredWorkspace) {
          setActiveWorkspace(restoredWorkspace)
          return
        }
      }
    } catch {
      // Ignore storage errors and fall back to first workspace.
    }

    setActiveWorkspace(workspaces[0])
  }, [currentUser?.id, workspacesLoading, workspaces, activeWorkspace])

  const fetchCurrentUser = async () => {
    try {
      const data = await getCurrentUser()
      setCurrentUser(data)
    } catch (err) {
      setCurrentUser(null)
    }
  }

  const fetchWorkspaces = async () => {
    try {
      setWorkspacesLoading(true)
      const data = await getWorkspaces()
      setWorkspaces(data)

      if (activeWorkspace) {
        const refreshedActive = data.find((workspace) => workspace.id === activeWorkspace.id)
        if (refreshedActive) {
          setActiveWorkspace(refreshedActive)
        }
      }
    } catch (err) {
      toast.error('Failed to load workspaces')
    } finally {
      setWorkspacesLoading(false)
    }
  }

  // ── Create workspace ─────────────────────────────
  // 🔌 BACKEND: POST /workspaces { name }
  const handleCreateWorkspace = async (name) => {
    try {
      const newWorkspace = await createWorkspace(name)
      setWorkspaces(prev => [newWorkspace, ...prev])
      toast.success(`"${name}" created!`)
      return newWorkspace
    } catch (err) {
      toast.error('Failed to create workspace')
      throw err
    }
  }

  // ── Delete workspace ─────────────────────────────
  // 🔌 BACKEND: DELETE /workspaces/{id}
  const handleDeleteWorkspace = async (id) => {
    const workspace = workspaces.find(w => w.id === id)
    try {
      await deleteWorkspace(id)
      setWorkspaces(prev => prev.filter(w => w.id !== id))

      // If deleted workspace was active, switch to first remaining
      if (activeWorkspace?.id === id) {
        const remaining = workspaces.filter(w => w.id !== id)
        setActiveWorkspace(remaining[0] || null)
      }
      toast.success(`"${workspace?.name}" deleted`)
    } catch (err) {
      toast.error('Failed to delete workspace')
      throw err
    }
  }

  // ── What all components can access ───────────────
  const value = {
    // Data
    workspaces,             // all workspaces array
    workspacesLoading,      // true while fetching
    activeWorkspace,        // currently selected workspace
    currentUser,            // logged in user profile

    // Actions
    setActiveWorkspace,     // select a workspace
    createWorkspace: handleCreateWorkspace,
    deleteWorkspace: handleDeleteWorkspace,
    refreshWorkspaces: fetchWorkspaces,
    refreshCurrentUser: fetchCurrentUser,
  }

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

// ─── Custom hook ──────────────────────────────────
// Instead of importing useContext + AppContext everywhere
// just import useAppContext
// Usage: const { workspaces, activeWorkspace } = useAppContext()
export const useAppContext = () => {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useAppContext must be used inside AppProvider')
  }
  return context
}

export default AppContext