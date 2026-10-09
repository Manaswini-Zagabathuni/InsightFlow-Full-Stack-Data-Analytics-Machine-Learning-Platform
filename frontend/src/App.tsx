import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppShell } from './components/AppShell'
import { AuthPage } from './pages/AuthPage'
import { Dashboard } from './pages/Dashboard'
import { ProjectDetail } from './pages/ProjectDetail'
import { Projects } from './pages/Projects'

export default function App() {
  return <Routes>
    <Route path="/login" element={<AuthPage mode="login" />} />
    <Route path="/register" element={<AuthPage mode="register" />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
      </Route>
    </Route>
    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes>
}
