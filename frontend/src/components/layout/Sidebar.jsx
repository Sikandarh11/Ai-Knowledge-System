import { NavLink, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Brain, Home, FileText,
  MessageSquare, Settings,
  ChevronRight, Database,
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'

const Sidebar = () => {
  const location = useLocation()
  const navigate = useNavigate()

  // 🔌 BACKEND: activeWorkspace now comes from Context
  // which gets it from GET /workspaces API
  const { activeWorkspace } = useAppContext()

  const NAV_ITEMS = [
    { label: 'Home',      to: '/',          icon: Home,          description: 'All Workspaces' },
    { label: 'Documents', to: activeWorkspace ? `/documents?workspace=${activeWorkspace.id}` : '/', icon: FileText, description: 'Manage files' },
    { label: 'Chat',      to: '/chat',       icon: MessageSquare, description: 'Ask questions'  },
  ]

  const isDocumentsActive = location.pathname === '/documents'

  return (
    <aside className="
      fixed left-0 top-0 h-screen w-64
      bg-dark-800 border-r border-dark-500
      flex flex-col z-40
    ">
      {/* ── Logo ──────────────────────────────────── */}
      <div className="p-6 border-b border-dark-500">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-neon-purple flex items-center justify-center shadow-neon-sm">
            <Brain size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-white font-bold text-sm leading-tight">AI Knowledge</h1>
            <p className="text-slate-500 text-xs">Personal System</p>
          </div>
        </div>
      </div>

      {/* ── Active Workspace ──────────────────────── */}
      {/* 🔌 BACKEND: activeWorkspace from Context → GET /workspaces */}
      <div className="p-4 border-b border-dark-500">
        <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">
          Active Workspace
        </p>
        <div
          onClick={() => navigate('/')}
          className="
            flex items-center gap-2 bg-dark-700
            rounded-lg p-3 border border-dark-500
            cursor-pointer hover:border-neon-purple
            transition-colors duration-200
          "
        >
          <Database size={16} className="text-neon-purple" />
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">
              {/* 🔌 BACKEND: activeWorkspace.name from API */}
              {activeWorkspace?.name || 'No workspace selected'}
            </p>
            <p className="text-slate-500 text-xs">
              {/* 🔌 BACKEND: activeWorkspace.doc_count from API */}
              {activeWorkspace?.doc_count ?? 0} documents
            </p>
          </div>
          <ChevronRight size={14} className="text-slate-500" />
        </div>
      </div>

      {/* ── Nav Links ─────────────────────────────── */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <p className="text-slate-500 text-xs uppercase tracking-wider mb-3">
          Navigation
        </p>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = item.label === 'Documents'
            ? isDocumentsActive
            : location.pathname === item.to

          return (
            <NavLink
              key={item.label}
              to={item.to}
              className={`
                flex items-center gap-3 px-3 py-2.5
                rounded-xl transition-all duration-200 group
                ${isActive
                  ? 'bg-neon-purple text-white shadow-neon-sm'
                  : 'text-slate-400 hover:bg-dark-600 hover:text-white'
                }
              `}
            >
              <Icon size={18} className={isActive ? 'text-white' : 'text-slate-500 group-hover:text-neon-glow'} />
              <div className="flex-1">
                <p className="text-sm font-medium">{item.label}</p>
                <p className={`text-xs ${isActive ? 'text-purple-200' : 'text-slate-600'}`}>
                  {item.description}
                </p>
              </div>
              {isActive && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
            </NavLink>
          )
        })}
      </nav>

      {/* ── Settings ──────────────────────────────── */}
      <div className="p-4 border-t border-dark-500">
        <button className="
          w-full flex items-center gap-3 px-3 py-2.5
          rounded-xl text-slate-400 hover:text-white
          hover:bg-dark-600 transition-all duration-200 group
        ">
          <Settings size={18} className="text-slate-500 group-hover:text-neon-glow" />
          <span className="text-sm font-medium">Settings</span>
        </button>
      </div>
    </aside>
  )
}

export default Sidebar