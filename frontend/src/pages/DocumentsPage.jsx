// DocumentsPage.jsx — Shows documents for a workspace
// Features:
//   - List all documents in selected workspace
//   - Upload new document via modal
//   - Delete document
//   - Shows which workspace is selected
//
// DUMMY DATA: documents come from api/documents.js dummy data
// 🔌 BACKEND: all API calls set up in api/documents.js
//    Just uncomment real calls when connecting backend

import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Upload, FileText, ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'
import DocumentCard from '../components/documents/DocumentCard'
import UploadModal from '../components/documents/UploadModal'
import Loader from '../components/ui/Loader'
import Button from '../components/ui/Button'
import { getDocuments, uploadDocument, deleteDocument } from '../api/documents'
import { getWorkspaces } from '../api/workspaces'

const DocumentsPage = () => {
  const navigate = useNavigate()

  // ─── Get workspace ID from URL ────────────────────
  // When user clicks "Open Workspace" in HomePage
  // URL becomes /documents?workspace=1
  // useSearchParams reads that value
  const [searchParams] = useSearchParams()
  const workspaceId = searchParams.get('workspace')
  // 🔌 BACKEND: workspaceId sent to GET /documents?workspace_id={id}

  // ─── State ────────────────────────────────────────
  const [documents, setDocuments] = useState([])
  const [workspace, setWorkspace] = useState(null)
  // workspace = the currently selected workspace object
  // 🔌 BACKEND: comes from GET /workspaces/{id}

  const [loading, setLoading] = useState(true)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  // ─── Fetch data on page load ──────────────────────
  useEffect(() => {
    if (workspaceId) {
      fetchData()
    } else {
      // No workspace selected — redirect to home
      navigate('/')
    }
  }, [workspaceId])

  const fetchData = async () => {
    try {
      setLoading(true)

      // Fetch documents and workspace info in parallel
      // Promise.all = run both requests at same time (faster)
      const [docs, workspaces] = await Promise.all([
        // 🔌 BACKEND: GET /documents?workspace_id={workspaceId}
        getDocuments(Number(workspaceId)),
        // 🔌 BACKEND: GET /workspaces
        getWorkspaces(),
      ])

      setDocuments(docs)
      // Find the current workspace from the list
      const currentWorkspace = workspaces.find(
        w => w.id === Number(workspaceId)
      )
      setWorkspace(currentWorkspace)
    } catch (err) {
      toast.error('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  // ─── Upload document ──────────────────────────────
  // 🔌 BACKEND: calls POST /documents/upload
  //    FormData: { file, workspace_id }
  const handleUpload = async (file) => {
    try {
      const newDoc = await uploadDocument(Number(workspaceId), file)
      // Add to list without refetching
      setDocuments(prev => [newDoc, ...prev])
      toast.success(`"${file.name}" uploaded successfully!`)
    } catch (err) {
      toast.error('Upload failed. Try again.')
      throw err // re-throw so modal shows error state
    }
  }

  // ─── Delete document ──────────────────────────────
  // 🔌 BACKEND: calls DELETE /documents/{id}
  const handleDelete = async (id) => {
    const doc = documents.find(d => d.id === id)
    try {
      setDeletingId(id)
      await deleteDocument(id)
      setDocuments(prev => prev.filter(d => d.id !== id))
      toast.success(`"${doc?.filename}" deleted`)
    } catch (err) {
      toast.error('Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  // ─── Loading state ────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" text="Loading documents..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ── Page Header ───────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Back to home button */}
          <button
            onClick={() => navigate('/')}
            className="
              w-9 h-9 rounded-xl
              bg-dark-700 border border-dark-500
              hover:border-neon-purple
              flex items-center justify-center
              text-slate-400 hover:text-white
              transition-all duration-200
            "
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            {/* Workspace name */}
            {/* 🔌 BACKEND: workspace.name from GET /workspaces */}
            <h2 className="text-2xl font-bold text-white">
              {workspace?.name || 'Documents'}
            </h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {documents.length} document{documents.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        {/* Upload button */}
        <Button
          variant="primary"
          onClick={() => setUploadModalOpen(true)}
        >
          <Upload size={16} />
          Upload Document
        </Button>
      </div>

      {/* ── Documents List ────────────────────────── */}
      {documents.length === 0 ? (
        // Empty state
        <div className="
          flex flex-col items-center justify-center
          h-64 rounded-2xl
          border-2 border-dashed border-dark-500
          text-center space-y-4
        ">
          <div className="w-16 h-16 rounded-2xl bg-dark-700 border border-dark-500 flex items-center justify-center">
            <FileText size={28} className="text-neon-purple" />
          </div>
          <div>
            <p className="text-white font-semibold">No documents yet</p>
            <p className="text-slate-500 text-sm mt-1">
              Upload your first document to start building your knowledge base
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => setUploadModalOpen(true)}
          >
            <Upload size={16} />
            Upload First Document
          </Button>
        </div>
      ) : (
        // Document list
        // 🔌 BACKEND: documents array from GET /documents?workspace_id={id}
        <div className="space-y-3">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDelete={handleDelete}
              isDeleting={deletingId === doc.id}
            />
          ))}
        </div>
      )}

      {/* ── Upload Modal ──────────────────────────── */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUpload={handleUpload}
        workspaceId={workspaceId}
      />

    </div>
  )
}

export default DocumentsPage