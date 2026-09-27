import type { Security, QuoteSnapshot, OhlcvDaily, IngestionRun, IngestionRunResult } from '../generated/client/types.gen'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export type DashboardData = {
  stocks: Security[]
  quotes: QuoteSnapshot[]
  runs: IngestionRun[]
}

export async function loadDashboard(token: string): Promise<DashboardData> {
  const [stocks, quotes, runs] = await Promise.all([
    apiFetch<Security[]>('/api/stocks', token),
    apiFetch<QuoteSnapshot[]>('/api/quotes/latest', token),
    apiFetch<IngestionRun[]>('/api/ingestions?limit=5', token),
  ])

  return { stocks, quotes, runs }
}

export function loadOhlcv(symbol: string, token: string): Promise<OhlcvDaily[]> {
  return apiFetch<OhlcvDaily[]>(`/api/stocks/${encodeURIComponent(symbol)}/ohlcv?limit=90`, token)
}

export function runIngestion(token: string): Promise<IngestionRunResult> {
  return apiFetch<IngestionRunResult>('/api/ingestions/run', token, { method: 'POST' })
}

async function readErrorDetail(response: Response) {
  const body = await response.text()
  if (!body) return ''

  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
    if (Array.isArray(parsed.detail)) return parsed.detail.map((item) => JSON.stringify(item)).join(', ')
  } catch {
    return body
  }

  return body
}
