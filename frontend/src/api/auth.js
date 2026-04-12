import axiosInstance from './axiosInstance'

export const registerUser = async (username, email, password) => {
  const response = await axiosInstance.post('/auth/register', {
    username,
    email,
    password,
  })
  return response.data
}

export const loginUser = async (email, password) => {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)

  const response = await axiosInstance.post('/auth/login', body, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })

  return response.data
}

export const persistToken = ({ access_token, token_type }) => {
  localStorage.setItem('access_token', access_token)
  localStorage.setItem('token_type', token_type || 'bearer')
  window.dispatchEvent(new Event('auth-changed'))
}

export const clearToken = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('token_type')
  window.dispatchEvent(new Event('auth-changed'))
}

export const getCurrentUser = async () => {
  const response = await axiosInstance.get('/auth/me')
  return response.data
}
