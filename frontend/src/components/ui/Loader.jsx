// Loader.jsx — Reusable loading spinner
// Used when: fetching data, uploading files, waiting for AI response
// Why separate component? So we have one consistent spinner everywhere

const Loader = ({
  size = 'md',       // sm | md | lg
  text = '',         // optional text below spinner
  fullScreen = false // true = covers whole page, false = inline
}) => {

  // ─── Size options ─────────────────────────────────
  const sizes = {
    sm: 'h-5 w-5 border-2',
    md: 'h-8 w-8 border-2',
    lg: 'h-12 w-12 border-4',
  }

  const spinner = (
    <div className="flex flex-col items-center gap-3">
      {/* 
        The spinner ring:
        - rounded-full = circle shape
        - border-dark-500 = gray base ring
        - border-t-neon-purple = purple top segment that spins
        - animate-spin = Tailwind spinning animation
      */}
      <div
        className={`
          ${sizes[size]}
          rounded-full
          border-dark-500
          border-t-neon-purple
          animate-spin
        `}
      />
      {/* Optional loading text */}
      {text && (
        <p className="text-slate-400 text-sm animate-pulse">
          {text}
        </p>
      )}
    </div>
  )

  // ─── Full screen mode ─────────────────────────────
  // Covers the whole page with dark overlay
  // Used when loading initial page data
  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-dark-900 flex items-center justify-center z-50">
        {spinner}
      </div>
    )
  }

  // ─── Inline mode ──────────────────────────────────
  // Just the spinner, inline with content
  return spinner
}

export default Loader