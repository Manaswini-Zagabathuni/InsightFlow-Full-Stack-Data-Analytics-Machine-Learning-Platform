import { FormEvent, lazy, ReactNode, Suspense, useEffect, useState } from 'react'
import { AlertTriangle, ArrowDown, ArrowLeft, ArrowUp, BarChart3, Bot, BrainCircuit, CheckCircle2, Database, FileText, FileUp, Loader2, Pencil, Search, Table2, Trash2 } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, apiErrorMessage } from '../api/client'
import type { ColumnProfile, Dataset, ProjectDetail as Detail } from '../types/data'

const VisualizationStudio = lazy(() => import('../components/VisualizationStudio').then((module) => ({ default: module.VisualizationStudio })))
const ExperimentStudio = lazy(() => import('../components/ExperimentStudio').then((module) => ({ default: module.ExperimentStudio })))
const AssistantPanel = lazy(() => import('../components/AssistantPanel').then((module) => ({ default: module.AssistantPanel })))
const ReportPanel = lazy(() => import('../components/ReportPanel').then((module) => ({ default: module.ReportPanel })))

export function ProjectDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<Detail | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [tab, setTab] = useState<'profile' | 'explore' | 'visualize' | 'model' | 'reports' | 'assistant'>('profile')
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const load = async () => {
    try {
      const { data } = await api.get<Detail>(`/projects/${id}`)
      setDetail(data)
      setSelectedId((current) => data.datasets.some((dataset) => dataset.id === current) ? current : data.datasets[0]?.id || '')
      setError('')
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
  }
  useEffect(() => { load() }, [id])
  useEffect(() => {
    if (!detail?.datasets.some((dataset) => ['queued', 'profiling'].includes(dataset.status))) return
    const timer = window.setInterval(load, 1800)
    return () => window.clearInterval(timer)
  }, [detail?.datasets.map((dataset) => dataset.status).join(',')])
  const dataset = detail?.datasets.find((item) => item.id === selectedId) || detail?.datasets[0]

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    try { await api.post(`/projects/${id}/datasets`, form); formElement.reset(); await load() }
    catch (requestError) { setError(apiErrorMessage(requestError)) }
  }
  const rename = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    try { await api.patch(`/projects/${id}`, { name: form.get('name') }); setEditing(false); await load() }
    catch (requestError) { setError(apiErrorMessage(requestError)) }
  }
  const remove = async () => {
    if (!window.confirm('Delete this project and all of its datasets? This cannot be undone.')) return
    try { await api.delete(`/projects/${id}`); navigate('/projects', { replace: true }) }
    catch (requestError) { setError(apiErrorMessage(requestError)) }
  }

  if (!detail) return <div className="grid h-72 place-items-center">{error ? <p className="text-sm text-red-600">{error}</p> : <Loader2 className="animate-spin text-pine" />}</div>
  return <div className="mx-auto max-w-7xl"><Link className="mb-5 inline-flex items-center gap-2 text-sm text-black/45 hover:text-pine" to="/projects"><ArrowLeft size={16} /> All projects</Link>
    <div className="flex flex-wrap items-end justify-between gap-4"><div>{editing ? <form className="flex gap-2" onSubmit={rename}><input autoFocus name="name" defaultValue={detail.project.name} className="input max-w-sm" required /><button className="btn-primary">Save</button><button type="button" className="btn-secondary" onClick={() => setEditing(false)}>Cancel</button></form> : <><h1 className="display text-3xl font-extrabold">{detail.project.name}</h1><p className="mt-2 text-sm text-black/45">{detail.project.description || 'Dataset analysis workspace'}</p></>}</div><div className="flex gap-2"><button className="btn-secondary" onClick={() => setEditing(true)}><Pencil size={15} /> Rename</button><button className="btn-secondary text-red-600" onClick={remove}><Trash2 size={15} /> Delete</button></div></div>
    {error && <div role="alert" className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>}
    <div className="mt-8 grid gap-6 xl:grid-cols-[300px_1fr]"><aside className="space-y-5"><form className="card border-dashed p-5" onSubmit={upload}><FileUp className="text-pine" size={25} /><h2 className="display mt-3 font-bold">Upload CSV</h2><p className="mt-1 text-xs leading-relaxed text-black/45">UTF-8 CSV, maximum 25 MB. Profiling runs in the background.</p><input className="mt-4 block w-full text-xs" type="file" name="file" accept=".csv,text/csv" required /><button className="btn-primary mt-4 w-full">Upload & profile</button></form>
      <div className="card overflow-hidden"><div className="border-b border-black/5 p-4 text-xs font-bold uppercase tracking-wider text-black/35">Datasets</div>{detail.datasets.length ? <div className="divide-y divide-black/5">{detail.datasets.map((item) => <button key={item.id} onClick={() => setSelectedId(item.id)} className={`w-full p-4 text-left transition ${item.id === dataset?.id ? 'bg-pine/[.06]' : 'hover:bg-black/[.02]'}`}><div className="truncate text-sm font-semibold">{item.name}</div><div className="mt-2 flex items-center justify-between"><Status value={item.status} /><span className="text-[11px] text-black/35">{formatBytes(item.size_bytes)}</span></div></button>)}</div> : <p className="p-5 text-sm text-black/40">No datasets uploaded.</p>}</div></aside>
      <section className="min-w-0">{dataset ? <>
        <div className="mb-5 flex items-center justify-between"><div><h2 className="display text-xl font-bold">{dataset.name}</h2><p className="mt-1 text-xs text-black/40">{dataset.original_filename}</p></div><Status value={dataset.status} /></div>
        {dataset.status === 'failed' ? <div className="card p-8 text-center text-red-700"><AlertTriangle className="mx-auto" /><p className="mt-3 text-sm">{dataset.profile_error}</p></div> : dataset.status !== 'ready' ? <div className="card p-12 text-center"><Loader2 className="mx-auto animate-spin text-pine" /><h3 className="display mt-4 font-bold">Profiling dataset</h3><p className="mt-2 text-sm text-black/45">Calculating quality, missingness, duplicates, and column distributions.</p></div> : <>
          <div className="mb-5 flex gap-1 overflow-x-auto border-b border-black/10">
            <TabButton active={tab === 'profile'} onClick={() => setTab('profile')} icon={Database} label="Profile" />
            <TabButton active={tab === 'explore'} onClick={() => setTab('explore')} icon={Table2} label="Explore" />
            <TabButton active={tab === 'visualize'} onClick={() => setTab('visualize')} icon={BarChart3} label="Visualize" />
            <TabButton active={tab === 'model'} onClick={() => setTab('model')} icon={BrainCircuit} label="Model Lab" />
            <TabButton active={tab === 'reports'} onClick={() => setTab('reports')} icon={FileText} label="Reports" />
            <TabButton active={tab === 'assistant'} onClick={() => setTab('assistant')} icon={Bot} label="Assistant" />
          </div>
          {tab === 'profile' ? <Profile dataset={dataset} /> : tab === 'explore' ? <Explorer dataset={dataset} /> : tab === 'visualize' ? <LazyFallback><VisualizationStudio projectId={id} dataset={dataset} /></LazyFallback> : tab === 'model' ? <LazyFallback><ExperimentStudio projectId={id} dataset={dataset} /></LazyFallback> : tab === 'reports' ? <LazyFallback><ReportPanel projectId={id} /></LazyFallback> : <LazyFallback><AssistantPanel dataset={dataset} /></LazyFallback>}
        </>}
      </> : <div className="card p-14 text-center"><Database className="mx-auto text-black/15" size={38} /><h2 className="display mt-4 font-bold">Upload a dataset to begin</h2><p className="mt-2 text-sm text-black/45">The original file is preserved while its profile is calculated.</p></div>}</section></div>
  </div>
}

function TabButton({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: typeof Database; label: string }) {
  return <button type="button" aria-current={active ? 'page' : undefined} onClick={onClick} className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-semibold ${active ? 'border-pine text-pine' : 'border-transparent text-black/40'}`}><Icon size={16} /> {label}</button>
}

function LazyFallback({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="card grid h-72 place-items-center"><Loader2 className="animate-spin text-pine" /></div>}>{children}</Suspense>
}

function Status({ value }: { value: string }) { const ready = value === 'ready'; const failed = value === 'failed'; return <span className={`badge ${ready ? 'bg-emerald-50 text-emerald-700' : failed ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>{ready ? <CheckCircle2 size={13} /> : null}{value}</span> }
function formatBytes(bytes: number) { return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB` }

function Profile({ dataset }: { dataset: Dataset }) {
  const metrics = [['Rows', dataset.row_count], ['Columns', dataset.column_count], ['Missing cells', dataset.missing_cells], ['Duplicate rows', dataset.duplicate_rows], ['Memory', formatBytes(dataset.memory_bytes || 0)]]
  return <div className="space-y-6"><div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">{metrics.map(([label, value]) => <div className="card p-4" key={String(label)}><div className="display text-xl font-extrabold">{typeof value === 'number' ? value.toLocaleString() : value}</div><div className="mt-1 text-xs text-black/40">{label}</div></div>)}</div>
    <div className="grid gap-6 lg:grid-cols-[.7fr_1.3fr]"><div className="card p-6"><div className="flex items-center justify-between"><h3 className="display font-bold">Data quality</h3><div className="display text-2xl font-extrabold text-pine">{dataset.quality_score}<span className="text-xs text-black/30">/100</span></div></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-black/5"><div className="h-full rounded-full bg-pine" style={{ width: `${dataset.quality_score}%` }} /></div><ul className="mt-5 space-y-3">{dataset.quality_issues?.map((issue) => <li className="flex gap-2 text-sm leading-relaxed text-black/55" key={issue}><AlertTriangle className="mt-0.5 shrink-0 text-amber" size={15} />{issue}</li>)}</ul><p className="mt-5 border-t border-black/5 pt-4 text-xs leading-relaxed text-black/35">Score starts at 100 and subtracts documented penalties for missing cells, duplicate rows, constant columns, high cardinality, and IQR outliers.</p></div>
      <div className="card overflow-hidden"><div className="border-b border-black/5 p-5"><h3 className="display font-bold">Column statistics</h3></div><div className="max-h-[480px] overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-white text-xs uppercase text-black/35"><tr><th className="p-3">Column</th><th className="p-3">Type</th><th className="p-3">Unique</th><th className="p-3">Missing</th></tr></thead><tbody>{dataset.columns.map((column) => <tr className="border-t border-black/5" key={column.name}><td className="p-3 font-semibold">{column.name}</td><td className="p-3"><span className="badge bg-black/5">{column.data_type}</span></td><td className="p-3">{column.unique_count}</td><td className="p-3"><span className={column.missing_count ? 'font-semibold text-amber-700' : ''}>{column.missing_count} ({column.missing_percentage}%)</span></td></tr>)}</tbody></table></div></div></div></div>
}

function Explorer({ dataset }: { dataset: Dataset }) {
  const [page, setPage] = useState(1); const [search, setSearch] = useState(''); const [sortBy, setSortBy] = useState(''); const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc'); const [data, setData] = useState<{ rows: Record<string, unknown>[]; columns: ColumnProfile[]; total: number; total_pages: number } | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    const timer = window.setTimeout(() => {
      api.get(`/datasets/${dataset.id}/rows`, { signal: controller.signal, params: { page, page_size: 25, search: search || undefined, sort_by: sortBy || undefined, sort_order: sortOrder } })
        .then(({ data }) => setData(data))
        .catch((requestError) => { if (!controller.signal.aborted) setError(apiErrorMessage(requestError)) })
        .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [dataset.id, page, search, sortBy, sortOrder])
  const sort = (column: string) => { if (sortBy === column) setSortOrder((order) => order === 'asc' ? 'desc' : 'asc'); else { setSortBy(column); setSortOrder('asc') }; setPage(1) }
  return <div className="card overflow-hidden"><div className="flex flex-wrap items-center gap-3 border-b border-black/5 p-4"><div className="relative min-w-60 flex-1"><Search className="absolute left-3 top-2.5 text-black/25" size={17} /><label className="sr-only" htmlFor="dataset-search">Search dataset rows</label><input id="dataset-search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} className="input pl-9" placeholder="Search all columns…" /></div><span className="text-xs text-black/35">{data?.total.toLocaleString() || 0} matching rows</span></div>{error && <div role="alert" className="m-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}<div className="overflow-x-auto"><table className="min-w-full whitespace-nowrap text-left text-sm"><caption className="sr-only">Paginated rows from {dataset.name}</caption><thead className="bg-canvas text-xs uppercase text-black/40"><tr>{dataset.columns.map((column) => <th key={column.name} className="p-3"><button className="flex items-center gap-1 font-bold" onClick={() => sort(column.name)}>{column.name}{sortBy === column.name ? sortOrder === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} /> : null}</button><div className="mt-1 font-normal normal-case text-black/30">{column.data_type}</div></th>)}</tr></thead><tbody className={loading ? 'opacity-50' : ''}>{data?.rows.map((row, index) => <tr key={index} className="border-t border-black/5">{dataset.columns.map((column) => { const missing = (row._missing as string[]).includes(column.name); return <td className="max-w-72 truncate p-3" key={column.name}>{missing ? <span className="rounded bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">missing</span> : String(row[column.name])}</td> })}</tr>)}</tbody></table>{loading && <div className="p-8 text-center"><Loader2 className="mx-auto animate-spin text-pine" /></div>}</div><div className="flex items-center justify-between border-t border-black/5 p-4"><button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button><span className="text-xs text-black/40">Page {page} of {data?.total_pages || 1}</span><button className="btn-secondary" disabled={page >= (data?.total_pages || 1)} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>
}
