import { Activity, ArrowRight, CheckCircle2, Database, FolderKanban, Server } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Project } from '../types/data'

type Health = { status: string; service: string; version: string; database: string }

export function Dashboard() {
  const { user } = useAuth()
  const [health, setHealth] = useState<Health | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  useEffect(() => {
    api.get<Health>('/health').then(({ data }) => setHealth(data)).catch(() => setHealth(null))
    api.get<Project[]>('/projects').then(({ data }) => setProjects(data)).catch(() => setProjects([]))
  }, [])

  return <div className="mx-auto max-w-7xl">
    <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><div className="text-xs font-bold uppercase tracking-[.2em] text-pine">Workspace overview</div><h1 className="display mt-2 text-3xl font-extrabold md:text-4xl">Welcome, {user?.full_name}.</h1><p className="mt-2 text-sm text-black/50">Move from a secure project to a transparent dataset profile.</p></div><Link className="btn-primary" to="/projects">View projects <ArrowRight size={16} /></Link></div>
    <div className="mt-10 grid gap-5 md:grid-cols-3"><Card icon={FolderKanban} title="Projects" value={String(projects.length)} detail="User-owned analysis workspaces" /><Card icon={Server} title="API service" value={health?.status === 'healthy' ? 'Healthy' : 'Checking…'} detail={health ? `${health.service} · v${health.version}` : 'Contacting the API'} /><Card icon={Database} title="Database" value={health?.database === 'connected' ? 'Connected' : 'Checking…'} detail="Verified through SQLAlchemy" /></div>
    <div className="card mt-8 p-6 md:p-8"><div className="flex items-start gap-4"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-pine/10 text-pine"><CheckCircle2 size={21} /></div><div><h2 className="display text-lg font-bold">From raw CSV to reproducible experiment</h2><p className="mt-2 max-w-3xl text-sm leading-relaxed text-black/50">Create a project, profile and explore a secure CSV, build data-driven visualizations, then compare classification, regression, or clustering models in the background Model Lab.</p></div></div></div>
  </div>
}

function Card({ icon: Icon, title, value, detail }: { icon: typeof Activity; title: string; value: string; detail: string }) { return <article className="card p-6"><div className="grid h-10 w-10 place-items-center rounded-xl bg-pine/10 text-pine"><Icon size={19} /></div><div className="mt-6 text-xs font-bold uppercase tracking-wider text-black/35">{title}</div><div className="display mt-1 text-xl font-extrabold">{value}</div><p className="mt-2 text-sm text-black/45">{detail}</p></article> }
