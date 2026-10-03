import { createFileRoute } from '@tanstack/react-router'
import {
  Database,
  LogIn,
  LogOut,
  Play,
  RefreshCcw,
  Search,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { Session } from '@supabase/supabase-js'

import { isSupabaseConfigured, supabase } from '../lib/supabase'
import { isAllowedUserEmail } from '../lib/access'
import { loadDashboard, loadOhlcv, loadQuotePrices, runIngestion, type DashboardData } from '../lib/api'
import type { OhlcvDaily, QuoteSnapshot, Security } from '../generated/client/types.gen'

export const Route = createFileRoute('/')({ component: Home })

function Home() {
  const [session, setSession] = useState<Session | null>(null)
  const [email, setEmail] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL')
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [ohlcv, setOhlcv] = useState<OhlcvDaily[]>([])
  const [quotePrices, setQuotePrices] = useState<QuoteSnapshot[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

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
      setSession(null)
      setMessage('This email is not allowed to access Quant v1.')
      supabase?.auth.signOut()
      return
    }
    setSession(nextSession)
  }

  useEffect(() => {
    if (!token) return

    setLoading(true)
    setMessage(null)
    loadDashboard(token)
      .then((data) => {
        setDashboard(data)
        if (data.stocks.length > 0 && !data.stocks.some((stock) => stock.yahoo_symbol === selectedSymbol)) {
          setSelectedSymbol(data.stocks[0].yahoo_symbol)
        }
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false))
  }, [token, selectedSymbol])

  useEffect(() => {
    if (!token || !selectedSymbol) return

    Promise.all([loadOhlcv(selectedSymbol, token), loadQuotePrices(selectedSymbol, token)])
      .then(([nextOhlcv, nextQuotePrices]) => {
        setOhlcv(nextOhlcv)
        setQuotePrices(nextQuotePrices)
      })
      .catch((error: Error) => setMessage(error.message))
  }, [token, selectedSymbol])

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
      setDashboard(data)
      const [nextOhlcv, nextQuotePrices] = await Promise.all([
        loadOhlcv(selectedSymbol, token),
        loadQuotePrices(selectedSymbol, token),
      ])
      setOhlcv(nextOhlcv)
      setQuotePrices(nextQuotePrices)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to refresh data')
    } finally {
      setLoading(false)
    }
  }

  async function triggerIngestion() {
    if (!token) return
    setLoading(true)
    setMessage('Ingestion started. This can take a minute.')
    try {
      const result = await runIngestion(token)
      setMessage(`Ingestion ${result.status}: ${result.symbols_succeeded}/${result.symbols_total} symbols succeeded.`)
      await refreshData()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Ingestion failed')
      setLoading(false)
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
            <button className="primary-button" type="button" onClick={triggerIngestion} disabled={loading}>
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

        <section className="content-grid">
          <div className="table-region">
            <div className="section-heading">
              <div>
                <h2>Stock universe</h2>
                <p>Configured Yahoo Finance symbols grouped by listing exchange.</p>
              </div>
              <Search size={18} />
            </div>
            <StockTable
              stocks={dashboard?.stocks ?? []}
              quoteBySymbol={quoteBySymbol}
              selectedSymbol={selectedSymbol}
              onSelect={setSelectedSymbol}
            />
          </div>

          <aside className="detail-region">
            <SecurityDetail security={selectedSecurity} quote={latestQuote} ohlcvRows={ohlcv} priceRows={quotePrices} />
            <RunList runs={dashboard?.runs ?? []} />
          </aside>
        </section>
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
  selectedSymbol,
  onSelect,
}: {
  stocks: Security[]
  quoteBySymbol: Map<string, QuoteSnapshot>
  selectedSymbol: string
  onSelect: (symbol: string) => void
}) {
  return (
    <div className="stock-table">
      <div className="stock-row header">
        <span>Symbol</span>
        <span>Exchange</span>
        <span>Name</span>
        <span>Price</span>
      </div>
      {stocks.map((stock) => {
        const quote = quoteBySymbol.get(stock.yahoo_symbol)
        return (
          <button
            className={`stock-row ${selectedSymbol === stock.yahoo_symbol ? 'selected' : ''}`}
            key={stock.yahoo_symbol}
            type="button"
            onClick={() => onSelect(stock.yahoo_symbol)}
          >
            <strong>{stock.yahoo_symbol}</strong>
            <span>{stock.exchange_code}</span>
            <span>{stock.name}</span>
            <span>{formatMoney(quote?.price, quote?.currency ?? stock.currency)}</span>
          </button>
        )
      })}
    </div>
  )
}

function SecurityDetail({
  security,
  quote,
  ohlcvRows,
  priceRows,
}: {
  security: Security | undefined
  quote: QuoteSnapshot | undefined
  ohlcvRows: OhlcvDaily[]
  priceRows: QuoteSnapshot[]
}) {
  const orderedPrices = [...priceRows].reverse()
  const maxPrice = Math.max(...orderedPrices.map((row) => Number(row.price ?? 0)), 1)

  return (
    <section className="detail-panel">
      <div className="section-heading">
        <div>
          <h2>{security?.yahoo_symbol ?? 'No stock selected'}</h2>
          <p>{security?.name ?? 'Run ingestion to populate Supabase.'}</p>
        </div>
        <span className="exchange-pill">{security?.exchange_code ?? '--'}</span>
      </div>
      <div className="quote-grid">
        <Metric label="Last price" value={formatAmount(quote?.price)} />
        <Metric label="Price rows" value={priceRows.length} />
      </div>
      <div className="mini-chart" aria-label="Price history">
        {orderedPrices.slice(-42).map((row) => (
          <span
            key={row.date}
            title={`${row.date}: ${formatAmount(row.price)}`}
            style={{ height: `${Math.max((Number(row.price ?? 0) / maxPrice) * 100, 4)}%` }}
          />
        ))}
      </div>
      <div className="price-list">
        <h3>Price</h3>
        {priceRows.slice(0, 6).map((row) => (
          <div key={row.date}>
            <span>{row.date}</span>
            <strong>{formatMoney(row.price, row.currency)}</strong>
          </div>
        ))}
      </div>
      <div className="ohlcv-list">
        <h3>OHLCV</h3>
        {ohlcvRows.slice(0, 6).map((row) => (
          <div key={row.date}>
            <span>{row.date}</span>
            <strong>Close {formatAmount(row.close)}</strong>
            <small>
              O {formatAmount(row.open)} / H {formatAmount(row.high)} / L {formatAmount(row.low)} / V{' '}
              {row.volume?.toLocaleString() ?? '--'}
            </small>
          </div>
        ))}
      </div>
    </section>
  )
}

function RunList({ runs }: { runs: Array<{ id: string; status: string; started_at: string; symbols_succeeded: number; symbols_total: number }> }) {
  return (
    <section className="run-list">
      <h2>Recent ingestion</h2>
      {runs.length === 0 ? <p>No ingestion runs recorded.</p> : null}
      {runs.map((run) => (
        <div key={run.id}>
          <span>{new Date(run.started_at).toLocaleString()}</span>
          <strong>{run.status}</strong>
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
