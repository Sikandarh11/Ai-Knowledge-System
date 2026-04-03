// UploadModal.jsx — File upload modal with drag & drop
// Supports: PDF, DOCX, TXT
// Shows upload progress and result
//
// 🔌 BACKEND: on upload calls POST /documents/upload
//    FormData: { file, workspace_id }
//    Returns: { id, filename, file_type, chunk_count, created_at }

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'

const UploadModal = ({
  isOpen,        // show/hide modal
  onClose,       // close modal function
  onUpload,      // called with file after upload succeeds
  workspaceId,   // which workspace to upload to
               // 🔌 BACKEND: sent as workspace_id in FormData
}) => {
  const [file, setFile] = useState(null)       // selected file
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  // uploadStatus: null | 'success' | 'error'

  // ─── Dropzone config ──────────────────────────────
  // react-dropzone handles drag & drop + file selection
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      setUploadStatus('error')
      return
    }
    // Only take first file
    setFile(acceptedFiles[0])
    setUploadStatus(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    // 🔌 BACKEND: these match what extractor.py supports
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,        // one file at a time
    maxSize: 10485760,  // 10MB max
  })

  // ─── Handle upload ────────────────────────────────
  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setUploadStatus(null)

    try {
      // 🔌 BACKEND: onUpload calls uploadDocument() from api/documents.js
      //    which sends POST /documents/upload with FormData
      await onUpload(file)
      setUploadStatus('success')
      // Auto close after success
      setTimeout(() => {
        setFile(null)
        setUploadStatus(null)
        onClose()
      }, 1500)
    } catch (err) {
      setUploadStatus('error')
    } finally {
      setUploading(false)
    }
  }

  // Reset when modal closes
  const handleClose = () => {
    setFile(null)
    setUploadStatus(null)
    onClose()
  }

  // Format file size nicely
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Document"
      size="md"
    >
      <div className="space-y-4">

        {/* ── Dropzone area ──────────────────────── */}
        <div
          {...getRootProps()}
          className={`
            relative rounded-xl p-8
            border-2 border-dashed
            flex flex-col items-center justify-center
            cursor-pointer
            transition-all duration-200
            ${isDragActive
              ? 'border-neon-purple bg-neon-purple/10'
              : file
              ? 'border-green-500/50 bg-green-500/5'
              : 'border-dark-500 hover:border-neon-purple/50 hover:bg-dark-600'
            }
          `}
        >
          <input {...getInputProps()} />

          {/* Icon changes based on state */}
          <div className={`
            w-14 h-14 rounded-2xl mb-4
            flex items-center justify-center
            ${isDragActive ? 'bg-neon-purple/20' : 'bg-dark-600'}
          `}>
            <Upload
              size={24}
              className={isDragActive ? 'text-neon-purple' : 'text-slate-500'}
            />
          </div>

          {isDragActive ? (
            <p className="text-neon-purple font-medium">Drop file here!</p>
          ) : (
            <>
              <p className="text-white font-medium text-sm">
                Drag & drop your file here
              </p>
              <p className="text-slate-500 text-xs mt-1">
                or click to browse
              </p>
            </>
          )}

          {/* Supported formats */}
          {/* 🔌 BACKEND: matches what extractor.py supports */}
          <div className="flex gap-2 mt-4">
            {['PDF', 'DOCX', 'TXT'].map(fmt => (
              <span key={fmt} className="
                px-2 py-0.5 rounded text-xs
                bg-dark-600 border border-dark-500
                text-slate-500
              ">
                {fmt}
              </span>
            ))}
          </div>
        </div>

        {/* ── Selected file preview ──────────────── */}
        {file && (
          <div className="
            flex items-center gap-3 p-3
            bg-dark-600 rounded-xl
            border border-dark-500
          ">
            <div className="w-9 h-9 rounded-lg bg-neon-purple/20 border border-neon-purple/30 flex items-center justify-center">
              <File size={16} className="text-neon-purple" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {file.name}
              </p>
              <p className="text-slate-500 text-xs">
                {formatSize(file.size)}
              </p>
            </div>
            {/* Remove selected file */}
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null) }}
              className="text-slate-500 hover:text-red-400 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* ── Upload status messages ─────────────── */}
        {uploadStatus === 'success' && (
          <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-xl">
            <CheckCircle size={16} className="text-green-400" />
            <p className="text-green-400 text-sm">
              File uploaded and processed successfully!
            </p>
          </div>
        )}
        {uploadStatus === 'error' && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
            <AlertCircle size={16} className="text-red-400" />
            <p className="text-red-400 text-sm">
              Upload failed. Please try again with a valid file.
            </p>
          </div>
        )}

        {/* ── Action buttons ─────────────────────── */}
        <div className="flex gap-3 pt-1">
          <Button
            variant="secondary"
            onClick={handleClose}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleUpload}
            loading={uploading}
            disabled={!file || uploading}
            className="flex-1"
          >
            {uploading ? 'Processing...' : 'Upload & Process'}
          </Button>
        </div>

        {/* Upload explanation */}
        {/* 🔌 BACKEND: explains the ingestion pipeline */}
        <p className="text-slate-600 text-xs text-center">
          File will be extracted → chunked → embedded → stored in vector DB
        </p>

      </div>
    </Modal>
  )
}

export default UploadModal