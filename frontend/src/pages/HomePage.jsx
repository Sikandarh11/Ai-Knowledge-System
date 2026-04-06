// HomePage.jsx — Updated to use AppContext
// No more direct API calls — everything through Context

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Database, Sparkles } from 'lucide-react'
import WorkspaceCard from '../components/workspace/WorkspaceCard'
import CreateWorkspaceModal from '../components/workspace/CreateWorkspaceModal'
import Loader from '../components/ui/Loader'
import Button from '../components/ui/Button'
import { useAppContext } from '../context/AppContext'

const HomePage = () => {
  const navigate = useNavigate()
  const [modalOpen, setModalOpen] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  // 🔌 BACKEND: all data from Context → api/workspaces.js
  const {
    workspaces,
    workspacesLoading,
    createWorkspace,
    deleteWorkspace,
    setActiveWorkspace,
  } = useAppContext()

  // ── Create workspace ───────────────────────────
  // 🔌 BACKEND: POST /workspaces { name }
  const handleCreate = async (name) => {
    await createWorkspace(name)
  }

  // ── Delete workspace ───────────────────────────
  // 🔌 BACKEND: DELETE /workspaces/{id}
  const handleDelete = async (id) => {
    setDeletingId(id)
    await deleteWorkspace(id)
    setDeletingId(null)
  }

  // ── Open workspace ─────────────────────────────
  const handleOpen = (workspace) => {
    // Set as active workspace in Context
    // Sidebar will update automatically
    setActiveWorkspace(workspace)
    navigate(`/documents?workspace=${workspace.id}`)
  }

  if (workspacesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" text="Loading workspaces..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ── Header ────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Your Workspaces</h2>
          <p className="text-slate-500 text-sm mt-1">
            {workspaces.length} workspace{workspaces.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          <Plus size={16} />
          New Workspace
        </Button>
      </div>

      {/* ── Grid or Empty State ───────────────────── */}
      {workspaces.length === 0 ? (
        <div className="
          flex flex-col items-center justify-center h-64
          rounded-2xl border-2 border-dashed border-dark-500
          text-center space-y-4
        ">
          <div className="w-16 h-16 rounded-2xl bg-dark-700 border border-dark-500 flex items-center justify-center">
            <Database size={28} className="text-neon-purple" />
          </div>
          <div>
            <p className="text-white font-semibold">No workspaces yet</p>
            <p className="text-slate-500 text-sm mt-1">
              Create your first workspace to get started
            </p>
          </div>
          <Button variant="primary" onClick={() => setModalOpen(true)}>
            <Plus size={16} /> Create First Workspace
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workspaces.map((workspace) => (
            <WorkspaceCard
              key={workspace.id}
              workspace={workspace}
              onDelete={handleDelete}
              onOpen={handleOpen}
              isDeleting={deletingId === workspace.id}
            />
          ))}
        </div>
      )}

      {/* ── Tips ──────────────────────────────────── */}
      <div className="p-4 rounded-2xl bg-dark-700 border border-dark-500 flex items-start gap-3">
        <Sparkles size={18} className="text-neon-purple mt-0.5" />
        <div>
          <p className="text-slate-300 text-sm font-medium">How it works</p>
          <p className="text-slate-500 text-xs mt-1">
            Create a workspace → Upload documents → Ask questions in Chat.
          </p>
        </div>
      </div>

      <CreateWorkspaceModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  )
}

export default HomePage