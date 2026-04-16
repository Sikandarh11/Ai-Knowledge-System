// axiosInstance.js — Base axios configuration
// All API files import axios from HERE, not directly from 'axios'
// Why? Because we configure base URL and headers ONCE here
// instead of repeating it in every single API call
//
// Think of it like a pre-configured phone —
// you just dial the extension, not the full number every time

import axios from 'axios'

// 🔌 BACKEND CONNECTION:
// This reads VITE_API_BASE_URL from your .env file
// Right now .env has: VITE_API_BASE_URL=http://localhost:8000
// When your backend is running, this automatically points to it
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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

    // Log errors clearly in console for debugging
    console.error(`❌ API Error: ${error.response?.status} ${error.config?.url}`)
    return Promise.reject(error)
  }
)

export default axiosInstance