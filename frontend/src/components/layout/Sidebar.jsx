// Sidebar.jsx — Left navigation panel
// Shows: App logo, navigation links, active workspace info
// Stays fixed on left side — page content scrolls on the right
// 
// DUMMY DATA NOTE:
// - activeWorkspace is hardcoded dummy data
// - 🔌 BACKEND: replace with real workspace from AppContext
//   which will come from GET /workspaces API in Step 4

import { NavLink, useLocation } from 'react-router-dom'
import {
  Brain,        // app logo icon
  Home,         // home page icon
  FileText,     // documents page icon
  MessageSquare, // chat page icon
  Settings,     // settings icon
  ChevronRight, // arrow indicator
  Database,     // workspace icon
} from 'lucide-react'

// ─── Navigation items ─────────────────────────────
// Each item = one link in the sidebar
// 'to' = the route path it navigates to
const NAV_ITEMS = [
  {
    label: 'Home',
    to: '/',
    icon: Home,
    description: 'All Workspaces'
  },
  {
    label: 'Documents',
    to: '/documents',
    icon: FileText,
    description: 'Manage files'
  },
  {
    label: 'Chat',
    to: '/chat',
    icon: MessageSquare,
    description: 'Ask questions'
  },
]

const Sidebar = () => {
  const location = useLocation() // tells us which page we're on

  // ── DUMMY DATA ─────────────────────────────────────
  // 🔌 BACKEND: replace this with selected workspace from
  //    AppContext → comes from GET /workspaces response
  //    It will look like: const { activeWorkspace } = useAppContext()
  const activeWorkspace = {
    name: 'My Knowledge Base',  // dummy workspace name
    docCount: 12,               // dummy document count
  }
  // ── END DUMMY DATA ─────────────────────────────────

  return (
    // fixed = stays in place when page scrolls
    // h-screen = full height of screen
    // w-64 = fixed width sidebar
    <aside className="
      fixed left-0 top-0
      h-screen w-64
      bg-dark-800
      border-r border-dark-500
      flex flex-col
      z-40
    ">

      {/* ── Logo Section ──────────────────────────── */}
      <div className="p-6 border-b border-dark-500">
        <div className="flex items-center gap-3">
          {/* Brain icon as app logo */}
          <div className="
            w-9 h-9 rounded-xl
            bg-neon-purple
            flex items-center justify-center
            shadow-neon-sm
          ">
            <Brain size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-white font-bold text-sm leading-tight">
              AI Knowledge
            </h1>
            <p className="text-slate-500 text-xs">
              Personal System
            </p>
          </div>
        </div>
      </div>

      {/* ── Active Workspace Card ─────────────────── */}
      {/* Shows which workspace is currently selected */}
      {/* 🔌 BACKEND: activeWorkspace comes from GET /workspaces */}
      <div className="p-4 border-b border-dark-500">
        <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">
          Active Workspace
        </p>
        <div className="
          flex items-center gap-2
          bg-dark-700 rounded-lg p-3
          border border-dark-500
          cursor-pointer
          hover:border-neon-purple
          transition-colors duration-200
        ">
          <Database size={16} className="text-neon-purple" />
          <div className="flex-1 min-w-0">
            {/* truncate = cuts off long names with ... */}
            <p className="text-white text-sm font-medium truncate">
              {activeWorkspace.name}
            </p>
            <p className="text-slate-500 text-xs">
              {activeWorkspace.docCount} documents
            </p>
          </div>
          <ChevronRight size={14} className="text-slate-500" />
        </div>
      </div>

      {/* ── Navigation Links ──────────────────────── */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <p className="text-slate-500 text-xs uppercase tracking-wider mb-3">
          Navigation
        </p>

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          // isActive = true when we're on this page
          const isActive = location.pathname === item.to

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={`
                flex items-center gap-3
                px-3 py-2.5 rounded-xl
                transition-all duration-200
                group
                ${isActive
                  ? 'bg-neon-purple text-white shadow-neon-sm'
                  : 'text-slate-400 hover:bg-dark-600 hover:text-white'
                }
              `}
            >
              <Icon
                size={18}
                className={isActive ? 'text-white' : 'text-slate-500 group-hover:text-neon-glow'}
              />
              <div className="flex-1">
                <p className="text-sm font-medium">{item.label}</p>
                <p className={`text-xs ${isActive ? 'text-purple-200' : 'text-slate-600'}`}>
                  {item.description}
                </p>
              </div>
              {/* Active indicator dot */}
              {isActive && (
                <div className="w-1.5 h-1.5 rounded-full bg-white" />
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* ── Bottom Settings ───────────────────────── */}
      <div className="p-4 border-t border-dark-500">
        <button className="
          w-full flex items-center gap-3
          px-3 py-2.5 rounded-xl
          text-slate-400 hover:text-white
          hover:bg-dark-600
          transition-all duration-200
          group
        ">
          <Settings
            size={18}
            className="text-slate-500 group-hover:text-neon-glow"
          />
          <span className="text-sm font-medium">Settings</span>
        </button>
      </div>

    </aside>
  )
}

export default Sidebar