import { FormEvent, useEffect, useRef, useState } from 'react'
import { Bot, CheckCircle2, Cpu, Loader2, LockKeyhole, RefreshCw, Send, Sparkles, UserRound, WifiOff } from 'lucide-react'
import { api, apiErrorMessage } from '../api/client'
import type { AssistantAnswer, AssistantStatus, Dataset } from '../types/data'

const SUGGESTIONS = [
  'Give me a concise dataset summary',
  'Which columns have the most missing values?',
  'What are the strongest correlations?',
  'Interpret my latest saved visualization',
  'Summarize my latest ML experiment',
]

type Message = { id: number; role: 'user' | 'assistant'; content: string; metadata?: AssistantAnswer }

export function AssistantPanel({ dataset }: { dataset: Dataset }) {
  const [status, setStatus] = useState<AssistantStatus | null>(null)
  const [checking, setChecking] = useState(true)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  const checkStatus = async () => {
    setChecking(true); setError('')
    try { const { data } = await api.get<AssistantStatus>('/assistant/status'); setStatus(data) }
    catch (requestError) { setStatus({ available: false, model: 'local model', message: apiErrorMessage(requestError) }) }
    finally { setChecking(false) }
  }
  useEffect(() => { setMessages([]); checkStatus() }, [dataset.id])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, sending])

  const ask = async (event?: FormEvent, suggestion?: string) => {
    event?.preventDefault()
    const prompt = (suggestion || question).trim()
    if (!prompt || sending || !status?.available) return
    setMessages((current) => [...current, { id: Date.now(), role: 'user', content: prompt }]); setQuestion(''); setSending(true); setError('')
    try {
      const { data } = await api.post<AssistantAnswer>('/assistant/query', { dataset_id: dataset.id, question: prompt })
      setMessages((current) => [...current, { id: Date.now() + 1, role: 'assistant', content: data.answer, metadata: data }])
    } catch (requestError) { setError(apiErrorMessage(requestError)) }
    finally { setSending(false) }
  }

  if (checking) return <div className="card grid h-80 place-items-center"><div className="text-center"><Loader2 className="mx-auto animate-spin text-pine" /><p className="mt-3 text-sm text-black/45">Checking the local Ollama service…</p></div></div>
  if (!status?.available) return <div className="card overflow-hidden"><div className="grid min-h-[460px] place-items-center p-8 text-center"><div className="max-w-lg"><div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-black/[.04] text-black/35"><WifiOff size={28} /></div><div className="mt-5 text-xs font-bold uppercase tracking-[.18em] text-black/35">Optional enhancement</div><h3 className="display mt-2 text-xl font-extrabold">Local assistant unavailable</h3><p className="mt-3 text-sm leading-relaxed text-black/50">{status?.message || 'Ollama is not currently reachable.'}</p><div className="mt-5 rounded-xl bg-canvas p-4 text-left text-xs leading-relaxed text-black/50"><strong>The rest of InsightFlow is fully available.</strong> Install and start Ollama on this computer, pull the configured model, then retry. No paid LLM API is required.</div><button className="btn-secondary mt-5" onClick={checkStatus}><RefreshCw size={15} /> Check again</button></div></div></div>

  return <div className="card overflow-hidden"><header className="flex flex-wrap items-center justify-between gap-4 border-b border-black/5 bg-white p-5"><div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-pine text-white"><Bot size={22} /></div><div><h3 className="display font-bold">Dataset assistant</h3><p className="mt-0.5 text-xs text-black/40">Answers from structured InsightFlow analytics</p></div></div><div className="flex items-center gap-2"><span className="badge bg-emerald-50 text-emerald-700"><CheckCircle2 size={13} /> Local</span><span className="badge bg-black/[.04] text-black/50"><Cpu size={13} /> {status.model}</span></div></header>
    <div className="grid min-h-[620px] lg:grid-cols-[1fr_260px]"><div className="flex min-w-0 flex-col"><div className="h-[500px] space-y-5 overflow-y-auto p-5 sm:p-6">{messages.length === 0 ? <div className="grid h-full place-items-center text-center"><div className="max-w-md"><Sparkles className="mx-auto text-pine/30" size={42} /><h4 className="display mt-4 font-bold">Ask about {dataset.name}</h4><p className="mt-2 text-sm leading-relaxed text-black/40">Start with a summary, missing values, correlations, statistics, a saved visualization, or an ML experiment.</p><div className="mt-5 flex flex-wrap justify-center gap-2">{SUGGESTIONS.slice(0, 3).map((suggestion) => <button type="button" className="rounded-full border border-black/10 bg-white px-3 py-2 text-xs font-medium text-black/55 transition hover:border-pine/30 hover:text-pine" onClick={() => ask(undefined, suggestion)} key={suggestion}>{suggestion}</button>)}</div></div></div> : messages.map((message) => <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>{message.role === 'assistant' && <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-pine text-white"><Bot size={16} /></div>}<div className={`max-w-[82%] rounded-2xl px-4 py-3 ${message.role === 'user' ? 'bg-pine text-white' : 'border border-black/5 bg-canvas text-black/70'}`}><div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>{message.metadata && <div className="mt-3 flex flex-wrap gap-1.5 border-t border-black/5 pt-3">{message.metadata.context_sections.map((section) => <span key={section} className="rounded-md bg-white px-2 py-1 text-[10px] font-semibold capitalize text-black/35">{section}</span>)}</div>}</div>{message.role === 'user' && <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-black/5 text-black/45"><UserRound size={16} /></div>}</div>)}{sending && <div className="flex gap-3"><div className="grid h-8 w-8 place-items-center rounded-lg bg-pine text-white"><Bot size={16} /></div><div className="flex items-center gap-2 rounded-2xl bg-canvas px-4 py-3 text-sm text-black/40"><Loader2 size={14} className="animate-spin" /> Analyzing structured statistics locally…</div></div>}<div ref={endRef} /></div><form className="border-t border-black/5 p-4" onSubmit={ask}><div className="flex gap-2"><input className="input" value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={500} placeholder="Ask a supported dataset question…" /><button className="btn-primary shrink-0" aria-label="Send question" disabled={sending || !question.trim()}><Send size={16} /><span className="hidden sm:inline">Ask</span></button></div>{error && <div role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}</form></div>
      <aside className="border-t border-black/5 bg-canvas/60 p-5 lg:border-l lg:border-t-0"><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-black/40"><LockKeyhole size={14} /> Privacy boundary</div><p className="mt-3 text-xs leading-relaxed text-black/45">The model receives structured profiles, correlations, chart digests, and saved experiment metrics—not the complete CSV or raw rows.</p><div className="mt-5 border-t border-black/5 pt-5"><div className="text-xs font-bold text-black/55">Supported questions</div><div className="mt-3 space-y-2">{SUGGESTIONS.map((suggestion) => <button type="button" onClick={() => ask(undefined, suggestion)} key={suggestion} className="w-full rounded-lg border border-black/5 bg-white p-2.5 text-left text-[11px] leading-relaxed text-black/45 transition hover:border-pine/20 hover:text-pine">{suggestion}</button>)}</div></div><div className="mt-5 rounded-xl border border-amber/20 bg-amber/10 p-3 text-[11px] leading-relaxed text-black/50">Correlation and model importance describe patterns—not causes. The assistant is instructed never to make causal claims from them.</div></aside></div>
  </div>
}
