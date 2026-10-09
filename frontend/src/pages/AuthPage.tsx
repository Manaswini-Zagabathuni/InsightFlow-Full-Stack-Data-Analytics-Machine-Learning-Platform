import { FormEvent, useState } from 'react'
import { ArrowRight, BarChart3, Check, Eye, EyeOff, Loader2, ShieldCheck } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { apiErrorMessage } from '../api/client'
import { useAuth } from '../context/AuthContext'

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user, login, register } = useAuth()
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()

  if (user) return <Navigate to="/dashboard" replace />

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      if (mode === 'register') {
        await register({
          full_name: String(form.get('full_name')),
          email: String(form.get('email')),
          password: String(form.get('password')),
        })
      } else {
        await login({ email: String(form.get('email')), password: String(form.get('password')) })
      }
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard'
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(apiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-[1.08fr_.92fr]">
      <section className="relative hidden overflow-hidden bg-[#123d30] p-12 text-white lg:flex lg:flex-col xl:p-16">
        <div className="absolute inset-0 grid-bg opacity-20" />
        <div className="relative flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-mint text-pine"><BarChart3 size={23} /></div>
          <div><div className="display text-xl font-extrabold">InsightFlow</div><div className="text-[10px] uppercase tracking-[.22em] text-white/45">Analytics workspace</div></div>
        </div>
        <div className="relative my-auto max-w-xl">
          <div className="mb-5 text-xs font-bold uppercase tracking-[.24em] text-mint">Secure by design</div>
          <h1 className="display text-5xl font-extrabold leading-[1.06] xl:text-6xl">Your analytical work deserves a solid foundation.</h1>
          <p className="mt-6 max-w-lg text-lg leading-relaxed text-white/60">A focused workspace for turning datasets into reliable, explainable results—built on authentication that protects every user boundary.</p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {['Hashed credentials', 'Expiring access tokens', 'Server-side authorization', 'Persistent sessions'].map((item) => <div className="flex items-center gap-2.5 text-sm text-white/75" key={item}><span className="grid h-6 w-6 place-items-center rounded-full bg-white/10 text-mint"><Check size={14} /></span>{item}</div>)}
          </div>
        </div>
        <div className="relative flex items-center gap-2 text-xs text-white/35"><ShieldCheck size={15} /> Passwords are never stored in plaintext.</div>
      </section>

      <section className="flex items-center justify-center bg-[#fbfcfa] px-5 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <div className="mb-9 lg:hidden"><div className="display text-xl font-extrabold text-pine">InsightFlow</div></div>
          <div className="mb-8">
            <p className="text-sm font-bold text-pine">{mode === 'login' ? 'Welcome back' : 'Create your account'}</p>
            <h2 className="display mt-2 text-3xl font-extrabold sm:text-4xl">{mode === 'login' ? 'Sign in to continue' : 'Start with InsightFlow'}</h2>
            <p className="mt-3 text-sm leading-relaxed text-black/50">{mode === 'login' ? 'Access your protected analytics workspace.' : 'Set up a secure account for your future analysis projects.'}</p>
          </div>

          <form className="space-y-5" onSubmit={submit}>
            {mode === 'register' && <div><label className="label" htmlFor="full_name">Full name</label><input className="input" id="full_name" name="full_name" autoComplete="name" required minLength={2} maxLength={120} placeholder="Ada Lovelace" /></div>}
            <div><label className="label" htmlFor="email">Email address</label><input className="input" id="email" name="email" type="email" autoComplete="email" required maxLength={320} placeholder="you@example.com" /></div>
            <div><label className="label" htmlFor="password">Password</label><div className="relative"><input className="input pr-11" id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 8 : 1} maxLength={72} placeholder={mode === 'register' ? '8+ characters with a letter and number' : 'Your password'} /><button aria-label={showPassword ? 'Hide password' : 'Show password'} className="absolute right-3 top-2.5 text-black/35 hover:text-black" type="button" onClick={() => setShowPassword((shown) => !shown)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></div>
            {error && <div role="alert" className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
            <button className="btn-primary w-full" disabled={submitting}>{submitting ? <Loader2 className="animate-spin" size={18} /> : null}{mode === 'login' ? 'Sign in' : 'Create account'}<ArrowRight size={17} /></button>
          </form>
          <p className="mt-7 text-center text-sm text-black/45">{mode === 'login' ? <>New to InsightFlow? <Link className="font-bold text-pine hover:underline" to="/register">Create an account</Link></> : <>Already have an account? <Link className="font-bold text-pine hover:underline" to="/login">Sign in</Link></>}</p>
        </div>
      </section>
    </main>
  )
}
