import { BarChart3, FolderKanban, LayoutDashboard, LogOut } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const signOut = async () => { await logout(); navigate('/login', { replace: true }) }
  const navigation = [['/dashboard', 'Overview', LayoutDashboard], ['/projects', 'Projects', FolderKanban]] as const

  return <div className="min-h-screen bg-canvas">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-[#153f32] p-5 text-white lg:flex">
      <div className="mb-10 flex items-center gap-3 px-2"><div className="grid h-10 w-10 place-items-center rounded-xl bg-mint text-pine"><BarChart3 size={21} /></div><div><div className="display font-extrabold">InsightFlow</div><div className="text-[10px] uppercase tracking-[.2em] text-white/40">Analytics workspace</div></div></div>
      <nav className="space-y-1">{navigation.map(([to, label, Icon]) => <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? 'bg-white/12 text-white' : 'text-white/55 hover:bg-white/5 hover:text-white'}`}><Icon size={18} />{label}</NavLink>)}</nav>
      <div className="mt-auto"><div className="mb-3 rounded-xl border border-white/10 bg-white/5 p-3"><div className="truncate text-sm font-semibold">{user?.full_name}</div><div className="truncate text-xs text-white/40">{user?.email}</div></div><button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:bg-white/5 hover:text-white" onClick={signOut}><LogOut size={17} />Sign out</button></div>
    </aside>
    <div className="lg:pl-64"><header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-black/5 bg-white/85 px-3 backdrop-blur sm:px-5 md:px-8"><div className="display hidden font-extrabold sm:block lg:hidden">InsightFlow</div><nav aria-label="Primary navigation" className="flex gap-1 lg:hidden">{navigation.map(([to, label]) => <NavLink className={({ isActive }) => `rounded-lg px-2 py-2 text-xs font-semibold sm:px-3 ${isActive ? 'bg-pine text-white' : 'text-black/45'}`} key={to} to={to}>{label}</NavLink>)}</nav><button aria-label="Sign out" className="btn-secondary ml-auto flex px-3 lg:hidden" onClick={signOut}><LogOut size={16} /><span className="sr-only">Sign out</span></button></header><main className="p-5 md:p-8"><Outlet /></main></div>
  </div>
}
