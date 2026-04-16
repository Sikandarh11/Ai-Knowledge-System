import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { LogIn, UserPlus } from 'lucide-react'
import Button from '../components/ui/Button'
import { loginUser, persistToken, registerUser } from '../api/auth'

const AuthPage = () => {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const isLogin = mode === 'login'

  const handleSubmit = async (event) => {
    event.preventDefault()

    const normalizedEmail = email.trim().toLowerCase()
    const normalizedUsername = username.trim()
    if (!normalizedEmail || !password) {
      toast.error('Email and password are required')
      return
    }

    if (!isLogin && normalizedUsername.length < 3) {
      toast.error('Username must be at least 3 characters')
      return
    }

    try {
      setLoading(true)
      const response = isLogin
        ? await loginUser(normalizedEmail, password)
        : await registerUser(normalizedUsername, normalizedEmail, password)

      persistToken(response)
      toast.success(isLogin ? 'Login successful' : 'Account created successfully')
      navigate('/chat?scope=global')
    } catch (error) {
      const detail = error?.response?.data?.detail
      const fallback = isLogin ? 'Login failed' : 'Registration failed'
      toast.error(typeof detail === 'string' ? detail : fallback)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-dark-700 border border-dark-500 rounded-2xl p-6 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-white">AI Knowledge Auth</h1>
          <p className="text-sm text-slate-400">Connect your frontend with backend authentication</p>
        </div>

        <div className="grid grid-cols-2 gap-2 bg-dark-900 p-1 rounded-xl border border-dark-500">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
              isLogin ? 'bg-neon-purple text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
              !isLogin ? 'bg-neon-purple text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="space-y-2">
              <label className="text-sm text-slate-300" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Your display name"
                className="w-full rounded-xl border border-dark-500 bg-dark-900 px-3 py-2 text-slate-200 outline-none focus:border-neon-purple"
                autoComplete="username"
              />
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm text-slate-300" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-xl border border-dark-500 bg-dark-900 px-3 py-2 text-slate-200 outline-none focus:border-neon-purple"
              autoComplete="email"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm text-slate-300" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="w-full rounded-xl border border-dark-500 bg-dark-900 px-3 py-2 text-slate-200 outline-none focus:border-neon-purple"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full justify-center"
            loading={loading}
            disabled={loading}
          >
            {isLogin ? <LogIn size={16} /> : <UserPlus size={16} />}
            {isLogin ? 'Login' : 'Create Account'}
          </Button>
        </form>
      </div>
    </div>
  )
}

export default AuthPage
