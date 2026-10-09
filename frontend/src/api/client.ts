import axios from 'axios'

export const TOKEN_KEY = 'insightflow_access_token'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY)
      window.dispatchEvent(new Event('insightflow:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail[0]?.msg || 'Please check the form and try again.'
  }
  return 'Unable to complete the request. Please try again.'
}
