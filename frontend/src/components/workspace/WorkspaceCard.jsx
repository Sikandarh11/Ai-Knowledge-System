// // WorkspaceCard.jsx — Single workspace card
// // Displays workspace name, doc count, created date
// // Has delete button and click to navigate
// //
// // DUMMY DATA: receives workspace object as prop
// // 🔌 BACKEND: workspace data comes from GET /workspaces
// //    Shape: { id, name, doc_count, created_at }

// import { useNavigate } from 'react-router-dom'
// import { Database, FileText, Trash2, ArrowRight, Calendar } from 'lucide-react'
// import Button from '../ui/Button'

// const WorkspaceCard = ({
//   workspace,    // workspace object from API
//   onDelete,     // function called when delete clicked
//   isDeleting,   // true when delete is in progress
// }) => {
//   const navigate = useNavigate()

//   // Format date nicely
//   // 🔌 BACKEND: created_at comes from your DB as ISO string
//   const formatDate = (dateStr) => {
//     return new Date(dateStr).toLocaleDateString('en-US', {
//       month: 'short',
//       day: 'numeric',
//       year: 'numeric'
//     })
//   }

//   return (
//     <div className="
//       bg-dark-700 rounded-2xl p-6
//       border border-dark-500
//       hover:border-neon-purple
//       transition-all duration-300
//       hover:shadow-neon-sm
//       group
//       flex flex-col gap-4
//     ">

//       {/* ── Top: Icon + Name ──────────────────────── */}
//       <div className="flex items-start justify-between">
//         <div className="flex items-center gap-3">
//           {/* Workspace icon */}
//           <div className="
//             w-10 h-10 rounded-xl
//             bg-dark-600
//             border border-dark-500
//             group-hover:border-neon-purple
//             group-hover:bg-neon-purple/10
//             flex items-center justify-center
//             transition-all duration-300
//           ">
//             <Database size={18} className="text-neon-purple" />
//           </div>
//           <div>
//             <h3 className="
//               text-white font-semibold text-base
//               group-hover:text-neon-glow
//               transition-colors duration-200
//             ">
//               {workspace.name}
//             </h3>
//             {/* Created date */}
//             {/* 🔌 BACKEND: workspace.created_at from DB */}
//             <div className="flex items-center gap-1 mt-0.5">
//               <Calendar size={11} className="text-slate-600" />
//               <p className="text-slate-600 text-xs">
//                 {formatDate(workspace.created_at)}
//               </p>
//             </div>
//           </div>
//         </div>

//         {/* Delete button */}
//         {/* 🔌 BACKEND: calls DELETE /workspaces/{id} */}
//         <button
//           onClick={(e) => {
//             e.stopPropagation() // prevent card click
//             onDelete(workspace.id)
//           }}
//           disabled={isDeleting}
//           className="
//             w-8 h-8 rounded-lg
//             text-slate-600
//             hover:text-red-400
//             hover:bg-red-400/10
//             flex items-center justify-center
//             transition-all duration-200
//             opacity-0 group-hover:opacity-100
//             disabled:opacity-50
//           "
//         >
//           <Trash2 size={15} />
//         </button>
//       </div>

//       {/* ── Middle: Stats ─────────────────────────── */}
//       {/* 🔌 BACKEND: workspace.doc_count from GET /workspaces */}
//       <div className="
//         flex items-center gap-2
//         bg-dark-600 rounded-xl p-3
//         border border-dark-500
//       ">
//         <FileText size={15} className="text-neon-cyan" />
//         <span className="text-slate-300 text-sm">
//           {workspace.doc_count}
//         </span>
//         <span className="text-slate-600 text-sm">
//           documents
//         </span>
//       </div>

//       {/* ── Bottom: Open button ───────────────────── */}
//       <button
//         onClick={() => navigate(`/documents?workspace=${workspace.id}`)}
//         className="
//           w-full flex items-center justify-between
//           px-4 py-2.5 rounded-xl
//           bg-dark-600 hover:bg-neon-purple/20
//           border border-dark-500 hover:border-neon-purple
//           text-slate-400 hover:text-neon-glow
//           transition-all duration-200
//           group/btn
//         "
//       >
//         <span className="text-sm font-medium">Open Workspace</span>
//         <ArrowRight
//           size={15}
//           className="group-hover/btn:translate-x-1 transition-transform duration-200"
//         />
//       </button>

//     </div>
//   )
// }

// export default WorkspaceCard




// WorkspaceCard.jsx — Updated to use onOpen prop
import { useNavigate } from 'react-router-dom'
import { Database, FileText, Trash2, ArrowRight, Calendar } from 'lucide-react'

const WorkspaceCard = ({ workspace, onDelete, onOpen, isDeleting }) => {

  const formatDate = (dateStr) => new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  })

  return (
    <div className="
      bg-dark-700 rounded-2xl p-6
      border border-dark-500
      hover:border-neon-purple
      transition-all duration-300
      hover:shadow-neon-sm
      group flex flex-col gap-4
    ">
      {/* ── Top ───────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="
            w-10 h-10 rounded-xl bg-dark-600
            border border-dark-500
            group-hover:border-neon-purple
            group-hover:bg-neon-purple/10
            flex items-center justify-center
            transition-all duration-300
          ">
            <Database size={18} className="text-neon-purple" />
          </div>
          <div>
            <h3 className="text-white font-semibold text-base group-hover:text-neon-glow transition-colors duration-200">
              {workspace.name}
            </h3>
            <div className="flex items-center gap-1 mt-0.5">
              <Calendar size={11} className="text-slate-600" />
              <p className="text-slate-600 text-xs">{formatDate(workspace.created_at)}</p>
            </div>
          </div>
        </div>
        {/* Delete button */}
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(workspace.id) }}
          disabled={isDeleting}
          className="
            w-8 h-8 rounded-lg text-slate-600
            hover:text-red-400 hover:bg-red-400/10
            flex items-center justify-center
            transition-all duration-200
            opacity-0 group-hover:opacity-100
            disabled:opacity-50
          "
        >
          <Trash2 size={15} />
        </button>
      </div>

      {/* ── Doc count ─────────────────────────────── */}
      {/* 🔌 BACKEND: workspace.doc_count from GET /workspaces */}
      <div className="flex items-center gap-2 bg-dark-600 rounded-xl p-3 border border-dark-500">
        <FileText size={15} className="text-neon-cyan" />
        <span className="text-slate-300 text-sm">{workspace.doc_count}</span>
        <span className="text-slate-600 text-sm">documents</span>
      </div>

      {/* ── Open button ───────────────────────────── */}
      <button
        onClick={() => onOpen(workspace)}
        className="
          w-full flex items-center justify-between
          px-4 py-2.5 rounded-xl
          bg-dark-600 hover:bg-neon-purple/20
          border border-dark-500 hover:border-neon-purple
          text-slate-400 hover:text-neon-glow
          transition-all duration-200 group/btn
        "
      >
        <span className="text-sm font-medium">Open Workspace</span>
        <ArrowRight size={15} className="group-hover/btn:translate-x-1 transition-transform duration-200" />
      </button>
    </div>
  )
}

export default WorkspaceCard