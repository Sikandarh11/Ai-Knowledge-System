// Topbar.jsx — Top navigation bar
// Shows: current page title, search bar, action buttons
//
// DUMMY DATA NOTE:
// - pageTitle is passed as a prop from each page
// - workspaceName is dummy hardcoded
// 🔌 BACKEND: workspaceName will come from AppContext
//   which gets it from GET /workspaces API

import { Search, Bell, Plus } from 'lucide-react'
import Button from '../ui/Button'

const Topbar = ({
  title = 'Home',      // page title — passed from each page
  onAction,           // primary action button click handler
  actionLabel = '',   // label for action button e.g. "New Workspace"
  showAction = false, // show or hide the action button
}) => {

  // ── DUMMY DATA ─────────────────────────────────────
  // 🔌 BACKEND: replace with real user/workspace data
  //    from AppContext when backend is connected
  const user = {
    initials: 'AK',    // dummy user initials
  }
  // ── END DUMMY DATA ─────────────────────────────────

  return (
    // ml-64 = pushes topbar to the right of sidebar (sidebar is w-64)
    // fixed = stays at top when page scrolls
    // z-30 = below sidebar (z-40) but above page content
    <header className="
      fixed top-0 right-0
      left-64
      h-16
      bg-dark-800
      border-b border-dark-500
      flex items-center justify-between
      px-6
      z-30
      glass
    ">

      {/* ── Left: Page Title ──────────────────────── */}
      <div>
        <h2 className="text-white font-semibold text-lg">
          {title}
        </h2>
      </div>

      {/* ── Right: Actions ────────────────────────── */}
      <div className="flex items-center gap-3">

        {/* Search bar */}
        {/* 🔌 BACKEND: search will query GET /documents?search=... */}
        <div className="
          flex items-center gap-2
          bg-dark-700 rounded-lg
          border border-dark-500
          px-3 py-2
          hover:border-neon-purple
          transition-colors duration-200
          group
        ">
          <Search size={15} className="text-slate-500 group-hover:text-neon-purple" />
          <input
            type="text"
            placeholder="Search..."
            className="
              bg-transparent outline-none
              text-slate-300 text-sm
              placeholder-slate-600
              w-40
            "
          />
        </div>

        {/* Optional action button — shown on specific pages */}
        {/* e.g. "New Workspace" on HomePage */}
        {showAction && actionLabel && (
          <Button
            variant="primary"
            size="sm"
            onClick={onAction}
          >
            <Plus size={15} />
            {actionLabel}
          </Button>
        )}

        {/* Notification bell */}
        <button className="
          w-9 h-9 rounded-lg
          bg-dark-700 border border-dark-500
          flex items-center justify-center
          text-slate-400 hover:text-white
          hover:border-neon-purple
          transition-colors duration-200
        ">
          <Bell size={17} />
        </button>

        {/* User avatar with initials */}
        {/* 🔌 BACKEND: replace initials with real user data */}
        <div className="
          w-9 h-9 rounded-lg
          bg-neon-purple
          flex items-center justify-center
          shadow-neon-sm
          cursor-pointer
        ">
          <span className="text-white text-xs font-bold">
            {user.initials}
          </span>
        </div>

      </div>
    </header>
  )
}

export default Topbar