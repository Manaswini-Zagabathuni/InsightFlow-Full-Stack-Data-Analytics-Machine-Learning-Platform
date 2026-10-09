import { useEffect, useState } from 'react'
import { Download, FileText, Loader2, RefreshCw, ShieldCheck } from 'lucide-react'
import { api, apiErrorMessage } from '../api/client'
import type { Report } from '../types/data'

export function ReportPanel({ projectId }: { projectId: string }) {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [downloadingId, setDownloadingId] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get<Report[]>(`/reports/project/${projectId}`)
      setReports(data)
    } catch (requestError) {
      setError(apiErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [projectId])

  const generate = async () => {
    setGenerating(true); setError('')
    try {
      await api.post(`/reports/${projectId}`)
      await load()
    } catch (requestError) {
      setError(apiErrorMessage(requestError))
    } finally {
      setGenerating(false)
    }
  }

  const download = async (report: Report) => {
    setDownloadingId(report.id); setError('')
    try {
      const { data } = await api.get<Blob>(`/reports/${report.id}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(data)
      const link = document.createElement('a')
      link.href = url
      link.download = report.filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      setError(apiErrorMessage(requestError))
    } finally {
      setDownloadingId('')
    }
  }

  return <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
    <section className="card overflow-hidden">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-black/5 p-5"><div><h3 className="display font-bold">Project reports</h3><p className="mt-1 text-xs text-black/40">Downloadable snapshots generated from saved project analysis.</p></div><button type="button" className="btn-primary" disabled={generating} onClick={generate}>{generating ? <Loader2 className="animate-spin" size={16} /> : <FileText size={16} />} Generate PDF</button></header>
      {error && <div role="alert" className="m-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {loading ? <div className="grid h-64 place-items-center"><Loader2 className="animate-spin text-pine" /></div> : reports.length ? <div className="divide-y divide-black/5">{reports.map((report) => <div className="flex flex-wrap items-center gap-4 p-5" key={report.id}><div className="grid h-10 w-10 place-items-center rounded-xl bg-pine/10 text-pine"><FileText size={19} /></div><div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{report.filename}</div><div className="mt-1 text-xs text-black/35">{new Date(report.created_at).toLocaleString()} · {formatBytes(report.size_bytes)}</div></div><button type="button" className="btn-secondary" disabled={downloadingId === report.id} onClick={() => download(report)}>{downloadingId === report.id ? <Loader2 className="animate-spin" size={15} /> : <Download size={15} />} Download</button></div>)}</div> : <div className="p-12 text-center"><FileText className="mx-auto text-pine/25" size={42} /><h4 className="display mt-4 font-bold">No reports generated</h4><p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-black/40">Generate a report after profiling data, saving visualizations, and completing experiments.</p></div>}
    </section>
    <aside className="card h-fit p-5"><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-pine"><ShieldCheck size={15} /> Included evidence</div><ul className="mt-4 space-y-3 text-sm leading-relaxed text-black/50"><li>Project and dataset overview</li><li>Data quality and column profiles</li><li>Saved visualization configurations</li><li>Persisted model metrics</li><li>Model-derived feature importance</li><li>Evidence-bounded conclusions</li></ul><p className="mt-5 border-t border-black/5 pt-4 text-xs leading-relaxed text-black/40">Reports do not claim that correlation or feature importance proves causation.</p><button type="button" className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-black/40 hover:text-pine" onClick={load}><RefreshCw size={13} /> Refresh history</button></aside>
  </div>
}

function formatBytes(bytes: number) {
  return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
