import { Loader2 } from 'lucide-react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="grid min-h-screen place-items-center bg-canvas"><Loader2 className="animate-spin text-pine" /></div>
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}
