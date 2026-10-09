import { FormEvent, useEffect, useState } from 'react'
import { ArrowRight, FolderKanban, Plus, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, apiErrorMessage } from '../api/client'
import type { Project } from '../types/data'

export function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [error, setError] = useState('')
  const load = () => api.get<Project[]>('/projects').then(({ data }) => setProjects(data)).catch((requestError) => setError(apiErrorMessage(requestError)))
  useEffect(() => { void load() }, [])

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('')
    const form = new FormData(event.currentTarget)
    try {
      await api.post('/projects', { name: form.get('name'), description: form.get('description') })
      setShowCreate(false); load()
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
  }

  return <div className="mx-auto max-w-7xl"><div className="mb-8 flex items-end justify-between gap-4"><div><div className="text-xs font-bold uppercase tracking-[.2em] text-pine">Analysis portfolio</div><h1 className="display mt-2 text-3xl font-extrabold">Projects</h1><p className="mt-2 text-sm text-black/50">Keep each dataset and its analysis context in a private workspace.</p></div><button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={17} /> New project</button></div>
    {error && <div role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>}
    {projects.length ? <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{projects.map((project) => <Link to={`/projects/${project.id}`} key={project.id} className="card group p-6 transition hover:-translate-y-0.5 hover:shadow-md"><div className="flex items-start justify-between"><div className="grid h-11 w-11 place-items-center rounded-xl bg-pine/10 text-pine"><FolderKanban size={21} /></div><ArrowRight size={18} className="text-black/20 transition group-hover:translate-x-1 group-hover:text-pine" /></div><h2 className="display mt-7 text-lg font-bold">{project.name}</h2><p className="mt-2 line-clamp-2 min-h-10 text-sm leading-relaxed text-black/45">{project.description || 'No description provided.'}</p><div className="mt-6 flex justify-between border-t border-black/5 pt-4 text-xs text-black/35"><span>{project.dataset_count} dataset{project.dataset_count === 1 ? '' : 's'}</span><span>{new Date(project.updated_at).toLocaleDateString()}</span></div></Link>)}</div> : <div className="card border-dashed p-14 text-center"><FolderKanban className="mx-auto text-black/15" size={40} /><h2 className="display mt-4 text-lg font-bold">No projects yet</h2><p className="mt-2 text-sm text-black/45">Create a project to upload your first CSV.</p></div>}
    {showCreate && <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowCreate(false) }}><form aria-labelledby="create-project-title" aria-modal="true" role="dialog" className="card w-full max-w-lg p-6" onSubmit={create}><div className="flex items-start justify-between"><div><h2 id="create-project-title" className="display text-xl font-bold">Create project</h2><p className="mt-1 text-sm text-black/45">Name the question or domain you are exploring.</p></div><button type="button" aria-label="Close" onClick={() => setShowCreate(false)}><X size={20} /></button></div><div className="mt-6"><label className="label" htmlFor="name">Project name</label><input autoFocus className="input" id="name" name="name" required maxLength={160} placeholder="Customer retention analysis" /></div><div className="mt-4"><label className="label" htmlFor="description">Description</label><textarea className="input min-h-24 resize-none" id="description" name="description" maxLength={2000} placeholder="What will this project help answer?" /></div><div className="mt-6 flex justify-end gap-3"><button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button><button className="btn-primary">Create project</button></div></form></div>}
  </div>
}
