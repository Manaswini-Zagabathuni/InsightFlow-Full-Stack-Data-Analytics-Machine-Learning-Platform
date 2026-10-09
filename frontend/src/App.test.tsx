import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api, TOKEN_KEY } from './api/client'
import { AuthProvider } from './context/AuthContext'

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>)
}

describe('authentication routes', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('renders the login screen', () => {
    renderAt('/login')
    expect(screen.getByRole('heading', { name: 'Sign in to continue' })).toBeTruthy()
  })

  it('renders the registration screen', () => {
    renderAt('/register')
    expect(screen.getByRole('heading', { name: 'Start with InsightFlow' })).toBeTruthy()
  })

  it('redirects unauthenticated users away from protected routes', async () => {
    renderAt('/dashboard')
    expect(await screen.findByRole('heading', { name: 'Sign in to continue' })).toBeTruthy()
  })

  it('restores a persisted session through the current-user endpoint', async () => {
    localStorage.setItem(TOKEN_KEY, 'persisted-token')
    vi.spyOn(api, 'get').mockImplementation(async (url) => {
      if (url === '/users/me') return { data: { id: 'user-1', email: 'ada@example.com', full_name: 'Ada Lovelace', created_at: new Date().toISOString() } } as never
      return { data: { status: 'healthy', service: 'insightflow-api', version: '0.1.0', database: 'connected' } } as never
    })

    renderAt('/dashboard')

    expect(await screen.findByRole('heading', { name: 'Welcome, Ada Lovelace.' })).toBeTruthy()
  })
})
