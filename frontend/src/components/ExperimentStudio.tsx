import { FormEvent, useEffect, useId, useMemo, useState } from 'react'
import { Activity, Beaker, Check, ChevronRight, Clock3, Info, Lightbulb, Loader2, Play, SlidersHorizontal, Target, TriangleAlert } from 'lucide-react'
import { api, apiErrorMessage } from '../api/client'
import type { Dataset, Experiment, MLTask, ModelCatalog, ModelExplanation, ModelOption } from '../types/data'

const TASKS: { id: MLTask; label: string; description: string }[] = [
  { id: 'classification', label: 'Classification', description: 'Predict a category or class' },
  { id: 'regression', label: 'Regression', description: 'Predict a numeric value' },
  { id: 'clustering', label: 'Clustering', description: 'Discover natural groups' },
]

const EMPTY_CATALOG: ModelCatalog = { classification: [], regression: [], clustering: [] }
const MODEL_NAMES: Record<string, string> = {
  logistic_regression: 'Logistic Regression', decision_tree: 'Decision Tree', random_forest: 'Random Forest', gradient_boosting: 'Gradient Boosting', xgboost: 'XGBoost',
  linear_regression: 'Linear Regression', ridge: 'Ridge', random_forest_regressor: 'Random Forest Regressor', gradient_boosting_regressor: 'Gradient Boosting Regressor', xgboost_regressor: 'XGBoost Regressor',
  kmeans: 'K-Means', dbscan: 'DBSCAN',
}

export function ExperimentStudio({ projectId, dataset }: { projectId: string; dataset: Dataset }) {
  const categorical = useMemo(() => dataset.columns.filter((column) => column.data_type !== 'numeric'), [dataset.columns])
  const numeric = useMemo(() => dataset.columns.filter((column) => column.data_type === 'numeric'), [dataset.columns])
  const [catalog, setCatalog] = useState<ModelCatalog>(EMPTY_CATALOG)
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selected, setSelected] = useState<Experiment | null>(null)
  const [task, setTask] = useState<MLTask>('classification')
  const [target, setTarget] = useState(categorical[0]?.name || '')
  const [features, setFeatures] = useState<string[]>(dataset.columns.filter((column) => column.name !== categorical[0]?.name).map((column) => column.name))
  const [models, setModels] = useState<string[]>([])
  const [numericImputer, setNumericImputer] = useState('median')
  const [scaler, setScaler] = useState('standard')
  const [testSize, setTestSize] = useState('0.2')
  const [clusters, setClusters] = useState('3')
  const [dbscanEps, setDbscanEps] = useState('0.5')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadExperiments = async () => {
    const { data } = await api.get<Experiment[]>(`/experiments/project/${projectId}`)
    setExperiments(data)
    setSelected((current) => current ? data.find((experiment) => experiment.id === current.id) || current : data[0] || null)
    return data
  }

  useEffect(() => {
    setError(''); setSelected(null)
    Promise.all([api.get<ModelCatalog>('/experiments/catalog'), api.get<Experiment[]>(`/experiments/project/${projectId}`)])
      .then(([modelsResponse, experimentsResponse]) => { setCatalog(modelsResponse.data); setExperiments(experimentsResponse.data); setSelected(experimentsResponse.data[0] || null) })
      .catch((requestError) => setError(apiErrorMessage(requestError)))
  }, [projectId, dataset.id])

  const active = experiments.some((experiment) => ['queued', 'training'].includes(experiment.status))
  useEffect(() => {
    if (!active) return
    const timer = window.setInterval(() => loadExperiments().catch(() => undefined), 1800)
    return () => window.clearInterval(timer)
  }, [active, projectId])

  const chooseTask = (next: MLTask) => {
    const nextTarget = next === 'classification' ? categorical[0]?.name || dataset.columns[0]?.name || '' : next === 'regression' ? numeric[numeric.length - 1]?.name || '' : ''
    setTask(next); setTarget(nextTarget); setFeatures(dataset.columns.filter((column) => column.name !== nextTarget).map((column) => column.name)); setModels([]); setError('')
  }

  const changeTarget = (next: string) => {
    setTarget(next); setFeatures((current) => current.filter((feature) => feature !== next))
  }
  const toggleFeature = (column: string) => setFeatures((current) => current.includes(column) ? current.filter((feature) => feature !== column) : [...current, column])
  const toggleModel = (model: ModelOption) => { if (model.available) setModels((current) => current.includes(model.id) ? current.filter((id) => id !== model.id) : [...current, model.id]) }

  const train = async (event: FormEvent) => {
    event.preventDefault(); setLoading(true); setError('')
    try {
      const modelParameters: Record<string, Record<string, number>> = {}
      if (models.includes('kmeans')) modelParameters.kmeans = { n_clusters: Number(clusters) }
      if (models.includes('dbscan')) modelParameters.dbscan = { eps: Number(dbscanEps), min_samples: 5 }
      const { data } = await api.post<Experiment>('/experiments', {
        project_id: projectId, dataset_id: dataset.id, name: name.trim() || `${TASKS.find((item) => item.id === task)?.label} experiment`, task_type: task,
        target_column: task === 'clustering' ? null : target, features, selected_models: models, model_parameters: modelParameters,
        preprocessing: { numeric_imputer: numericImputer, categorical_imputer: 'most_frequent', scaler, categorical_encoder: 'onehot', test_size: Number(testSize) },
      })
      setSelected(data); setName(''); await loadExperiments()
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
    finally { setLoading(false) }
  }

  const targetOptions = task === 'regression' ? numeric : dataset.columns
  return <div className="grid gap-5 2xl:grid-cols-[380px_minmax(0,1fr)]">
    <form className="space-y-5" onSubmit={train}>
      <section className="card p-5"><Step number="1" title="Learning task" /><div className="mt-4 space-y-2">{TASKS.map((item) => <button type="button" key={item.id} onClick={() => chooseTask(item.id)} className={`w-full rounded-xl border p-3 text-left transition ${task === item.id ? 'border-pine bg-pine/[.06] ring-1 ring-pine/10' : 'border-black/10 hover:bg-black/[.02]'}`}><div className={`text-sm font-bold ${task === item.id ? 'text-pine' : ''}`}>{item.label}</div><div className="mt-0.5 text-xs text-black/40">{item.description}</div></button>)}</div></section>
      <section className="card p-5"><Step number="2" title="Data roles" />{task !== 'clustering' && <div className="mt-4"><label className="label" htmlFor="ml-target">Target column</label><select id="ml-target" className="input" value={target} required onChange={(event) => changeTarget(event.target.value)}><option value="">Select target</option>{targetOptions.map((column) => <option key={column.name} value={column.name}>{column.name} · {column.data_type}</option>)}</select></div>}<div className="mt-4"><div className="flex items-center justify-between"><span className="label">Features</span><span className="text-[11px] text-black/35">{features.length} selected</span></div><div className="max-h-48 space-y-1 overflow-auto rounded-xl border border-black/10 p-2">{dataset.columns.filter((column) => column.name !== target).map((column) => <label key={column.name} className="flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 hover:bg-black/[.025]"><input type="checkbox" checked={features.includes(column.name)} onChange={() => toggleFeature(column.name)} className="h-4 w-4 accent-pine" /><span className="min-w-0 flex-1 truncate text-sm font-medium">{column.name}</span><span className="text-[10px] text-black/30">{column.data_type}</span></label>)}</div></div></section>
      <section className="card p-5"><Step number="3" title="Preprocessing" icon={SlidersHorizontal} /><div className="mt-4 grid gap-3 sm:grid-cols-2 2xl:grid-cols-1"><FieldSelect label="Missing numeric values" value={numericImputer} setValue={setNumericImputer} options={[['median', 'Median imputation'], ['mean', 'Mean imputation']]} /><FieldSelect label="Numerical scaling" value={scaler} setValue={setScaler} options={[['standard', 'Standardize'], ['minmax', 'Min-max scale'], ['none', 'No scaling']]} />{task !== 'clustering' && <FieldSelect label="Test partition" value={testSize} setValue={setTestSize} options={[['0.2', '20% test'], ['0.25', '25% test'], ['0.3', '30% test']]} />}</div><div className="mt-3 rounded-xl bg-canvas p-3 text-xs leading-relaxed text-black/45">Categorical values use most-frequent imputation and one-hot encoding. For supervised tasks, every preprocessing step is fitted only on the training partition.</div></section>
      <section className="card p-5"><Step number="4" title="Models" /><div className="mt-4 space-y-2">{catalog[task].map((model) => <label key={model.id} title={model.unavailable_reason || undefined} className={`flex items-center gap-3 rounded-xl border p-3 ${model.available ? 'cursor-pointer hover:bg-black/[.02]' : 'cursor-not-allowed bg-black/[.025] opacity-55'} ${models.includes(model.id) ? 'border-pine bg-pine/[.05]' : 'border-black/10'}`}><input type="checkbox" disabled={!model.available} checked={models.includes(model.id)} onChange={() => toggleModel(model)} className="h-4 w-4 accent-pine" /><span className="flex-1 text-sm font-semibold">{model.name}</span>{models.includes(model.id) && <Check className="text-pine" size={15} />}</label>)}{task === 'clustering' && models.includes('kmeans') && <NumberField label="K-Means clusters" value={clusters} setValue={setClusters} min="2" max="20" step="1" />}{task === 'clustering' && models.includes('dbscan') && <NumberField label="DBSCAN epsilon" value={dbscanEps} setValue={setDbscanEps} min="0.01" max="100" step="0.05" />}</div></section>
      <section className="card p-5"><label className="label" htmlFor="experiment-name">Experiment name</label><input id="experiment-name" className="input" value={name} onChange={(event) => setName(event.target.value)} maxLength={160} placeholder={`${TASKS.find((item) => item.id === task)?.label} experiment`} />{error && <div role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-xs text-red-700">{error}</div>}<button className="btn-primary mt-4 w-full" disabled={loading || !features.length || !models.length || (task !== 'clustering' && !target)}>{loading ? <Loader2 className="animate-spin" size={16} /> : <Play size={16} />} Start training</button><p className="mt-3 text-center text-[11px] text-black/35">Training is sent to the background worker and this page polls its persisted status.</p></section>
    </form>
    <div className="min-w-0 space-y-5"><ExperimentResults experiment={selected} /><section className="card overflow-hidden"><div className="flex items-center gap-2 border-b border-black/5 p-4 text-xs font-bold uppercase tracking-wider text-black/35"><Clock3 size={14} /> Experiment history</div>{experiments.length ? <div className="divide-y divide-black/5">{experiments.map((experiment) => <button type="button" key={experiment.id} onClick={() => setSelected(experiment)} className={`flex w-full items-center gap-3 p-4 text-left transition hover:bg-black/[.02] ${selected?.id === experiment.id ? 'bg-pine/[.04]' : ''}`}><Status status={experiment.status} /><div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{experiment.name}</div><div className="mt-1 text-[11px] capitalize text-black/35">{experiment.task_type} · {experiment.selected_models.length} model{experiment.selected_models.length === 1 ? '' : 's'} · {new Date(experiment.created_at).toLocaleString()}</div></div><ChevronRight size={16} className="text-black/20" /></button>)}</div> : <p className="p-6 text-sm text-black/40">Your saved experiments will appear here.</p>}</section></div>
  </div>
}

function Step({ number, title, icon: Icon }: { number: string; title: string; icon?: typeof SlidersHorizontal }) { return <div className="flex items-center gap-3"><span className="grid h-7 w-7 place-items-center rounded-lg bg-pine text-xs font-bold text-white">{number}</span>{Icon && <Icon size={16} className="text-pine" />}<h3 className="display font-bold">{title}</h3></div> }
function FieldSelect({ label, value, setValue, options }: { label: string; value: string; setValue: (value: string) => void; options: string[][] }) { const id = useId(); return <div><label className="label" htmlFor={id}>{label}</label><select id={id} className="input" value={value} onChange={(event) => setValue(event.target.value)}>{options.map(([optionId, name]) => <option key={optionId} value={optionId}>{name}</option>)}</select></div> }
function NumberField({ label, value, setValue, ...props }: { label: string; value: string; setValue: (value: string) => void; min: string; max: string; step: string }) { const id = useId(); return <div className="mt-3"><label className="label" htmlFor={id}>{label}</label><input id={id} className="input" type="number" value={value} onChange={(event) => setValue(event.target.value)} {...props} /></div> }
function Status({ status }: { status: Experiment['status'] }) { const active = status === 'queued' || status === 'training'; return <span className={`badge shrink-0 capitalize ${status === 'completed' ? 'bg-emerald-50 text-emerald-700' : status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>{active && <Loader2 size={12} className="animate-spin" />}{status}</span> }

function ExperimentResults({ experiment }: { experiment: Experiment | null }) {
  if (!experiment) return <section className="card grid min-h-[520px] place-items-center p-8 text-center"><div><Beaker className="mx-auto text-pine/25" size={48} /><h3 className="display mt-4 text-lg font-bold">Design a reproducible experiment</h3><p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-black/40">Select a task, target, features, preprocessing, and one or more available models. Results are persisted for comparison.</p></div></section>
  if (experiment.status === 'failed') return <section className="card min-h-[300px] p-8"><div className="flex items-center gap-3 text-red-700"><TriangleAlert /><h3 className="display text-lg font-bold">Training failed</h3></div><p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{experiment.error}</p></section>
  const active = ['queued', 'training'].includes(experiment.status)
  const columns = experiment.task_type === 'classification' ? [['accuracy', 'Accuracy'], ['precision', 'Precision'], ['recall', 'Recall'], ['f1', 'F1'], ['roc_auc', 'ROC-AUC']] : experiment.task_type === 'regression' ? [['mae', 'MAE'], ['rmse', 'RMSE'], ['r2', 'R²']] : [['silhouette_score', 'Silhouette'], ['cluster_sizes', 'Clusters']]
  return <section className="card min-h-[520px] overflow-hidden"><header className="border-b border-black/5 p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs font-bold uppercase tracking-[.18em] text-pine">{experiment.task_type}</div><h3 className="display mt-1 text-xl font-extrabold">{experiment.name}</h3><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-black/40">{experiment.target_column && <span className="flex items-center gap-1"><Target size={13} /> Target: {experiment.target_column}</span>}<span>{experiment.features.length} features</span><span>{experiment.selected_models.length} models</span></div></div><Status status={experiment.status} /></div>{active && <div className="mt-5"><div className="mb-2 flex justify-between text-xs text-black/40"><span>Background worker is {experiment.status}</span><span>{experiment.progress}%</span></div><div className="h-2 overflow-hidden rounded-full bg-black/5"><div className="h-full rounded-full bg-pine transition-all" style={{ width: `${Math.max(5, experiment.progress)}%` }} /></div></div>}</header>
    {active ? <div className="grid h-72 place-items-center text-center"><div><Activity className="mx-auto animate-pulse text-pine" size={34} /><p className="mt-3 text-sm font-semibold">Training without blocking the API</p><p className="mt-1 text-xs text-black/40">Results will appear here automatically.</p></div></div> : <div className="p-6"><div className="mb-4 flex items-center justify-between"><h4 className="display font-bold">Model comparison</h4><span className="text-[11px] text-black/35">Metrics use the held-out test partition</span></div><div className="overflow-x-auto rounded-xl border border-black/5"><table className="w-full whitespace-nowrap text-left text-sm"><thead className="bg-canvas text-xs uppercase tracking-wider text-black/35"><tr><th className="p-3">Model</th>{columns.map(([, label]) => <th className="p-3 text-right" key={label}>{label}</th>)}</tr></thead><tbody>{experiment.metrics.map((metric) => <tr className="border-t border-black/5" key={metric.id}><td className="p-3 font-semibold">{MODEL_NAMES[metric.model_name] || metric.model_name}</td>{columns.map(([key]) => <td className="p-3 text-right font-mono text-xs" key={key}>{formatMetric(metric.metrics[key])}</td>)}</tr>)}</tbody></table></div><div className="mt-5 grid gap-3 sm:grid-cols-3"><InfoCard title="Missing values" value={String(experiment.preprocessing.numeric_imputer)} /><InfoCard title="Scaling" value={String(experiment.preprocessing.scaler)} /><InfoCard title="Evaluation" value={experiment.task_type === 'clustering' ? 'Unsupervised' : `${Number(experiment.preprocessing.test_size) * 100}% held out`} /></div>{experiment.metrics.map((metric) => <ExplanationPanel key={`${metric.id}-explanation`} modelName={MODEL_NAMES[metric.model_name] || metric.model_name} explanation={metric.explainability} />)}{experiment.task_type === 'classification' && experiment.metrics.map((metric) => Array.isArray(metric.metrics.confusion_matrix) ? <div key={`${metric.id}-matrix`} className="mt-5 rounded-xl bg-canvas p-4"><div className="text-xs font-bold text-black/55">{MODEL_NAMES[metric.model_name]} confusion matrix</div><pre className="mt-2 overflow-auto text-xs text-black/55">{JSON.stringify(metric.metrics.confusion_matrix, null, 2)}</pre></div> : null)}</div>}
  </section>
}

function formatMetric(value: unknown) { if (value == null) return '—'; if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4); if (typeof value === 'object') return `${Object.keys(value as object).length} groups`; return String(value) }
function InfoCard({ title, value }: { title: string; value: string }) { return <div className="rounded-xl border border-black/5 bg-canvas p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-black/35">{title}</div><div className="mt-1 text-sm font-semibold capitalize">{value}</div></div> }

function ExplanationPanel({ modelName, explanation }: { modelName: string; explanation: ModelExplanation }) {
  if (!explanation || !explanation.status || explanation.status === 'unavailable') return <section className="mt-6 rounded-2xl border border-black/5 bg-canvas p-5"><div className="flex items-center gap-2"><Info size={17} className="text-black/35" /><h4 className="display font-bold">{modelName} explanation</h4></div><p className="mt-2 text-sm leading-relaxed text-black/50">{explanation?.reason || 'A reliable explanation is not available for this model.'}</p><InterpretationGuide explanation={explanation} /></section>
  const maxImportance = Math.max(...explanation.global_importance.map((row) => row.importance), 0.000001)
  const contributions = explanation.individual?.contributions || []
  const maxContribution = Math.max(...contributions.map((row) => Math.abs(row.contribution)), 0.000001)
  return <section className="mt-6 overflow-hidden rounded-2xl border border-black/5"><header className="flex flex-wrap items-start justify-between gap-3 bg-canvas p-5"><div><div className="flex items-center gap-2"><Lightbulb size={18} className="text-amber" /><h4 className="display font-bold">Why {modelName} produced its output</h4></div><p className="mt-1 text-xs text-black/45">{explanation.method_detail}</p></div><span className="badge bg-pine/[.08] text-pine">{explanation.method}</span></header><div className="grid gap-7 p-5 xl:grid-cols-2"><div><div className="flex items-end justify-between"><div><h5 className="text-sm font-bold">Global feature importance</h5><p className="mt-1 text-xs leading-relaxed text-black/40">Average influence across {explanation.sample_rows || 'held-out'} rows.</p></div><span className="text-[10px] font-bold uppercase tracking-wider text-black/30">Model-derived</span></div><div className="mt-4 space-y-3">{explanation.global_importance.map((row, index) => <div key={row.feature}><div className="mb-1.5 flex items-center justify-between gap-3 text-xs"><span className="font-semibold"><span className="mr-2 text-black/25">{index + 1}</span>{row.feature}</span><span className="font-mono text-black/40">{(row.share * 100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-black/[.05]"><div className="h-full rounded-full bg-pine" style={{ width: `${Math.max(2, row.importance / maxImportance * 100)}%` }} /></div></div>)}</div></div><div><h5 className="text-sm font-bold">One held-out prediction</h5>{explanation.individual ? <><div className="mt-3 grid grid-cols-3 gap-2"><InfoCard title="Model predicted" value={String(explanation.individual.prediction)} /><InfoCard title="Observed value" value={String(explanation.individual.actual)} /><InfoCard title="Model baseline" value={formatContribution(explanation.individual.baseline)} /></div><p className="mt-3 text-xs leading-relaxed text-black/40">Bars show which features moved this model's output above or below its baseline. Length indicates relative strength for this prediction.</p><div className="mt-4 space-y-3">{contributions.map((row) => <div key={row.feature}><div className="mb-1 flex items-center justify-between gap-3 text-xs"><span className="font-semibold">{row.feature}</span><span className={row.contribution >= 0 ? 'text-pine' : 'text-red-600'}>{row.contribution >= 0 ? 'raises' : 'lowers'} output</span></div><div className="relative h-3 rounded-full bg-black/[.04]"><div className="absolute bottom-0 left-1/2 top-0 w-px bg-black/15" />{row.contribution >= 0 ? <div className="absolute bottom-0 left-1/2 top-0 rounded-r-full bg-pine" style={{ width: `${Math.max(1, Math.abs(row.contribution) / maxContribution * 50)}%` }} /> : <div className="absolute bottom-0 right-1/2 top-0 rounded-l-full bg-[#c65f47]" style={{ width: `${Math.max(1, Math.abs(row.contribution) / maxContribution * 50)}%` }} />}</div></div>)}</div><details className="mt-4 rounded-xl border border-black/5 bg-canvas p-3"><summary className="cursor-pointer text-xs font-semibold text-black/55">View this row's input values</summary><div className="mt-3 flex flex-wrap gap-2">{explanation.individual.input.map((item) => <span className="rounded-lg bg-white px-2.5 py-1.5 text-[11px] text-black/55" key={item.feature}><strong>{item.feature}:</strong> {String(item.value ?? 'missing')}</span>)}</div></details><p className="mt-4 rounded-xl bg-amber/10 p-3 text-[11px] leading-relaxed text-black/50">{explanation.individual.output_note}</p></> : <div className="mt-3 rounded-xl bg-canvas p-4 text-sm text-black/45">{explanation.individual_unavailable_reason}</div>}</div></div><InterpretationGuide explanation={explanation} /></section>
}

function InterpretationGuide({ explanation }: { explanation?: ModelExplanation }) {
  const interpretation = explanation?.interpretation
  return <div className="grid border-t border-black/5 bg-[#fbfcfa] sm:grid-cols-3"><div className="p-4"><div className="text-[10px] font-bold uppercase tracking-wider text-pine">Model importance</div><p className="mt-1 text-xs leading-relaxed text-black/45">{interpretation?.importance_note || 'Describes patterns used by the fitted model.'}</p></div><div className="border-black/5 p-4 sm:border-l"><div className="text-[10px] font-bold uppercase tracking-wider text-[#53798d]">Correlation</div><p className="mt-1 text-xs leading-relaxed text-black/45">{interpretation?.correlation_note || 'Measures statistical association, not cause.'}</p></div><div className="border-black/5 p-4 sm:border-l"><div className="text-[10px] font-bold uppercase tracking-wider text-[#c65f47]">Causation</div><p className="mt-1 text-xs leading-relaxed text-black/45">{interpretation?.causal_note || 'Not established by this experiment.'}</p></div></div>
}

function formatContribution(value: unknown) { return typeof value === 'number' ? value.toFixed(4) : String(value ?? '—') }
