// Topbar.jsx — Top navigation bar
// Shows: current page title, search bar, action buttons
//
// DUMMY DATA NOTE:
// - pageTitle is passed as a prop from each page
// - workspaceName is dummy hardcoded
// 🔌 BACKEND: workspaceName will come from AppContext
//   which gets it from GET /workspaces API

import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, Plus, LogOut, ChevronDown } from 'lucide-react'
import Button from '../ui/Button'
import { clearToken } from '../../api/auth'
import { useAppContext } from '../../context/AppContext'

const Topbar = ({
  title = 'Home',      // page title — passed from each page
  onAction,           // primary action button click handler
  actionLabel = '',   // label for action button e.g. "New Workspace"
  showAction = false, // show or hide the action button
}) => {
  const navigate = useNavigate()
  const { currentUser } = useAppContext()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (!menuRef.current?.contains(event.target)) {
        setMenuOpen(false)
      }
    }

    window.addEventListener('mousedown', handleOutsideClick)
    return () => window.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  const userDisplayName = useMemo(() => {
    if (currentUser?.username?.trim()) {
      return currentUser.username.trim()
    }
    if (currentUser?.email?.includes('@')) {
      return currentUser.email.split('@')[0]
    }
    return 'User'
  }, [currentUser])

  const userInitials = useMemo(() => {
    const parts = userDisplayName.split(/\s+/).filter(Boolean)
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return userDisplayName.slice(0, 2).toUpperCase()
  }, [userDisplayName])

  const handleLogout = () => {
    clearToken()
    setMenuOpen(false)
    navigate('/auth', { replace: true })
  }

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

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((prev) => !prev)}
            className="
              h-9 px-2 rounded-lg
              bg-dark-700 border border-dark-500
              flex items-center gap-2
              hover:border-neon-purple
              transition-colors duration-200
            "
          >
            <div className="
              w-7 h-7 rounded-md
              bg-neon-purple
              flex items-center justify-center
              shadow-neon-sm
            ">
              <span className="text-white text-xs font-bold">
                {userInitials}
              </span>
            </div>
            <ChevronDown size={14} className="text-slate-400" />
          </button>

          {menuOpen && (
            <div className="
              absolute right-0 mt-2 w-48
              rounded-xl border border-dark-500
              bg-dark-800 shadow-xl
              overflow-hidden
            ">
              <div className="px-3 py-2 border-b border-dark-500">
                <p className="text-sm font-medium text-white truncate">{userDisplayName}</p>
                <p className="text-xs text-slate-500 truncate">{currentUser?.email || ''}</p>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="
                  w-full px-3 py-2.5
                  flex items-center gap-2
                  text-sm text-slate-200
                  hover:bg-dark-700
                  transition-colors duration-150
                "
              >
                <LogOut size={15} className="text-slate-400" />
                Logout
              </button>
            </div>
          )}
        </div>

      </div>
    </header>
  )
}

export default Topbar