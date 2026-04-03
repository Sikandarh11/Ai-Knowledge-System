// CreateWorkspaceModal.jsx — Modal for creating a new workspace
// Has a text input for workspace name
// On submit calls createWorkspace API function
//
// 🔌 BACKEND: on submit calls POST /workspaces
//    Body: { name: "workspace name" }
//    Returns: { id, name, doc_count, created_at }

import { useState } from 'react'
import { Database } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'

const CreateWorkspaceModal = ({
  isOpen,     // show/hide modal
  onClose,    // close modal function
  onCreate,   // called with new workspace data after creation
}) => {
  // Local state for the input field
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // ─── Handle form submit ──────────────────────────
  const handleSubmit = async () => {
    // Basic validation
    if (!name.trim()) {
      setError('Workspace name is required')
      return
    }
    if (name.trim().length < 3) {
      setError('Name must be at least 3 characters')
      return
    }

    setLoading(true)
    setError('')

    try {
      // 🔌 BACKEND: createWorkspace calls POST /workspaces
      //    This is imported and called in HomePage.jsx
      //    We call onCreate() which triggers it from parent
      await onCreate(name.trim())
      setName('')   // reset input
      onClose()     // close modal
    } catch (err) {
      setError('Failed to create workspace. Try again.')
    } finally {
      setLoading(false)
    }
  }

  // Reset state when modal closes
  const handleClose = () => {
    setName('')
    setError('')
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Workspace"
      size="sm"
    >
      <div className="space-y-4">

        {/* ── Icon + Description ─────────────────── */}
        <div className="flex items-center gap-3 p-3 bg-dark-600 rounded-xl border border-dark-500">
          <div className="w-9 h-9 rounded-lg bg-neon-purple/20 border border-neon-purple/30 flex items-center justify-center">
            <Database size={16} className="text-neon-purple" />
          </div>
          <p className="text-slate-400 text-sm">
            A workspace holds all your documents and knowledge for a specific topic.
          </p>
        </div>

        {/* ── Name Input ─────────────────────────── */}
        <div className="space-y-2">
          <label className="text-slate-300 text-sm font-medium">
            Workspace Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              setError('') // clear error on type
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="e.g. Research Papers, Work Docs..."
            className="
              w-full px-4 py-3 rounded-xl
              bg-dark-600
              border border-dark-500
              focus:border-neon-purple
              focus:outline-none
              text-white placeholder-slate-600
              text-sm
              transition-colors duration-200
            "
            autoFocus
          />
          {/* Error message */}
          {error && (
            <p className="text-red-400 text-xs">{error}</p>
          )}
        </div>

        {/* ── Action Buttons ─────────────────────── */}
        <div className="flex gap-3 pt-2">
          <Button
            variant="secondary"
            onClick={handleClose}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={loading}
            className="flex-1"
          >
            Create Workspace
          </Button>
        </div>

      </div>
    </Modal>
  )
}

export default CreateWorkspaceModal