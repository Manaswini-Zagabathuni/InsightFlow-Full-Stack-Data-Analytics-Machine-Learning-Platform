import { FormEvent, useEffect, useId, useMemo, useState } from 'react'
import { BarChart3, Boxes, CircleDot, Clock3, Grid3X3, LineChart as LineIcon, Loader2, PieChart as PieIcon, Save, ScatterChart as ScatterIcon, Trash2 } from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, apiErrorMessage } from '../api/client'
import type { ChartType, Dataset, Visualization, VisualizationResult } from '../types/data'

const COLORS = ['#1d5c45', '#d28a39', '#53798d', '#955e78', '#709e74', '#c65f47', '#735f9b', '#a5a239', '#397c83', '#b4774f']
const CHARTS: { type: ChartType; label: string; icon: typeof BarChart3 }[] = [
  { type: 'bar', label: 'Bar', icon: BarChart3 },
  { type: 'line', label: 'Line', icon: LineIcon },
  { type: 'scatter', label: 'Scatter', icon: ScatterIcon },
  { type: 'histogram', label: 'Histogram', icon: Boxes },
  { type: 'box', label: 'Box plot', icon: CircleDot },
  { type: 'pie', label: 'Donut', icon: PieIcon },
  { type: 'heatmap', label: 'Correlation', icon: Grid3X3 },
]

type Props = { projectId: string; dataset: Dataset }

export function VisualizationStudio({ projectId, dataset }: Props) {
  const numeric = useMemo(() => dataset.columns.filter((column) => column.data_type === 'numeric'), [dataset.columns])
  const [chartType, setChartType] = useState<ChartType>('bar')
  const [name, setName] = useState('')
  const [xAxis, setXAxis] = useState(dataset.columns[0]?.name || '')
  const [yAxis, setYAxis] = useState(numeric[0]?.name || '')
  const [group, setGroup] = useState('')
  const [result, setResult] = useState<VisualizationResult | null>(null)
  const [saved, setSaved] = useState<Visualization[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadSaved = () => api.get<Visualization[]>(`/visualizations/project/${projectId}`).then(({ data }) => setSaved(data))
  useEffect(() => { loadSaved().catch((requestError) => setError(apiErrorMessage(requestError))) }, [projectId])
  useEffect(() => {
    setResult(null); setError(''); setGroup(''); setChartType('bar')
    setXAxis(dataset.columns[0]?.name || ''); setYAxis('')
  }, [dataset.id])

  const chooseChart = (type: ChartType) => {
    setChartType(type); setResult(null); setError(''); setGroup('')
    setXAxis(type === 'scatter' || type === 'histogram' ? numeric[0]?.name || '' : dataset.columns[0]?.name || '')
    setYAxis(['line', 'scatter', 'box'].includes(type) ? numeric[1]?.name || numeric[0]?.name || '' : '')
  }

  const save = async (event: FormEvent) => {
    event.preventDefault(); setLoading(true); setError('')
    try {
      const { data } = await api.post<VisualizationResult>('/visualizations', {
        project_id: projectId,
        dataset_id: dataset.id,
        name: name.trim() || `${CHARTS.find((chart) => chart.type === chartType)?.label} of ${dataset.name}`,
        chart_type: chartType,
        x_axis: chartType === 'heatmap' ? null : xAxis || null,
        y_axis: chartType === 'heatmap' || chartType === 'histogram' ? null : yAxis || null,
        group_column: chartType === 'heatmap' ? null : group || null,
      })
      setResult(data); setName(''); await loadSaved()
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
    finally { setLoading(false) }
  }

  const open = async (visualization: Visualization) => {
    setLoading(true); setError('')
    try {
      const { data } = await api.get<VisualizationResult>(`/visualizations/${visualization.id}`)
      setResult(data); setChartType(visualization.chart_type); setXAxis(visualization.x_axis || ''); setYAxis(visualization.y_axis || ''); setGroup(visualization.group_column || '')
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
    finally { setLoading(false) }
  }

  const remove = async (visualization: Visualization) => {
    if (!window.confirm(`Delete “${visualization.name}”?`)) return
    try {
      await api.delete(`/visualizations/${visualization.id}`)
      if (result?.visualization.id === visualization.id) setResult(null)
      await loadSaved()
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
  }

  const xColumns = chartType === 'scatter' || chartType === 'histogram' ? numeric : dataset.columns
  const yRequired = ['line', 'scatter', 'box'].includes(chartType)
  const yAllowed = !['histogram', 'heatmap'].includes(chartType)
  const axesDisabled = chartType === 'heatmap'

  return <div className="grid gap-5 2xl:grid-cols-[320px_minmax(0,1fr)]">
    <div className="space-y-5">
      <form className="card p-5" onSubmit={save}>
        <div className="flex items-center justify-between"><div><h3 className="display font-bold">Chart builder</h3><p className="mt-1 text-xs text-black/40">Configure from live dataset columns.</p></div><span className="badge bg-pine/[.08] text-pine">{dataset.row_count?.toLocaleString()} rows</span></div>
        <div className="mt-5 grid grid-cols-2 gap-2">{CHARTS.map(({ type, label, icon: Icon }) => <button key={type} type="button" onClick={() => chooseChart(type)} className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-xs font-semibold transition ${chartType === type ? 'border-pine bg-pine/[.07] text-pine ring-1 ring-pine/10' : 'border-black/10 bg-white text-black/55 hover:bg-black/[.02]'}`}><Icon size={16} />{label}</button>)}</div>
        <div className="mt-5 space-y-4">
          <Select label="X-axis" value={axesDisabled ? '' : xAxis} disabled={axesDisabled} required={!axesDisabled && chartType !== 'box'} onChange={setXAxis} columns={xColumns.map((column) => column.name)} placeholder={axesDisabled ? 'Uses all numeric columns' : chartType === 'box' ? 'No grouping' : 'Select a column'} />
          <Select label="Y-axis" value={axesDisabled ? '' : yAxis} disabled={!yAllowed} required={yRequired} onChange={setYAxis} columns={numeric.map((column) => column.name)} placeholder={!yAllowed ? 'Not used for this chart' : chartType === 'bar' || chartType === 'pie' ? 'Count rows' : 'Select a numeric column'} />
          <Select label="Group / color" value={axesDisabled ? '' : group} disabled={axesDisabled} onChange={setGroup} columns={dataset.columns.map((column) => column.name)} placeholder={axesDisabled ? 'Not used for this chart' : 'None'} />
          <div><label className="label" htmlFor="visualization-name">Visualization name</label><input id="visualization-name" className="input" value={name} onChange={(event) => setName(event.target.value)} maxLength={160} placeholder="Optional descriptive name" /></div>
        </div>
        <button className="btn-primary mt-5 w-full" disabled={loading}>{loading ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Generate & save</button>
        <p className="mt-3 text-center text-[11px] leading-relaxed text-black/35">The server validates columns and calculates chart data from the stored CSV.</p>
      </form>
      <div className="card overflow-hidden"><div className="flex items-center gap-2 border-b border-black/5 p-4 text-xs font-bold uppercase tracking-wider text-black/35"><Clock3 size={14} /> Saved visualizations</div>{saved.length ? <div className="max-h-72 divide-y divide-black/5 overflow-auto">{saved.map((visualization) => <div key={visualization.id} className="group flex items-center gap-2 p-3"><button onClick={() => open(visualization)} className="min-w-0 flex-1 text-left"><div className="truncate text-sm font-semibold">{visualization.name}</div><div className="mt-1 text-[11px] capitalize text-black/35">{visualization.chart_type} · {new Date(visualization.created_at).toLocaleDateString()}</div></button><button aria-label={`Delete ${visualization.name}`} onClick={() => remove(visualization)} className="rounded-lg p-2 text-black/25 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 focus:opacity-100"><Trash2 size={15} /></button></div>)}</div> : <p className="p-5 text-sm text-black/40">Saved charts will appear here.</p>}</div>
    </div>
    <div className="card min-h-[640px] overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/5 px-6 py-5"><div><h3 className="display font-bold">{result?.visualization.name || 'Visualization preview'}</h3><p className="mt-1 text-xs text-black/40">{result ? axisSummary(result.visualization) : 'Choose a chart and save it to generate a preview.'}</p></div>{result && <span className="badge bg-black/[.04] capitalize text-black/55">{result.visualization.chart_type}</span>}</div>
      {error ? <div role="alert" className="m-6 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
      <div className="h-[545px] p-5 sm:p-8">{loading ? <div className="grid h-full place-items-center"><Loader2 className="animate-spin text-pine" size={26} /></div> : result ? <ChartRenderer result={result} /> : <EmptyChart />}</div>
    </div>
  </div>
}

function Select({ label, value, columns, placeholder, disabled, required, onChange }: { label: string; value: string; columns: string[]; placeholder: string; disabled?: boolean; required?: boolean; onChange: (value: string) => void }) {
  const id = useId()
  return <div><label className="label" htmlFor={id}>{label}{required ? ' *' : ''}</label><select id={id} className="input disabled:bg-black/[.025] disabled:text-black/35" value={value} disabled={disabled} required={required} onChange={(event) => onChange(event.target.value)}><option value="">{placeholder}</option>{columns.map((column) => <option value={column} key={column}>{column}</option>)}</select></div>
}

function axisSummary(visualization: Visualization) {
  if (visualization.chart_type === 'heatmap') return 'Pearson correlation across all numeric columns'
  const axes = [visualization.x_axis && `X: ${visualization.x_axis}`, visualization.y_axis && `Y: ${visualization.y_axis}`, visualization.group_column && `Color: ${visualization.group_column}`].filter(Boolean)
  return axes.join(' · ')
}

function EmptyChart() { return <div className="grid h-full place-items-center rounded-2xl border border-dashed border-black/10 bg-canvas/60 text-center"><div><BarChart3 className="mx-auto text-pine/25" size={46} /><h4 className="display mt-4 font-bold text-black/65">Build a chart from your dataset</h4><p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-black/40">Every preview is generated from uploaded data. No samples or placeholder values are displayed.</p></div></div> }

export function ChartRenderer({ result }: { result: VisualizationResult }) {
  const { chart_type: type, x_axis: xAxis, y_axis: yAxis } = result.visualization
  const series = (result.meta.series as string[] | undefined) || ['value']
  const tooltipStyle = { borderRadius: 12, border: '1px solid rgba(0,0,0,.08)', boxShadow: '0 8px 25px rgba(0,0,0,.08)', fontSize: 12 }
  const common = <><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,.07)" /><XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={24} /><YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} /></>
  if (type === 'bar' || type === 'histogram') return <ResponsiveContainer width="100%" height="100%"><BarChart data={result.data as Record<string, unknown>[]} margin={{ top: 15, right: 10, bottom: 35, left: 0 }}>{common}{series.map((key, index) => <Bar key={key} dataKey={key} name={key === 'value' ? (yAxis || 'Count') : key} fill={COLORS[index % COLORS.length]} radius={[5, 5, 0, 0]} maxBarSize={60} />)}<text x="50%" y="99%" textAnchor="middle" fontSize="12" fill="rgba(0,0,0,.45)">{xAxis}</text></BarChart></ResponsiveContainer>
  if (type === 'line') return <ResponsiveContainer width="100%" height="100%"><LineChart data={result.data as Record<string, unknown>[]} margin={{ top: 15, right: 20, bottom: 35, left: 0 }}>{common}{series.map((key, index) => <Line key={key} type="monotone" dataKey={key} stroke={COLORS[index % COLORS.length]} strokeWidth={2.5} dot={{ r: 2 }} activeDot={{ r: 5 }} connectNulls />)}<text x="50%" y="99%" textAnchor="middle" fontSize="12" fill="rgba(0,0,0,.45)">{xAxis}</text></LineChart></ResponsiveContainer>
  if (type === 'scatter') {
    const points = result.data as { x: number; y: number; group: string }[]
    const groups = (result.meta.groups as string[]) || ['All']
    return <ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 15, right: 20, bottom: 35, left: 10 }}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,.07)" /><XAxis type="number" dataKey="x" name={xAxis || 'X'} tick={{ fontSize: 11 }} /><YAxis type="number" dataKey="y" name={yAxis || 'Y'} tick={{ fontSize: 11 }} /><Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={tooltipStyle} /><Legend />{groups.map((group, index) => <Scatter key={group} name={group} data={points.filter((point) => point.group === group)} fill={COLORS[index % COLORS.length]} />)}</ScatterChart></ResponsiveContainer>
  }
  if (type === 'pie') {
    const data = result.data as { name: string; value: number }[]
    return <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="47%" innerRadius="35%" outerRadius="72%" paddingAngle={2} labelLine={false} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>{data.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip contentStyle={tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} /></PieChart></ResponsiveContainer>
  }
  if (type === 'box') return <BoxPlot data={result.data as BoxDatum[]} />
  if (type === 'heatmap') return <Heatmap data={result.data as HeatmapData} />
  return <EmptyChart />
}

type BoxDatum = { label: string; minimum: number; q1: number; median: number; q3: number; maximum: number; outliers: number[] }
function BoxPlot({ data }: { data: BoxDatum[] }) {
  if (!data.length) return <NoData />
  const all = data.flatMap((item) => [item.minimum, item.maximum, ...item.outliers]); const min = Math.min(...all); const max = Math.max(...all); const range = max - min || 1
  const y = (value: number) => 440 - ((value - min) / range) * 390
  const width = 900; const spacing = width / data.length
  return <div className="h-full overflow-x-auto"><svg viewBox={`0 0 ${width + 80} 500`} className="h-full min-w-[680px] w-full" role="img" aria-label="Box plot"><line x1="55" y1="50" x2="55" y2="440" stroke="rgba(0,0,0,.18)" />{[0, .25, .5, .75, 1].map((tick) => { const value = min + range * tick; const py = y(value); return <g key={tick}><line x1="55" y1={py} x2={width + 55} y2={py} stroke="rgba(0,0,0,.07)" strokeDasharray="3 3" /><text x="48" y={py + 4} textAnchor="end" fontSize="11" fill="rgba(0,0,0,.45)">{value.toPrecision(4)}</text></g> })}{data.map((item, index) => { const cx = 55 + spacing * index + spacing / 2; const boxWidth = Math.min(54, spacing * .55); return <g key={item.label}><title>{`${item.label}: median ${item.median}, Q1 ${item.q1}, Q3 ${item.q3}`}</title><line x1={cx} y1={y(item.minimum)} x2={cx} y2={y(item.maximum)} stroke="#1d5c45" strokeWidth="2" /><line x1={cx - 13} y1={y(item.minimum)} x2={cx + 13} y2={y(item.minimum)} stroke="#1d5c45" strokeWidth="2" /><line x1={cx - 13} y1={y(item.maximum)} x2={cx + 13} y2={y(item.maximum)} stroke="#1d5c45" strokeWidth="2" /><rect x={cx - boxWidth / 2} y={y(item.q3)} width={boxWidth} height={Math.max(2, y(item.q1) - y(item.q3))} rx="5" fill="#dce9e4" stroke="#1d5c45" strokeWidth="2" /><line x1={cx - boxWidth / 2} y1={y(item.median)} x2={cx + boxWidth / 2} y2={y(item.median)} stroke="#d28a39" strokeWidth="3" />{item.outliers.map((outlier, outlierIndex) => <circle key={outlierIndex} cx={cx + ((outlierIndex % 3) - 1) * 3} cy={y(outlier)} r="2.5" fill="#c65f47" />)}<text x={cx} y="465" textAnchor="middle" fontSize="11" fill="rgba(0,0,0,.55)">{item.label.length > 14 ? `${item.label.slice(0, 12)}…` : item.label}</text></g> })}</svg></div>
}

type HeatmapData = { columns: string[]; cells: { x: string; y: string; value: number | null }[] }
function Heatmap({ data }: { data: HeatmapData }) {
  if (!data.columns.length) return <NoData />
  const values = new Map(data.cells.map((cell) => [`${cell.y}\0${cell.x}`, cell.value]))
  const color = (value: number | null | undefined) => { if (value == null) return '#eef0ee'; const strength = Math.abs(value); return value >= 0 ? `rgba(29,92,69,${.1 + strength * .9})` : `rgba(198,95,71,${.1 + strength * .9})` }
  return <div className="flex h-full flex-col"><div className="mb-4 flex items-center justify-end gap-2 text-[11px] text-black/40"><span>−1</span><span className="h-3 w-24 rounded-full bg-gradient-to-r from-[#c65f47] via-[#eef0ee] to-[#1d5c45]" /><span>+1 correlation</span></div><div className="min-h-0 flex-1 overflow-auto"><div className="grid min-w-[520px] gap-1" style={{ gridTemplateColumns: `minmax(100px, 1fr) repeat(${data.columns.length}, minmax(54px, 1fr))` }}><div />{data.columns.map((column) => <div key={`x-${column}`} className="truncate px-1 pb-2 text-center text-[10px] font-semibold text-black/45" title={column}>{column}</div>)}{data.columns.flatMap((row) => [<div key={`label-${row}`} className="flex items-center truncate pr-2 text-xs font-semibold text-black/50" title={row}>{row}</div>, ...data.columns.map((column) => { const value = values.get(`${row}\0${column}`); return <div key={`${row}-${column}`} className={`grid aspect-square min-h-11 place-items-center rounded-lg text-[11px] font-bold ${value != null && Math.abs(value) > .55 ? 'text-white' : 'text-black/65'}`} style={{ background: color(value) }} title={`${row} × ${column}: ${value ?? 'not available'}`}>{value?.toFixed(2) ?? '—'}</div> })])}</div></div></div>
}

function NoData() { return <div className="grid h-full place-items-center text-sm text-black/40">No plottable values were found for this configuration.</div> }
