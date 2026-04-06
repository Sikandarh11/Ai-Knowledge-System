// Modal.jsx — Reusable popup overlay
// Used for: Create Workspace, Upload File, Confirmations
// Why reusable? Every modal needs the same dark overlay + close on click
// We build the "shell" here, each modal passes its own content as children

import { useEffect } from 'react'
import { X } from 'lucide-react'  // X icon for close button

const Modal = ({
  isOpen,          // boolean — show or hide modal
  onClose,         // function — called when modal closes
  title = '',      // modal header title
  children,        // content inside the modal
  size = 'md',     // sm | md | lg | xl
}) => {

  // ─── Close modal on Escape key ────────────────────
  // Good UX — user can press Esc to close
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEsc)
    }
    // Cleanup — remove listener when modal closes
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  // ─── Prevent body scroll when modal is open ───────
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => { document.body.style.overflow = 'unset' }
  }, [isOpen])

  // ─── Don't render anything if modal is closed ─────
  if (!isOpen) return null

  // ─── Size options ─────────────────────────────────
  const sizes = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-2xl',
  }

  return (
    // ── Dark overlay behind modal ──────────────────
    // fixed inset-0 = covers entire screen
    // z-50 = sits on top of everything
    // clicking the overlay closes the modal
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.7)' }}
      onClick={onClose}
    >
      {/* ── Modal box ─────────────────────────────────
          stopPropagation = clicking INSIDE modal
          doesn't trigger the overlay's onClose
      ─────────────────────────────────────────────── */}
      <div
        className={`
          ${sizes[size]} w-full
          bg-dark-700 rounded-2xl
          border border-dark-500
          shadow-neon-lg
          p-6
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Modal Header ──────────────────────────── */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">
            {title}
          </h2>
          {/* Close button */}
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white
                       hover:bg-dark-600 rounded-lg p-1
                       transition-colors duration-200"
          >
            <X size={20} />
          </button>
        </div>

        {/* ── Modal Content ─────────────────────────── */}
        {/* Whatever is passed between <Modal>...</Modal> renders here */}
        {children}
      </div>
    </div>
  )
}

export default Modal