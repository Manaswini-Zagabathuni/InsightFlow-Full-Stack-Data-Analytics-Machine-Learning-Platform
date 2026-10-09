import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

export type User = { id: string; email: string; full_name: string; created_at: string }
type Credentials = { email: string; password: string }
type Registration = Credentials & { full_name: string }
type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (credentials: Credentials) => Promise<void>
  register: (registration: Registration) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<User>('/users/me')
      .then(({ data }) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const clearExpiredSession = () => setUser(null)
    window.addEventListener('insightflow:unauthorized', clearExpiredSession)
    return () => window.removeEventListener('insightflow:unauthorized', clearExpiredSession)
  }, [])

  const login = async (credentials: Credentials) => {
    const { data } = await api.post('/auth/login', credentials)
    setUser(data.user)
  }

  const register = async (registration: Registration) => {
    const { data } = await api.post('/auth/register', registration)
    setUser(data.user)
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      setUser(null)
    }
  }

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
