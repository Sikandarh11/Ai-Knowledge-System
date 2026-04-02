// Button.jsx — Reusable button component
// Used everywhere: forms, modals, actions
// Why reusable? So every button looks consistent
// Instead of repeating 10 tailwind classes every time,
// we just write <Button>Click me</Button>

const Button = ({
  children,        // text or icon inside the button
  onClick,         // function to call when clicked
  variant = 'primary',  // style variant: primary | secondary | danger | ghost
  size = 'md',          // size: sm | md | lg
  disabled = false,     // disable the button
  loading = false,      // show loading spinner inside button
  className = '',       // extra classes from outside if needed
  type = 'button',      // html button type
}) => {

  // ─── Style variants ───────────────────────────────
  // Each variant has different colors
  // primary = neon purple (main actions)
  // secondary = dark with border (secondary actions)
  // danger = red (delete actions)
  // ghost = transparent (subtle actions)
  const variants = {
    primary: `
      bg-neon-purple hover:bg-purple-600
      text-white
      shadow-neon-sm hover:shadow-neon-md
      border border-purple-500
    `,
    secondary: `
      bg-dark-600 hover:bg-dark-500
      text-slate-200
      border border-dark-500 hover:border-neon-purple
    `,
    danger: `
      bg-red-600 hover:bg-red-700
      text-white
      border border-red-500
    `,
    ghost: `
      bg-transparent hover:bg-dark-600
      text-slate-300 hover:text-white
      border border-transparent hover:border-dark-500
    `,
  }

  // ─── Size variants ────────────────────────────────
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        ${variants[variant]}
        ${sizes[size]}
        rounded-lg font-medium
        transition-all duration-200
        flex items-center gap-2
        cursor-pointer
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
    >
      {/* Show spinner when loading */}
      {loading && (
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12" cy="12" r="10"
            stroke="currentColor" strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v8z"
          />
        </svg>
      )}
      {/* Button text or icon passed as children */}
      {children}
    </button>
  )
}

export default Button