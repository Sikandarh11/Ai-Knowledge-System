// axiosInstance.js — Base axios configuration
// All API files import axios from HERE, not directly from 'axios'
// Why? Because we configure base URL and headers ONCE here
// instead of repeating it in every single API call
//
// Think of it like a pre-configured phone —
// you just dial the extension, not the full number every time

import axios from 'axios'

// 🔌 BACKEND CONNECTION:
// Always load from VITE_API_BASE_URL only (single source of truth).
const normalizeBaseUrl = (value) => {
  if (!value) return ''

  // Ignore accidental inline comments/spaces in .env values.
  const firstToken = value.trim().split(/\s+/)[0]
  const candidate = firstToken.replace(/\/+$/, '')

  try {
    return new URL(candidate).toString().replace(/\/$/, '')
  } catch {
    return ''
  }
}

const ENV_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)
const BASE_URL = ENV_BASE_URL
console.log(`🔌 API Base URL: ${BASE_URL || 'NOT SET'} (from VITE_API_BASE_URL)`)
console.log(`⚠️  ${ENV_BASE_URL ? 'Using VITE_API_BASE_URL from env vars.' : 'No valid VITE_API_BASE_URL found.'}`)
if (!ENV_BASE_URL) {
  console.error('Invalid or missing VITE_API_BASE_URL. Example: https://backend-ai-knowledge-system-9jf3.vercel.app')
}

const axiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Request times out after 10 seconds
  timeout: 10000,
})

// ─── Request Interceptor ──────────────────────────
// Runs BEFORE every request is sent
// Good place to add auth tokens later
axiosInstance.interceptors.request.use(
  (config) => {
    if (!BASE_URL) {
      return Promise.reject(new Error('VITE_API_BASE_URL is missing or invalid. Set it in frontend env files.'))
    }

    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    console.log(`📤 API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => Promise.reject(error)
)

// ─── Response Interceptor ─────────────────────────
// Runs AFTER every response comes back
// Good place to handle global errors (401, 500 etc)
axiosInstance.interceptors.response.use(
  (response) => {
    console.log(`📥 API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      localStorage.removeItem('last_activity_at')
      window.dispatchEvent(new Event('auth-changed'))

      // Force navigation to login when session is invalid/expired.
      if (window.location.pathname !== '/auth') {
        window.location.assign('/auth')
      }
    }

    // Log errors clearly in console for debugging.
    const status = error.response?.status
    const url = error.config?.url
    const detail = error.response?.data?.detail
    const message = error.message
    console.error(`❌ API Error: ${status} ${url} ${detail || message || ''}`)
    return Promise.reject(error)
  }
)

export default axiosInstance