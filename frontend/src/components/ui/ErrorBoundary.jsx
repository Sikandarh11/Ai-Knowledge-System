import { Component } from 'react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('UI crash caught by ErrorBoundary:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-dark-900 text-slate-200 flex items-center justify-center px-4">
          <div className="w-full max-w-lg rounded-2xl border border-dark-500 bg-dark-800 p-6 space-y-3">
            <h2 className="text-lg font-semibold text-white">Something went wrong</h2>
            <p className="text-sm text-slate-400">
              A rendering error occurred. Reload the page to continue.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg bg-neon-purple text-white hover:bg-purple-600 transition-colors duration-150"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
