import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Activity, ClipboardList, HeartPulse, LogIn, LogOut, RefreshCcw, Send, ShieldCheck } from 'lucide-react'
import './styles.css'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
const requestSchema = z.object({
  customer_name: z.string().min(2),
  customer_email: z.string().email(),
  customer_phone: z.string().optional(),
  device_type: z.string().min(2),
  device_model: z.string().optional(),
  description: z.string().min(20),
})
type RequestForm = z.infer<typeof requestSchema>
type Ticket = RequestForm & { id: string; public_reference: string; priority: string; status: string; category: string; ai_summary?: string; suggested_action?: string; ai_confidence?: number; requires_manual_review: boolean; sla_due_at?: string }
type TicketList = { items: Ticket[]; total: number }
type AutomationRun = { id: string; workflow_name: string; correlation_id: string; status: string; attempt: number; error_message?: string | null; started_at: string; completed_at?: string | null }

const queryClient = new QueryClient()

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), ...authHeaders() },
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = Array.isArray(json.detail)
      ? json.detail.map((item: { msg?: string }) => item.msg).join(' ')
      : json.detail
    if (res.status === 401 && localStorage.getItem('token')) {
      localStorage.removeItem('token')
      queryClient.clear()
      window.dispatchEvent(new Event('serviceflow-auth-expired'))
    }
    throw new Error(detail || `Request failed with status ${res.status}`)
  }
  return json as T
}

function FieldError({ message }: { message?: string }) {
  return message ? <span className="field-error">{message}</span> : null
}

function PublicForm() {
  const form = useForm<RequestForm>({ resolver: zodResolver(requestSchema) })
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: async (body: RequestForm) => {
      return apiJson<Ticket>('/tickets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    },
    onSuccess: () => {
      form.reset()
      void client.invalidateQueries({ queryKey: ['tickets'] })
      void client.invalidateQueries({ queryKey: ['runs'] })
    },
  })
  return <section className="panel">
    <div className="section-heading"><h2>New Service Request</h2>{mutation.isPending && <span className="muted">Creating ticket...</span>}</div>
    <form onSubmit={form.handleSubmit(v => mutation.mutate(v))} className="grid">
      <label><input placeholder="Customer name" {...form.register('customer_name')} /><FieldError message={form.formState.errors.customer_name?.message} /></label>
      <label><input placeholder="Email" {...form.register('customer_email')} /><FieldError message={form.formState.errors.customer_email?.message} /></label>
      <label><input placeholder="Phone" {...form.register('customer_phone')} /></label>
      <label><input placeholder="Device type" {...form.register('device_type')} /><FieldError message={form.formState.errors.device_type?.message} /></label>
      <label><input placeholder="Device model" {...form.register('device_model')} /></label>
      <label className="wide"><textarea placeholder="Problem description" {...form.register('description')} /><FieldError message={form.formState.errors.description?.message} /></label>
      <button disabled={mutation.isPending}><Send size={16}/> {mutation.isPending ? 'Submitting...' : 'Submit request'}</button>
    </form>
    {mutation.data && <p className="success">Created {mutation.data.public_reference}. Priority: {mutation.data.priority}</p>}
    {mutation.isError && <p className="error">{mutation.error.message}</p>}
  </section>
}

function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('admin@serviceflow.local')
  const [password, setPassword] = useState('Admin123!ChangeMe')
  const mutation = useMutation({
    mutationFn: async () => apiJson<{ access_token: string }>('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) }),
    onSuccess: (json) => {
      localStorage.setItem('token', json.access_token)
      onLogin()
    },
  })
  return (
    <section className="panel compact login-card">
      <h2><LogIn size={18}/> Admin Login</h2>
      <div className="login-form">
        <input value={email} onChange={e=>setEmail(e.target.value)} aria-label="Admin email" />
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} aria-label="Admin password" />
        <button className="login-button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
          <ShieldCheck size={16}/> {mutation.isPending ? 'Signing in...' : 'Sign in'}
        </button>
      </div>
      {mutation.isError && <p className="error">{mutation.error.message}</p>}
    </section>
  )
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const ticketsQuery = useQuery({ queryKey: ['tickets'], queryFn: () => apiJson<TicketList>('/tickets?page_size=50'), retry: false })
  const runsQuery = useQuery({ queryKey: ['runs'], queryFn: () => apiJson<AutomationRun[]>('/automation/runs'), retry: false })
  const tickets: Ticket[] = ticketsQuery.data?.items ?? []
  const runs: AutomationRun[] = runsQuery.data ?? []
  const manualReview = tickets.filter(t => t.requires_manual_review)
  function refresh() {
    void ticketsQuery.refetch()
    void runsQuery.refetch()
  }
  return <main className="dashboard">
    <div className="toolbar"><button className="secondary" onClick={refresh} disabled={ticketsQuery.isFetching || runsQuery.isFetching}><RefreshCcw size={16}/> Refresh</button><button className="secondary" onClick={onLogout}><LogOut size={16}/> Logout</button></div>
    {(ticketsQuery.isError || runsQuery.isError) && <section className="panel"><p className="error">{ticketsQuery.error?.message || runsQuery.error?.message || 'Dashboard data could not be loaded.'}</p></section>}
    <section className="stats"><div><ClipboardList/> <b>{tickets.length}</b><span>Tickets</span></div><div><Activity/> <b>{manualReview.length}</b><span>Manual review</span></div><div><HeartPulse/> <b>{runs.length}</b><span>Automation runs</span></div></section>
    <section className="table"><div className="section-heading"><h2>Ticket Dashboard</h2>{ticketsQuery.isFetching && <span className="muted">Loading...</span>}</div>{tickets.length === 0 && <p className="muted">No tickets yet.</p>}{tickets.map(t => <article className="ticket-row" key={t.id}><div className="ticket-main"><strong>{t.public_reference}</strong><span>{t.customer_name}</span></div><div className="capitalize">{t.category}</div><div className={`badge ${t.priority}`}>{t.priority}</div><div className="status">{t.status}</div><p>{t.ai_summary || t.description}</p></article>)}</section>
    <section className="table"><h2>Manual Review Queue</h2>{manualReview.length === 0 && <p className="muted">No tickets require manual review.</p>}{manualReview.map(t => <article className="review-row" key={t.id}><strong>{t.public_reference}</strong><span>{t.customer_name}</span><p>{t.suggested_action}</p></article>)}</section>
    <section className="table"><h2>Automation Run History</h2>{runs.length === 0 && <p className="muted">No automation runs recorded.</p>}{runs.slice(0, 8).map(run => <article className="run-row" key={run.id}><strong>{run.workflow_name}</strong><span className={`run-status ${run.status}`}>{run.status}</span><span className="run-attempt">Attempt {run.attempt}</span><span className="run-date">{new Date(run.started_at).toLocaleString()}</span>{run.error_message && <p>{run.error_message}</p>}</article>)}</section>
    <section className="table"><h2>System Health</h2><p>API, database readiness, MailHog, MinIO, Redis, and n8n are wired through Docker Compose health checks.</p></section>
  </main>
}

function App() {
  const [logged, setLogged] = useState(Boolean(localStorage.getItem('token')))
  useEffect(() => {
    const handleAuthExpired = () => setLogged(false)
    window.addEventListener('serviceflow-auth-expired', handleAuthExpired)
    return () => window.removeEventListener('serviceflow-auth-expired', handleAuthExpired)
  }, [])
  function logout() {
    localStorage.removeItem('token')
    queryClient.clear()
    setLogged(false)
  }
  return <><header><h1>ServiceFlow AI</h1><nav>Request Automation Dashboard</nav></header><PublicForm />{logged ? <Dashboard onLogout={logout} /> : <Login onLogin={() => setLogged(true)} />}</>
}

createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><App /></QueryClientProvider>)
