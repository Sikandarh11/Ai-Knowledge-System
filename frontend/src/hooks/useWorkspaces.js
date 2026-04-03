// useWorkspaces.js — Custom hook for workspace operations
// Thin wrapper around AppContext workspace data
// Makes component code cleaner and more readable
//
// Usage in any component:
// const { workspaces, loading, create, remove } = useWorkspaces()

import { useAppContext } from '../context/AppContext'

const useWorkspaces = () => {
  const {
    workspaces,
    workspacesLoading,
    activeWorkspace,
    setActiveWorkspace,
    createWorkspace,
    deleteWorkspace,
    refreshWorkspaces,
  } = useAppContext()

  return {
    workspaces,
    loading: workspacesLoading,
    activeWorkspace,
    setActiveWorkspace,
    create: createWorkspace,
    remove: deleteWorkspace,
    refresh: refreshWorkspaces,
  }
}

export default useWorkspaces