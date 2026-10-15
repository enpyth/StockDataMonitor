import { createFileRoute } from '@tanstack/react-router'
import {
  Database,
  LogIn,
  LogOut,
  Play,
  RefreshCcw,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Session } from '@supabase/supabase-js'

import { isSupabaseConfigured, supabase } from '../lib/supabase'
import { isAllowedUserEmail } from '../lib/access'
import { loadDashboard, loadOhlcv, loadQuotePrices, runIngestion, type DashboardData } from '../lib/api'
import { PriceLineChart } from '../components/PriceLineChart'
import type { OhlcvDaily, QuoteSnapshot, Security } from '../generated/client/types.gen'

export const Route = createFileRoute('/')({ component: Home })

function Home() {
  const [session, setSession] = useState<Session | null>(null)
  const [email, setEmail] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [selectedExchange, setSelectedExchange] = useState('')
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [ohlcv, setOhlcv] = useState<OhlcvDaily[]>([])
  const [quotePrices, setQuotePrices] = useState<QuoteSnapshot[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailVersion, setDetailVersion] = useState(0)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const activeTokenRef = useRef<string | null>(null)

  const token = session?.access_token

  useEffect(() => {
    if (!supabase) return

    supabase.auth.getSession().then(({ data }) => {
      handleSession(data.session)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      handleSession(nextSession)
    })

    return () => data.subscription.unsubscribe()
  }, [])

  function handleSession(nextSession: Session | null) {
    const userEmail = nextSession?.user.email
    if (nextSession && !isAllowedUserEmail(userEmail)) {
      activeTokenRef.current = null
      setSession(null)
      setMessage('This email is not allowed to access Quant v1.')
      supabase?.auth.signOut()
      return
    }
    activeTokenRef.current = nextSession?.access_token ?? null
    setSession(nextSession)
    setDashboard(null)
    setSelectedSymbol('')
    setSelectedExchange('')
    setOhlcv([])
    setQuotePrices([])
    setDetailLoading(false)
  }

  useEffect(() => {
    if (!token) return
    let active = true

    setLoading(true)
    setMessage(null)
    loadDashboard(token)
      .then((data) => {
        if (!active) return
        setDashboard(data)
        setSelectedExchange((current) => data.exchanges.includes(current) ? current : (data.exchanges[0] ?? ''))
        setSelectedSymbol((current) =>
          data.stocks.some((stock) => stock.yahoo_symbol === current)
            ? current
            : (data.stocks[0]?.yahoo_symbol ?? ''),
        )
      })
      .catch((error: Error) => { if (active) setMessage(error.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token])

  useEffect(() => {
    if (!token || !selectedSymbol) {
      setOhlcv([])
      setQuotePrices([])
      setDetailLoading(false)
      return
    }
    let active = true
    setOhlcv([])
    setQuotePrices([])
    setDetailLoading(true)

    Promise.all([loadOhlcv(selectedSymbol, token), loadQuotePrices(selectedSymbol, token)])
      .then(([nextOhlcv, nextQuotePrices]) => {
        if (!active) return
        setOhlcv(nextOhlcv)
        setQuotePrices(nextQuotePrices)
      })
      .catch((error: Error) => { if (active) setMessage(error.message) })
      .finally(() => { if (active) setDetailLoading(false) })
    return () => { active = false }
  }, [token, selectedSymbol, detailVersion])

  const quoteBySymbol = useMemo(() => {
    return new Map((dashboard?.quotes ?? []).map((quote) => [quote.symbol, quote]))
  }, [dashboard])

  async function signInWithGoogle() {
    if (!supabase) return
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  }

  async function signInWithMagicLink() {
    if (!supabase || !email) return
    if (!isAllowedUserEmail(email)) {
      setMessage('This email is not allowed to access Quant v1.')
      return
    }
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    })
    setMessage(error ? error.message : 'Magic link sent. Check your email.')
  }

  async function refreshData() {
    if (!token) return
    setLoading(true)
    setMessage(null)
    try {
      const data = await loadDashboard(token)
      if (activeTokenRef.current !== token) return
      setDashboard(data)
      setSelectedExchange((current) => data.exchanges.includes(current) ? current : (data.exchanges[0] ?? ''))
      const nextSymbol = data.stocks.some((stock) => stock.yahoo_symbol === selectedSymbol)
        ? selectedSymbol
        : (data.stocks[0]?.yahoo_symbol ?? '')
      setSelectedSymbol(nextSymbol)
      setDetailVersion((version) => version + 1)
    } catch (error) {
      if (activeTokenRef.current === token) {
        setMessage(error instanceof Error ? error.message : 'Unable to refresh data')
      }
    } finally {
      if (activeTokenRef.current === token) setLoading(false)
    }
  }

  async function triggerIngestion() {
    if (!token || !selectedExchange) return
    setLoading(true)
    setMessage(`${selectedExchange} ingestion started. This can take a minute.`)
    try {
      const result = await runIngestion(token, selectedExchange)
      if (activeTokenRef.current !== token) return
      await refreshData()
      setMessage(`${selectedExchange} ingestion ${result.status}: ${result.symbols_succeeded}/${result.symbols_total} symbols succeeded.`)
    } catch (error) {
      if (activeTokenRef.current === token) {
        setMessage(error instanceof Error ? error.message : 'Ingestion failed')
        setLoading(false)
      }
    }
  }

  if (!isSupabaseConfigured) {
    return <SetupScreen />
  }

  if (!session) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <div className="brand-row">
            <Database size={26} />
            <span>Quant v1</span>
          </div>
          <h1>Market data collection workspace</h1>
          <p>Sign in to review configured securities, latest quote snapshots, daily OHLCV, and ingestion runs.</p>
          <div className="auth-actions">
            <button className="primary-button" type="button" onClick={signInWithGoogle}>
              <LogIn size={18} />
              Google
            </button>
            <div className="magic-link">
              <input
                aria-label="Email address"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
              <button type="button" onClick={signInWithMagicLink}>
                Send link
              </button>
            </div>
          </div>
          {message ? <p className="notice">{message}</p> : null}
        </section>
      </main>
    )
  }

  const selectedSecurity = dashboard?.stocks.find((stock) => stock.yahoo_symbol === selectedSymbol)
  const latestQuote = selectedSymbol ? quoteBySymbol.get(selectedSymbol) : undefined
  const userEmail = session.user.email ?? 'Signed in'

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Daily batch</span>
            <h1>Stock data monitor</h1>
          </div>
          <div className="topbar-actions">
            <span className="user-email" title={userEmail}>{userEmail}</span>
            <button type="button" onClick={refreshData} disabled={loading}>
              <RefreshCcw size={17} />
              Refresh
            </button>
            <select aria-label="Exchange to ingest" value={selectedExchange} onChange={(event) => setSelectedExchange(event.target.value)} disabled={loading || !dashboard?.exchanges.length}>
              {dashboard?.exchanges.length ? dashboard.exchanges.map((exchange) => <option key={exchange} value={exchange}>{exchange}</option>) : <option value="">No exchange configured</option>}
            </select>
            <button className="primary-button" type="button" onClick={triggerIngestion} disabled={loading || !selectedExchange}>
              <Play size={17} />
              Run ingestion
            </button>
            <button type="button" onClick={() => supabase?.auth.signOut()}>
              <LogOut size={17} />
              Log out
            </button>
          </div>
        </header>

        {message ? <p className="status-line">{message}</p> : null}

        <section className="metric-strip" aria-label="Summary">
          <Metric label="Configured stocks" value={dashboard?.stocks.length ?? 0} />
          <Metric label="Latest quotes" value={dashboard?.quotes.length ?? 0} />
          <Metric label="Recent runs" value={dashboard?.runs.length ?? 0} />
        </section>

        <div className="content-grid">
          <div className="table-region">
            <div className="section-heading">
              <div>
                <h2>Latest market data</h2>
                <p>Latest trading session OHLCV and latest quote snapshot for each configured stock.</p>
              </div>
            </div>
            <StockTable
              stocks={dashboard?.stocks ?? []}
              quoteBySymbol={quoteBySymbol}
              latestOhlcv={dashboard?.latestOhlcv ?? {}}
              selectedSymbol={selectedSymbol}
              onSelect={setSelectedSymbol}
            />
          </div>

          <div className="detail-region">
            <SecurityDetail security={selectedSecurity} quote={latestQuote} ohlcvRows={ohlcv} priceRows={quotePrices} loading={detailLoading} />
            <RunList runs={dashboard?.runs ?? []} />
          </div>
        </div>
      </section>
    </main>
  )
}

function SetupScreen() {
  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <div className="brand-row">
          <Database size={26} />
          <span>Quant v1</span>
        </div>
        <h1>Supabase environment required</h1>
          <p>Add `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`, and `VITE_ALLOWED_USER_EMAILS` to `.env`, then restart the web app.</p>
      </section>
    </main>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function StockTable({
  stocks,
  quoteBySymbol,
  latestOhlcv,
  selectedSymbol,
  onSelect,
}: {
  stocks: Security[]
  quoteBySymbol: Map<string, QuoteSnapshot>
  latestOhlcv: Record<string, OhlcvDaily | undefined>
  selectedSymbol: string
  onSelect: (symbol: string) => void
}) {
  return (
    <div className="stock-table-scroll">
      <div className="stock-table">
        <div className="stock-row header">
          <span>Stock</span><span>Session</span><span>Open</span><span>High</span>
          <span>Low</span><span>Close</span><span>Volume</span><span>Snapshot price</span>
        </div>
        {stocks.map((stock) => {
          const quote = quoteBySymbol.get(stock.yahoo_symbol)
          const daily = latestOhlcv[stock.yahoo_symbol]
          return (
            <button
              className={`stock-row ${selectedSymbol === stock.yahoo_symbol ? 'selected' : ''}`}
              key={stock.yahoo_symbol}
              type="button"
              onClick={() => onSelect(stock.yahoo_symbol)}
            >
              <span className="stock-identity"><strong>{stock.yahoo_symbol}</strong><small>{stock.name} · {stock.exchange_code}</small></span>
              <span className="stock-date">{daily?.date ?? '—'}</span>
              <span>{formatAmount(daily?.open)}</span>
              <span>{formatAmount(daily?.high)}</span>
              <span>{formatAmount(daily?.low)}</span>
              <strong>{formatAmount(daily?.close)}</strong>
              <span>{daily?.volume?.toLocaleString() ?? '—'}</span>
              <span className="snapshot-cell"><strong>{formatMoney(quote?.price, quote?.currency ?? stock.currency)}</strong><small>{quote?.date ?? 'No snapshot'}</small></span>
            </button>
          )
        })}
        {stocks.length === 0 && <p className="table-empty">No stocks configured for this user.</p>}
      </div>
    </div>
  )
}

function SecurityDetail({
  security,
  quote,
  ohlcvRows,
  priceRows,
  loading,
}: {
  security: Security | undefined
  quote: QuoteSnapshot | undefined
  ohlcvRows: OhlcvDaily[]
  priceRows: QuoteSnapshot[]
  loading: boolean
}) {
  const latestDaily = ohlcvRows[0]

  return (
    <section className="detail-panel">
      <div className="section-heading">
        <div>
          <h2>{security?.yahoo_symbol ?? 'No stock selected'}</h2>
          <p>{security?.name ?? 'Run ingestion to populate Supabase.'}</p>
        </div>
        <span className="exchange-pill">{security?.exchange_code ?? '--'}</span>
      </div>
      <div className="detail-prices">
        <div><span>Snapshot price · {quote?.date ?? '—'}</span><strong>{formatMoney(quote?.price, quote?.currency ?? security?.currency ?? 'USD')}</strong></div>
        <div><span>Session close · {latestDaily?.date ?? '—'}</span><strong>{formatMoney(latestDaily?.close, security?.currency ?? 'USD')}</strong></div>
      </div>
      {loading ? <p className="chart-empty">Loading price history…</p> : (
        <PriceLineChart ohlcvRows={ohlcvRows} priceRows={priceRows} currency={security?.currency ?? 'USD'} />
      )}
    </section>
  )
}

function RunList({ runs }: { runs: Array<{ id: string; exchange_code?: string | null; status: string; started_at: string; symbols_succeeded: number; symbols_total: number }> }) {
  return (
    <section className="run-list">
      <h2>Recent ingestion</h2>
      {runs.length === 0 ? <p>No ingestion runs recorded.</p> : null}
      {runs.map((run) => (
        <div key={run.id}>
          <span>{new Date(run.started_at).toLocaleString()}</span>
          <strong>{run.exchange_code ?? 'All'} · {run.status}</strong>
          <small>
            {run.symbols_succeeded}/{run.symbols_total} symbols
          </small>
        </div>
      ))}
    </section>
  )
}

function formatMoney(value: unknown, currency: string) {
  const number = Number(value)
  if (!Number.isFinite(number) || number === 0) return '--'
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(number)
}

function formatAmount(value: unknown) {
  const number = Number(value)
  if (!Number.isFinite(number) || number === 0) return '--'
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(number)
}
