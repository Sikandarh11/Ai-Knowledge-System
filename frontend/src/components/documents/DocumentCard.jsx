// DocumentCard.jsx — Single document row/card
// Shows: filename, file type badge, chunk count, date, delete button
//
// DUMMY DATA: receives document object as prop
// 🔌 BACKEND: document data comes from GET /documents?workspace_id={id}
//    Shape: { id, workspace_id, filename, file_type, created_at, chunk_count }

import { FileText, File, FileType, Trash2, Calendar, Layers } from 'lucide-react'

// ─── File type config ─────────────────────────────
// Each file type has its own color and icon
const FILE_TYPE_CONFIG = {
  pdf: {
    color: 'text-red-400',
    bg: 'bg-red-400/10',
    border: 'border-red-400/20',
    label: 'PDF',
  },
  docx: {
    color: 'text-blue-400',
    bg: 'bg-blue-400/10',
    border: 'border-blue-400/20',
    label: 'DOCX',
  },
  txt: {
    color: 'text-green-400',
    bg: 'bg-green-400/10',
    border: 'border-green-400/20',
    label: 'TXT',
  },
  // fallback for unknown types
  default: {
    color: 'text-slate-400',
    bg: 'bg-slate-400/10',
    border: 'border-slate-400/20',
    label: 'FILE',
  },
}

const DocumentCard = ({
  document,     // document object from API
  onOpen,       // called when card clicked
  onDelete,     // called when delete clicked
  isDeleting,   // true when delete in progress
}) => {

  // Get file type config or use default
  const typeConfig = FILE_TYPE_CONFIG[document.file_type] || FILE_TYPE_CONFIG.default

  // Format date
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    })
  }

  return (
    <button
      type="button"
      onClick={() => onOpen?.(document)}
      className="
      flex items-center gap-4
      w-full text-left
      p-4 rounded-xl
      bg-dark-700
      border border-dark-500
      hover:border-neon-purple/50
      transition-all duration-200
      group
    ">

      {/* ── File type icon ────────────────────────── */}
      <div className={`
        w-10 h-10 rounded-xl flex-shrink-0
        flex items-center justify-center
        ${typeConfig.bg} border ${typeConfig.border}
      `}>
        <FileText size={18} className={typeConfig.color} />
      </div>

      {/* ── File info ─────────────────────────────── */}
      {/* flex-1 = takes all available space */}
      <div className="flex-1 min-w-0">
        {/* filename — truncate if too long */}
        {/* 🔌 BACKEND: document.filename from DB */}
        <p className="text-white text-sm font-medium truncate">
          {document.filename}
        </p>
        <div className="flex items-center gap-3 mt-1">
          {/* Date */}
          {/* 🔌 BACKEND: document.created_at from DB */}
          <div className="flex items-center gap-1">
            <Calendar size={11} className="text-slate-600" />
            <span className="text-slate-600 text-xs">
              {formatDate(document.created_at)}
            </span>
          </div>
          {/* Chunk count */}
          {/* 🔌 BACKEND: document.chunk_count = chunks stored in ChromaDB */}
          <div className="flex items-center gap-1">
            <Layers size={11} className="text-slate-600" />
            <span className="text-slate-600 text-xs">
              {document.chunk_count} chunks
            </span>
          </div>
        </div>
      </div>

      {/* ── File type badge ───────────────────────── */}
      <span className={`
        px-2.5 py-1 rounded-lg text-xs font-bold
        ${typeConfig.color} ${typeConfig.bg}
        border ${typeConfig.border}
        flex-shrink-0
      `}>
        {typeConfig.label}
      </span>

      {/* ── Delete button ─────────────────────────── */}
      {/* 🔌 BACKEND: calls DELETE /documents/{id} */}
      <button
        onClick={(event) => {
          event.stopPropagation()
          onDelete(document.id)
        }}
        disabled={isDeleting}
        type="button"
        className="
          w-8 h-8 rounded-lg flex-shrink-0
          text-slate-600
          hover:text-red-400
          hover:bg-red-400/10
          flex items-center justify-center
          transition-all duration-200
          opacity-0 group-hover:opacity-100
          disabled:opacity-50
        "
      >
        <Trash2 size={15} />
      </button>

    </button>
  )
}

export default DocumentCard